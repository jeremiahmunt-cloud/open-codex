(function () {
  "use strict";
  const C = window.AtelierCore;
  const brief = JSON.parse(document.getElementById("editorial-brief").textContent);
  const $ = (id) => document.getElementById(id);
  const state = {index: null, search: null, candidates: new Map(), sectionId: brief.sections[0].id,
    view: "evidence", query: "", allEvidence: false, quality: "all", related: false,
    pairing: null, visible: 24, sample: false, page: null, draft: null, pending: null};
  let importSequence = 0;
  const section = () => brief.sections.find((item) => item.id === state.sectionId);
  const findChunk = (id) => state.index.chunks.find((item) => item.id === id);
  const selected = (sectionId, imageId) => state.candidates.get(C.selectionKey(sectionId, imageId));
  const labelRole = (role) => role.replaceAll("-", " ");
  const format = (value) => value.toLocaleString("en-US");

  function node(tag, className, value) {
    const element = document.createElement(tag);
    if (className) element.className = className;
    if (value !== undefined) element.textContent = value;
    return element;
  }
  function button(label, action, value, className = "text-button") {
    const element = node("button", className, label);
    element.type = "button";
    element.dataset.action = action;
    if (value !== undefined) element.dataset.value = value;
    return element;
  }
  function pageButton(page, label = `p. ${page}`) { return button(label, "page", String(page), "page-link"); }
  function badge(label, warning = false) { return node("span", warning ? "badge warn" : "badge", label); }
  function notify(message, error = false) {
    $("notice").textContent = message;
    $("notice").dataset.error = String(error);
    $("notice").hidden = false;
  }
  function empty(title, message) {
    const element = node("div", "empty-state");
    element.append(node("span", "folio", "— /"), node("h3", "", title), node("p", "", message));
    return element;
  }
  function heading(message, count) {
    const element = node("div", "panel-heading");
    element.append(node("p", "", message), node("span", "result-count", count));
    return element;
  }
  function getThemeEvidence() { return state.search ? state.search(section().evidenceQuery) : []; }
  function setView(view, moveFocus = false) {
    state.view = view;
    state.visible = 24;
    render();
    if (moveFocus) $("tab-" + view).focus();
  }

  function renderNavigation() {
    const nav = $("section-nav");
    nav.replaceChildren();
    brief.sections.forEach((item, position) => {
      const element = button("", "section", item.id, "section-link");
      element.setAttribute("aria-current", String(item.id === state.sectionId));
      element.append(node("span", "section-index", String(position + 1).padStart(2, "0")), node("span", "", item.title));
      const count = [...state.candidates.values()].filter((candidate) => candidate.sectionId === item.id).length;
      if (count) element.append(node("small", "", String(count)));
      nav.append(element);
    });
  }

  function render() {
    renderNavigation();
    const editorial = section();
    $("section-number").textContent = `SECTION ${String(brief.sections.indexOf(editorial) + 1).padStart(2, "0")} / EDITORIAL DIRECTION`;
    $("section-title").textContent = editorial.title;
    $("visual-direction").textContent = editorial.visualDirection;
    $("section-role").textContent = labelRole(editorial.visualRole);
    for (const tab of document.querySelectorAll("[data-view]")) {
      const active = tab.dataset.view === state.view;
      tab.setAttribute("aria-selected", String(active));
      tab.tabIndex = active ? 0 : -1;
    }
    $("view-panel").setAttribute("aria-labelledby", "tab-" + state.view);
    $("search-tools").hidden = state.view === "review";
    $("search-input").placeholder = state.view === "images" ? "Search image IDs, captions, source sections, or page numbers…" : "Search passages or page numbers…";
    $("evidence-scope-label").hidden = state.view !== "evidence";
    $("quality-label").hidden = state.view !== "images";
    $("related-label").hidden = state.view !== "images";
    $("pairing-banner").hidden = !state.pairing;
    if (state.pairing) $("pairing-text").textContent = `Pairing passage p. ${findChunk(state.pairing).page} with imagery for “${section().title}”.`;
    $("evidence-count").textContent = state.index ? format(state.index.chunks.length) : "—";
    $("image-count").textContent = state.index ? format(state.index.images.length) : "—";
    $("review-count").textContent = format(state.candidates.size);
    $("export-manifest").disabled = !state.candidates.size;
    if (!state.index) return;
    const panel = $("view-panel");
    panel.replaceChildren();
    if (state.view === "evidence") renderEvidence(panel);
    else if (state.view === "images") renderImages(panel);
    else renderReview(panel);
  }

  function highlight(target, value, query) {
    const words = [...new Set(query.toLowerCase().match(/[\p{L}\p{N}]+/gu) || [])].filter((word) => word.length > 2).slice(0, 16);
    if (!words.length) { target.textContent = value; return; }
    const pattern = new RegExp("(" + words.map((word) => word.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|") + ")", "giu");
    let start = 0;
    for (const match of value.matchAll(pattern)) {
      target.append(document.createTextNode(value.slice(start, match.index)), node("mark", "", match[0]));
      start = match.index + match[0].length;
    }
    target.append(document.createTextNode(value.slice(start)));
  }

  function renderEvidence(panel) {
    const query = state.query.trim() || (state.allEvidence ? "" : section().evidenceQuery);
    const matches = state.search(query);
    panel.append(heading(query ? `Lexical evidence matches for “${query}”. Relevance is a starting point for your review.` : "All extracted passages, in source order. Open a page to inspect its full text and references.", `${format(matches.length)} passages`));
    if (!matches.length) {
      const element = empty("No matching evidence.", "Try fewer words, a page number, or Entire archive. A missing match does not establish a historical conclusion.");
      element.append(button("Browse the entire archive →", "browse-all"));
      panel.append(element);
      return;
    }
    const list = node("div", "evidence-list");
    for (const chunk of matches.slice(0, state.visible)) {
      const card = node("article", "evidence-card");
      card.dataset.chunkId = chunk.id;
      const meta = node("div", "source-meta");
      meta.append(pageButton(chunk.page), node("span", "", chunk.section), node("span", "", chunk.id));
      if (state.index.ocrPages.has(chunk.page)) meta.append(badge("OCR review", true));
      const excerpt = node("p", "evidence-text");
      highlight(excerpt, chunk.text, query);
      const footer = node("div", "card-footer");
      const imageCount = state.index.images.filter((image) => image.referencedOnPages.includes(chunk.page)).length;
      footer.append(node("span", "", `${imageCount} same-page image reference${imageCount === 1 ? "" : "s"} · unverified`), button("Pair imagery ↗", "pair", chunk.id));
      card.append(meta, excerpt, footer);
      list.append(card);
    }
    panel.append(list);
    loadMore(panel, matches.length);
  }

  function preview(image) {
    const element = node("div", "preview");
    element.append(node("span", "preview-label", "REVIEW THUMBNAIL"));
    const placeholder = node("div", "no-thumbnail");
    placeholder.append(node("strong", "", image.id), node("span", "", "No preview generated.\nUse the pipeline to extract the original."));
    element.append(placeholder);
    if (image.thumbnail) {
      const img = node("img");
      img.alt = `Archive review thumbnail ${image.id}; provenance and publication rights unreviewed`;
      img.loading = "lazy";
      img.decoding = "async";
      img.src = image.thumbnail;
      placeholder.hidden = true;
      img.addEventListener("error", () => { img.remove(); placeholder.hidden = false; });
      element.append(img);
    }
    return element;
  }

  function renderImages(panel) {
    const relatedPages = state.related ? new Set(state.pairing ? [findChunk(state.pairing).page] : getThemeEvidence().map((chunk) => chunk.page)) : null;
    const images = C.filterImages(state.index, {query: state.query, quality: state.quality, pages: relatedPages});
    panel.append(heading("Pixel thresholds use index dimensions, not a new original-file audit. Thumbnails are review aids; canvas size does not prove native detail or rights.", `${format(images.length)} images`));
    if (!images.length) {
      const element = empty("No images in this view.", "Some pages have no embedded images. Broaden the filters, or choose another passage. Missing thumbnails do not mean originals are unavailable.");
      element.append(button("Reset image filters →", "reset-filters"));
      panel.append(element);
      return;
    }
    const gallery = node("div", "gallery");
    for (const image of images.slice(0, state.visible)) {
      const chosen = selected(state.sectionId, image.id);
      const card = node("article", chosen ? "image-card chosen" : "image-card");
      card.dataset.imageId = image.id;
      const body = node("div", "image-body");
      const topline = node("div", "image-topline");
      topline.append(node("h3", "", image.id));
      if (image.native4kCanvas) topline.append(badge(image.landscape4kHero ? "4K LANDSCAPE" : "4K CANVAS"));
      const pages = node("div", "image-pages");
      image.referencedOnPages.slice(0, 4).forEach((page) => pages.append(pageButton(page)));
      if (image.referencedOnPages.length > 4) pages.append(node("span", "muted", `+${image.referencedOnPages.length - 4} more`));
      body.append(topline, node("p", "dimensions", `${format(image.width)} × ${format(image.height)} px · index metadata`), node("p", "image-caption", image.caption), pages,
        button(chosen ? "Edit candidate ✓" : state.pairing ? "Pair this image ↗" : "Inspect & select ↗", "candidate", image.id, "button compact"));
      card.append(preview(image), body);
      gallery.append(card);
    }
    panel.append(gallery);
    loadMore(panel, images.length);
  }

  function loadMore(panel, count) {
    if (count > state.visible) panel.append(button(`Show ${Math.min(24, count - state.visible)} more (${format(state.visible)} of ${format(count)})`, "more", "", "button load-more"));
  }

  function renderReview(panel) {
    panel.append(heading("All six editorial sections · candidates remain unapproved. Export includes exact selected passages and the source hash, without embedding image files.", `${format(state.candidates.size)} associations`));
    if (!state.candidates.size) {
      panel.append(empty("Your selection board is open.", "Choose a research passage, pair it with an image, and record why it belongs. An unlinked image can also be saved as a visual exploration candidate."));
      return;
    }
    for (const editorial of brief.sections) {
      const entries = [...state.candidates.values()].filter((candidate) => candidate.sectionId === editorial.id);
      if (!entries.length) continue;
      const group = node("section", "review-group");
      group.append(node("h3", "", editorial.title));
      for (const candidate of entries) {
        const image = state.index.images.find((item) => item.id === candidate.imageId);
        const article = node("article", "review-entry");
        const detail = node("div", "review-detail");
        const title = node("h4", "", `${image.id} · ${labelRole(candidate.proposedRole)}`);
        title.append(badge("REVIEW REQUIRED", true));
        detail.append(title, node("p", "muted", `${image.width} × ${image.height} px · origin: archive exhibit · publication approval: false`));
        if (candidate.notes) detail.append(node("p", "", candidate.notes));
        if (candidate.publicCaption) detail.append(node("p", "muted", `Unapproved caption: ${candidate.publicCaption}`));
        const links = node("div", "review-links");
        for (const id of candidate.evidenceIds) {
          const chunk = findChunk(id);
          links.append(pageButton(chunk.page, `p. ${chunk.page} · ${chunk.id}`));
        }
        if (!candidate.evidenceIds.length) links.append(node("span", "unlinked", "No evidence linked · visual exploration only"));
        const footer = node("div", "card-footer");
        const edit = button("Edit connection ↗", "edit-candidate", image.id);
        edit.dataset.section = editorial.id;
        footer.append(edit, button("Remove ×", "remove", C.selectionKey(editorial.id, image.id)));
        detail.append(links, footer);
        article.append(preview(image), detail);
        group.append(article);
      }
      panel.append(group);
    }
  }

  function showPage(number) {
    const page = state.index.pages.find((item) => item.page === number);
    if (!page) return;
    state.page = number;
    $("page-dialog-title").textContent = `Page ${number} · ${page.section}`;
    const body = $("page-dialog-body");
    body.replaceChildren(node("p", "muted", `${state.index.document.filename} · SHA-256 ${state.index.document.sha256}`));
    if (state.index.ocrPages.has(number)) body.append(node("p", "review-warning", "This page was flagged for OCR review. Extracted text may be absent or incomplete; inspect the original document locally."));
    body.append(node("div", "page-text", page.text || "No text extracted. This is not proof the page is blank. Inspect the original and review OCR."));
    const passages = node("div", "page-passages");
    state.index.chunks.filter((chunk) => chunk.page === number).forEach((chunk) => passages.append(button(`Pair imagery with ${chunk.id} ↗`, "pair", chunk.id, "button compact")));
    body.append(passages);
    const images = state.index.images.filter((image) => image.referencedOnPages.includes(number));
    body.append(node("h3", "", `Embedded image references (${images.length})`), node("p", "muted", "A same-page reference does not prove the image is displayed there, relevant, or licensed."));
    const imageButtons = node("div", "page-image-buttons");
    images.forEach((image) => imageButtons.append(button(`${image.id} · ${image.width} × ${image.height}`, "candidate", image.id, "button compact")));
    body.append(imageButtons);
    const refs = state.index.sourceLinks.filter((link) => link.page === number);
    if (refs.length) {
      body.append(node("h3", "", "Source references"), node("p", "muted", "Reference text only. This workspace never opens or requests external sources."));
      refs.forEach((link) => body.append(node("div", "source-reference", link.url)));
    }
    const numbers = state.index.pages.map((page) => page.page).sort((a, b) => a - b);
    $("previous-page").disabled = number === numbers[0];
    $("next-page").disabled = number === numbers[numbers.length - 1];
    $("page-jump").value = String(number);
    $("page-jump").max = String(numbers[numbers.length - 1]);
    $("page-jump").setCustomValidity("");
    if (!$("page-dialog").open) $("page-dialog").showModal();
  }

  function option(value, label) {
    const element = node("option", "", label);
    element.value = value;
    return element;
  }
  function openCandidate(imageId, sectionId = state.sectionId) {
    const image = state.index.images.find((item) => item.id === imageId);
    if (!image) return;
    $("page-dialog").close();
    state.draft = {imageId, sectionId};
    $("candidate-title").textContent = image.id;
    $("candidate-preview").replaceChildren(preview(image));
    $("candidate-meta").textContent = `${format(image.width)} × ${format(image.height)} px · index metadata${image.native4kCanvas ? " · 4K canvas" : " · below 4K canvas"}`;
    $("candidate-section").value = sectionId;
    fillDraft();
    $("candidate-dialog").showModal();
  }
  function fillDraft() {
    const draft = state.draft;
    const existing = selected(draft.sectionId, draft.imageId);
    draft.evidenceIds = [...(existing?.evidenceIds || [])];
    if (state.pairing && !draft.evidenceIds.includes(state.pairing)) draft.evidenceIds.push(state.pairing);
    const editorial = brief.sections.find((item) => item.id === draft.sectionId);
    $("candidate-role").value = existing?.proposedRole || editorial.visualRole;
    $("candidate-note").value = existing?.notes || "";
    $("candidate-caption").value = existing?.publicCaption || "";
    const choices = new Map();
    for (const chunk of state.search(editorial.evidenceQuery).slice(0, 80)) choices.set(chunk.id, chunk);
    for (const chunk of state.index.chunks.filter((chunk) => state.index.images.find((image) => image.id === draft.imageId).referencedOnPages.includes(chunk.page))) choices.set(chunk.id, chunk);
    for (const id of draft.evidenceIds) choices.set(id, findChunk(id));
    $("candidate-evidence").replaceChildren(option("", "Choose a passage to link (optional)…"));
    for (const chunk of choices.values()) $("candidate-evidence").append(option(chunk.id, `p. ${chunk.page} · ${chunk.id} · ${chunk.text.slice(0, 90)}`));
    renderLinkedEvidence();
  }
  function renderLinkedEvidence() {
    $("linked-evidence").replaceChildren();
    for (const id of state.draft.evidenceIds) {
      const chunk = findChunk(id);
      const row = node("div", "linked-row");
      const remove = button("×", "unlink", id);
      remove.setAttribute("aria-label", `Unlink passage ${id}`);
      row.append(node("span", "", `p. ${chunk.page} · ${chunk.id} · ${chunk.text.slice(0, 100)}`), remove);
      $("linked-evidence").append(row);
    }
  }

  async function readJsonFile(file) {
    if (!file || file.size > C.MAX_FILE_BYTES) throw new Error("Choose a JSON file no larger than 96 MiB.");
    const raw = await file.text();
    try { return JSON.parse(raw); }
    catch { throw new Error("That file is not valid JSON. Choose the original generated JSON file."); }
  }
  function afterConfirmation(action, message) {
    if (!state.candidates.size) { action(); return; }
    state.pending = action;
    $("confirm-message").textContent = message || "Export your review first if you want to keep it. Continuing clears the current index and candidate selections from this tab.";
    $("confirm-dialog").showModal();
  }
  function loadIndex(index, sample = false) {
    state.index = index;
    state.search = C.makeSearch(index);
    state.sample = sample;
    state.candidates = new Map();
    state.query = "";
    state.pairing = null;
    state.related = false;
    state.allEvidence = false;
    state.quality = "all";
    state.view = "evidence";
    state.visible = 24;
    $("search-input").value = "";
    $("all-evidence").checked = false;
    $("related-images").checked = false;
    $("quality-filter").value = "all";
    document.querySelector(".intro").hidden = true;
    $("archive-bar").hidden = false;
    $("document-name").textContent = index.document.filename;
    $("document-hash").textContent = `SHA-256 ${index.document.sha256.slice(0, 16)}…`;
    $("browse-pages").disabled = !index.pages.length;
    $("archive-label").textContent = sample ? "FICTIONAL SAMPLE / NO PROPERTY FACTS" : "LOCAL SOURCE ARCHIVE";
    $("archive-stats").replaceChildren();
    for (const [value, label] of [[index.pages.length, "pages"], [index.images.length, "images"], [index.images.filter((image) => image.native4kCanvas).length, "4K canvas"]]) {
      const stat = node("div", "stat");
      stat.append(node("strong", "", format(value)), node("span", "", label));
      $("archive-stats").append(stat);
    }
    for (const id of ["search-input", "all-evidence", "quality-filter", "manifest-file", "clear-session"]) $(id).disabled = false;
    $("resume-label").classList.remove("disabled");
    $("resume-label").setAttribute("aria-disabled", "false");
    notify(sample ? "Fictional sample loaded. Schematic previews and dimensions illustrate the interface; they are not property photography or verified original pixels." : `${format(index.pages.length)} pages loaded locally. Nothing uploaded or stored. Export your review before closing this tab.`);
    render();
  }

  $("index-file").addEventListener("change", async (event) => {
    const sequence = ++importSequence;
    const file = event.target.files[0];
    if (!file) return;
    try {
      const index = C.normalizeIndex(await readJsonFile(file));
      if (sequence === importSequence) afterConfirmation(() => loadIndex(index));
    } catch (error) { notify(error.message, true); }
    finally { event.target.value = ""; }
  });
  $("manifest-file").addEventListener("change", async (event) => {
    const file = event.target.files[0];
    if (!file || !state.index) return;
    const index = state.index;
    try {
      const restored = C.importManifest(await readJsonFile(file), index, brief);
      if (state.index !== index) throw new Error("The source index changed. Reopen the review for the current source.");
      afterConfirmation(() => {
        state.candidates = restored;
        setView("review");
        notify(`Restored ${restored.size} candidate associations. All publication and historical approvals remain false.`);
      }, "Replace the current candidate selections with this saved review? Export the current review first to keep it.");
    } catch (error) { notify(error.message, true); }
    finally { event.target.value = ""; }
  });
  $("load-sample").addEventListener("click", () => afterConfirmation(() => loadIndex(C.normalizeIndex(JSON.parse($("sample-index").textContent)), true)));
  $("browse-pages").addEventListener("click", () => {
    if (state.index?.pages.length) showPage(Math.min(...state.index.pages.map((page) => page.page)));
  });
  $("confirm-replace").addEventListener("click", () => {
    const action = state.pending;
    state.pending = null;
    $("confirm-dialog").close();
    if (action) action();
  });
  $("confirm-dialog").addEventListener("close", () => { state.pending = null; });
  $("clear-session").addEventListener("click", () => afterConfirmation(() => window.location.reload()));
  $("search-input").addEventListener("input", (event) => { state.query = event.target.value; state.visible = 24; render(); });
  $("all-evidence").addEventListener("change", (event) => { state.allEvidence = event.target.checked; state.visible = 24; render(); });
  $("quality-filter").addEventListener("change", (event) => { state.quality = event.target.value; state.visible = 24; render(); });
  $("related-images").addEventListener("change", (event) => { state.related = event.target.checked; state.visible = 24; render(); });
  $("cancel-pairing").addEventListener("click", () => { state.pairing = null; state.related = false; $("related-images").checked = false; render(); });
  $("candidate-section").addEventListener("change", (event) => { state.draft.sectionId = event.target.value; fillDraft(); });
  $("candidate-evidence").addEventListener("change", (event) => {
    if (event.target.value && !state.draft.evidenceIds.includes(event.target.value)) state.draft.evidenceIds.push(event.target.value);
    event.target.value = "";
    renderLinkedEvidence();
  });
  $("candidate-form").addEventListener("submit", (event) => {
    event.preventDefault();
    try {
      C.saveCandidate(state.index, brief, state.candidates, {...state.draft, proposedRole: $("candidate-role").value, notes: $("candidate-note").value, publicCaption: $("candidate-caption").value});
      $("candidate-dialog").close();
      notify("Candidate saved for review. Rights, visual suitability, historical claims, and publication remain unapproved.");
      render();
      $("tab-" + state.view).focus();
    } catch (error) { notify(error.message, true); }
  });
  $("previous-page").addEventListener("click", () => {
    const pages = state.index.pages.map((page) => page.page).filter((number) => number < state.page);
    if (pages.length) showPage(Math.max(...pages));
  });
  $("next-page").addEventListener("click", () => {
    const pages = state.index.pages.map((page) => page.page).filter((number) => number > state.page);
    if (pages.length) showPage(Math.min(...pages));
  });
  $("page-jump").addEventListener("change", (event) => {
    const number = Number(event.target.value);
    if (state.index.pages.some((page) => page.page === number)) showPage(number);
    else { event.target.setCustomValidity("Choose a page number present in this index."); event.target.reportValidity(); }
  });
  $("export-manifest").addEventListener("click", () => {
    if (!state.index || !state.candidates.size) return;
    const manifest = C.exportManifest(state.index, brief, state.candidates);
    const url = URL.createObjectURL(new Blob([JSON.stringify(manifest, null, 2) + "\n"], {type: "application/json"}));
    const anchor = node("a");
    anchor.href = url;
    anchor.download = "maison-visual-manifest.json";
    document.body.append(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
    notify("Review manifest exported locally. It contains selected private passages and no publication approvals. Keep it confidential.");
  });

  document.addEventListener("click", (event) => {
    const close = event.target.closest("[data-close]");
    if (close) { $(close.dataset.close).close(); return; }
    const tab = event.target.closest("[data-view]");
    if (tab) { setView(tab.dataset.view); return; }
    const trigger = event.target.closest("[data-action]");
    if (!trigger) return;
    const value = trigger.dataset.value;
    switch (trigger.dataset.action) {
      case "section":
        state.sectionId = value; state.pairing = null; state.query = ""; state.related = false;
        $("search-input").value = ""; $("related-images").checked = false; state.visible = 24;
        render();
        document.querySelector(`[data-value="${value}"]`)?.focus();
        break;
      case "page": if (state.index) showPage(Number(value)); break;
      case "candidate": openCandidate(value); break;
      case "edit-candidate": openCandidate(value, trigger.dataset.section); break;
      case "pair":
        $("page-dialog").close(); state.pairing = value; state.related = true; state.query = "";
        $("search-input").value = ""; $("related-images").checked = true; setView("images", true); break;
      case "more": state.visible += 24; render(); break;
      case "browse-all": state.allEvidence = true; state.query = ""; $("all-evidence").checked = true; $("search-input").value = ""; render(); break;
      case "reset-filters": state.quality = "all"; state.query = ""; state.related = false; $("quality-filter").value = "all"; $("related-images").checked = false; $("search-input").value = ""; render(); break;
      case "unlink": state.draft.evidenceIds = state.draft.evidenceIds.filter((id) => id !== value); renderLinkedEvidence(); break;
      case "remove": state.candidates.delete(value); render(); break;
    }
  });
  document.addEventListener("keydown", (event) => {
    const editable = /INPUT|TEXTAREA|SELECT/.test(event.target.tagName) || event.target.isContentEditable;
    if (event.key === "/" && !editable && state.index && !document.querySelector("dialog[open]")) {
      event.preventDefault(); if (state.view === "review") setView("evidence"); $("search-input").focus();
    }
    if (event.target.matches("[role=tab]") && ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
      event.preventDefault();
      const tabs = ["evidence", "images", "review"];
      let position = tabs.indexOf(state.view);
      if (event.key === "Home") position = 0;
      else if (event.key === "End") position = 2;
      else position = (position + (event.key === "ArrowRight" ? 1 : 2)) % 3;
      setView(tabs[position], true);
    }
    if (event.target.classList.contains("file-label") && ["Enter", " "].includes(event.key)) {
      event.preventDefault();
      const input = $(event.target.getAttribute("for"));
      if (!input.disabled) input.click();
    }
  });
  document.querySelectorAll(".file-label").forEach((label) => {
    label.tabIndex = 0;
    label.setAttribute("role", "button");
    label.setAttribute("aria-disabled", String($(label.getAttribute("for")).disabled));
  });
  brief.sections.forEach((item) => $("candidate-section").append(option(item.id, item.title)));
  C.ROLES.forEach((role) => $("candidate-role").append(option(role, labelRole(role))));
  render();
})();
