/* Pure data operations shared by the offline viewer and dependency-free tests. */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.AtelierCore = api;
})(typeof globalThis === "object" ? globalThis : this, function () {
  "use strict";
  const MAX_FILE_BYTES = 96 * 1024 * 1024;
  const ROLES = ["archive-exhibit", "concept-render", "material-mood", "coded-timeline", "property-photo"];
  const STOP = new Set("a an and are as at be by for from has have in into is it its of on or that the this to was were will with".split(" "));
  const fail = (message) => { throw new Error(message); };
  const object = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
  const text = (value, name, max = 5000000) => typeof value === "string" && value.length <= max ? value : fail(`Invalid ${name}.`);
  const list = (value, name, max) => Array.isArray(value) && value.length <= max ? value : fail(`Invalid ${name}.`);
  const positive = (value) => Number.isSafeInteger(value) && value > 0;
  const id = (value, name) => text(value, name, 160).trim() || fail(`Missing ${name}.`);

  function resolution(width, height) {
    return {
      width, height,
      native4kCanvas: Math.max(width, height) >= 3840 && Math.min(width, height) >= 2160,
      landscape4kHero: width >= 3840 && height >= 2160,
      portrait4kHero: width >= 2160 && height >= 3840,
    };
  }

  function safeThumbnail(value) {
    // Never allow URLs, SVG, HTML, or user-controlled image paths into the DOM.
    if (typeof value !== "string" || value.length > 800000) return null;
    return /^data:image\/(?:jpeg|png|webp);base64,[A-Za-z0-9+/]+={0,2}$/.test(value) ? value : null;
  }

  function unique(items, name) {
    if (new Set(items.map((item) => item.id)).size !== items.length) fail(`Duplicate ${name} identifiers.`);
    return items;
  }

  function normalizeIndex(input) {
    if (!object(input) || input.schemaVersion !== 1 || input.scope !== "private-research") {
      fail("Choose a version 1 private research-index.json produced by maison_visuals.py.");
    }
    if (!object(input.document) || !/^[a-f0-9]{64}$/i.test(input.document.sha256 || "")) fail("The index needs its source document SHA-256.");
    const pages = list(input.pages, "pages", 25000).map((page) => {
      if (!object(page) || !positive(page.page)) fail("Invalid page reference.");
      return {page: page.page, section: text(page.section, "page section", 2000), text: text(page.text, "page text")};
    });
    const pageNumbers = new Set(pages.map((page) => page.page));
    if (pageNumbers.size !== pages.length) fail("Duplicate page numbers.");
    const chunks = unique(list(input.chunks, "passages", 100000).map((chunk) => {
      if (!object(chunk) || !pageNumbers.has(chunk.page)) fail("A passage references a missing page.");
      return {id: id(chunk.id, "passage ID"), page: chunk.page, section: text(chunk.section, "passage section", 2000), text: text(chunk.text, "passage text", 100000)};
    }), "passage");
    const images = unique(list(input.images, "images", 25000).map((image) => {
      if (!object(image) || !positive(image.width) || !positive(image.height) || image.width > 1000000 || image.height > 1000000) fail("Invalid image dimensions.");
      const refs = [...new Set(list(image.referencedOnPages, "image pages", 25000))];
      if (!refs.length || refs.some((page) => !pageNumbers.has(page))) fail("An image references a missing page.");
      return {
        id: id(image.id, "image ID"), xref: positive(image.xref) ? image.xref : null,
        ...resolution(image.width, image.height), referencedOnPages: refs.sort((a, b) => a - b),
        section: text(image.section, "image section", 2000),
        caption: text(image.caption || "Archive exhibit — source and rights require review.", "image caption", 10000),
        kind: "archive-exhibit-unreviewed", thumbnail: safeThumbnail(image.thumbnail),
      };
    }), "image");
    const sourceLinks = list(input.sourceLinks || [], "source references", 100000).filter((link) =>
      object(link) && pageNumbers.has(link.page) && typeof link.url === "string" && link.url.length <= 4096
    ).map((link) => ({page: link.page, url: link.url}));
    const ocrPages = new Set((Array.isArray(input.stats?.pagesNeedingOcrCheck) ? input.stats.pagesNeedingOcrCheck : []).filter((page) => pageNumbers.has(page)));
    return {
      schemaVersion: 1, scope: "private-research", project: "maisonnoirelhx",
      document: {filename: text(input.document.filename, "document filename", 1000), sha256: input.document.sha256.toLowerCase()},
      pages, chunks, images, sourceLinks, ocrPages,
    };
  }

  function terms(value) {
    return (value.toLowerCase().match(/[\p{L}\p{N}]+/gu) || []).filter((term) => (term.length > 1 || /^\d$/.test(term)) && !STOP.has(term));
  }

  function makeSearch(index) {
    const frequency = new Map();
    const corpus = index.chunks.map((chunk) => {
      const counts = new Map();
      for (const term of terms(`${chunk.id} ${chunk.section} ${chunk.text}`)) counts.set(term, (counts.get(term) || 0) + 1);
      for (const term of counts.keys()) frequency.set(term, (frequency.get(term) || 0) + 1);
      return {counts, length: [...counts.values()].reduce((sum, count) => sum + count, 0)};
    });
    const average = corpus.reduce((sum, item) => sum + item.length, 0) / Math.max(1, corpus.length);
    return function search(query) {
      const queryTerms = [...new Set(terms(query))];
      const pageQuery = /^\s*(?:p(?:age)?\.?\s*)?(\d+)\s*$/i.exec(query);
      if (!query.trim()) return index.chunks.map((chunk) => ({...chunk, score: 0}));
      return index.chunks.map((chunk, position) => {
        const {counts, length} = corpus[position];
        let score = 0;
        for (const term of queryTerms) {
          const count = counts.get(term) || 0;
          if (count) score += Math.log(1 + (corpus.length - frequency.get(term) + 0.5) / (frequency.get(term) + 0.5)) * count * 2.2 / (count + 1.2 * (0.25 + 0.75 * length / Math.max(1, average)));
        }
        if (pageQuery && chunk.page === Number(pageQuery[1])) score += 20;
        return {...chunk, score};
      }).filter((chunk) => chunk.score > 0).sort((a, b) => b.score - a.score || a.page - b.page || a.id.localeCompare(b.id));
    };
  }

  function filterImages(index, {query = "", quality = "all", pages = null, selectedIds = null} = {}) {
    const queryTerms = terms(query);
    return index.images.filter((image) => {
      if (quality === "4k" && !image.native4kCanvas) return false;
      if (quality === "landscape" && !image.landscape4kHero) return false;
      if (quality === "portrait" && !image.portrait4kHero) return false;
      if (quality === "thumbnail" && !image.thumbnail) return false;
      if (pages && !image.referencedOnPages.some((page) => pages.has(page))) return false;
      if (selectedIds && !selectedIds.has(image.id)) return false;
      const haystack = `${image.id} ${image.caption} ${image.section} ${image.referencedOnPages.join(" ")}`.toLowerCase();
      return queryTerms.every((term) => haystack.includes(term));
    });
  }

  function selectionKey(sectionId, imageId) { return JSON.stringify([sectionId, imageId]); }

  function saveCandidate(index, brief, candidates, input) {
    const section = brief.sections.find((item) => item.id === input.sectionId);
    const image = index.images.find((item) => item.id === input.imageId);
    if (!section || !image) fail("Choose an existing section and image.");
    const evidenceIds = [...new Set(list(input.evidenceIds || [], "linked passages", 200))];
    if (evidenceIds.some((item) => !index.chunks.some((chunk) => chunk.id === item))) fail("A linked passage no longer exists.");
    if (!ROLES.includes(input.proposedRole)) fail("Choose a supported visual role.");
    const candidate = {
      sectionId: section.id, imageId: image.id, evidenceIds,
      proposedRole: input.proposedRole, notes: text(input.notes || "", "review notes", 6000),
      publicCaption: text(input.publicCaption || "", "proposed caption", 2000),
    };
    candidates.set(selectionKey(section.id, image.id), candidate);
    return candidate;
  }

  function exportManifest(index, brief, candidates, now = new Date()) {
    const grouped = new Map();
    for (const candidate of candidates.values()) {
      const image = index.images.find((item) => item.id === candidate.imageId);
      const section = brief.sections.find((item) => item.id === candidate.sectionId);
      if (!image || !section) fail("A candidate has lost its source reference.");
      if (!grouped.has(image.id)) {
        grouped.set(image.id, {
          id: image.id, kind: "archive-exhibit-unreviewed", xref: image.xref,
          ...resolution(image.width, image.height), referencedOnPages: image.referencedOnPages,
          sourceDocumentSha256: index.document.sha256, selectionStatus: "candidate",
          dimensionsVerifiedFromBytes: false, rightsReviewed: false, visualReviewed: false,
          publicApproved: false, historicalClaimsApproved: false, associations: [],
        });
      }
      grouped.get(image.id).associations.push({
        sectionId: section.id, sectionTitle: section.title,
        proposedRole: candidate.proposedRole, notes: candidate.notes, publicCaption: candidate.publicCaption,
        claimStatus: "unverified", publicationStatus: "review-required",
        evidence: candidate.evidenceIds.map((chunkId) => {
          const chunk = index.chunks.find((item) => item.id === chunkId);
          if (!chunk) fail("A linked passage no longer exists.");
          return {chunkId: chunk.id, page: chunk.page, section: chunk.section, quote: chunk.text, documentSha256: index.document.sha256};
        }),
      });
    }
    return {
      schemaVersion: 1, manifestKind: "maison-visual-review", project: brief.project,
      scope: "private-review", createdAt: now.toISOString(), sourceDocument: {...index.document},
      publicationStatus: "review-required", historicalClaimsApproved: false,
      editorialSections: brief.sections.map(({id, title, evidenceQuery, visualDirection, visualRole}) => ({id, title, evidenceQuery, visualDirection, visualRole})),
      assets: [...grouped.values()],
      reviewRequired: [
        "This file contains confidential selected research passages; keep it local and private.",
        "Selections and same-page image references are proposals, not proof of relevance or historical claims.",
        "Review source provenance, actual original pixels, visual suitability, rights, credits, and all public content separately.",
        "Dimensions come from the research index, not a new original-file audit. Thumbnails are not publication assets.",
        "Nothing in this review grants publication approval; the pipeline publication gate must still reject it.",
      ],
    };
  }

  function importManifest(input, index, brief) {
    if (!object(input) || input.schemaVersion !== 1 || input.manifestKind !== "maison-visual-review" || input.scope !== "private-review") fail("Choose a Visual Atelier review manifest.");
    if (input.sourceDocument?.sha256 !== index.document.sha256) fail("This review belongs to a different source document. Import its research index first.");
    const restored = new Map();
    for (const asset of list(input.assets, "review assets", 25000)) {
      if (!object(asset)) fail("Invalid review asset.");
      for (const association of list(asset.associations, "editorial associations", 6)) {
        if (!object(association)) fail("Invalid editorial association.");
        const evidenceIds = list(association.evidence, "linked evidence", 200).map((item) => {
          const chunk = index.chunks.find((chunk) => chunk.id === item?.chunkId);
          if (!chunk || item.page !== chunk.page || item.documentSha256 !== index.document.sha256) fail("A review passage does not match this research index.");
          return chunk.id;
        });
        const key = selectionKey(association.sectionId, asset.id);
        if (restored.has(key)) fail("Duplicate review association.");
        saveCandidate(index, brief, restored, {...association, imageId: asset.id, evidenceIds});
      }
    }
    return restored;
  }

  return {MAX_FILE_BYTES, ROLES, resolution, safeThumbnail, normalizeIndex, makeSearch, filterImages, selectionKey, saveCandidate, exportManifest, importManifest};
});
