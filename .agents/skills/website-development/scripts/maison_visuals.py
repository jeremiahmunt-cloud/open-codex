#!/usr/bin/env python3
"""Local PDF-to-visual research pipeline. No paid API or hosted model required."""
from __future__ import annotations

import argparse
import base64
from collections import Counter
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import urllib.parse
import urllib.request

import fitz
from PIL import Image, ImageOps, ImageFilter, ImageStat

STOP = set('a an and are as at be been by can for from has have in into is it its not of on or that the their these this to was were will with page pages original source contents maison noire confidential blessed homes llc'.split())
ALLOWED_IMAGE_HOSTS = {'images.pexels.com', 'dl.polyhaven.org'}
MAX_IMAGE_BYTES = 24 * 1024 * 1024


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    temp.replace(path)


def tokens(text):
    return [w for w in re.findall(r'[a-z]{3,}', text.lower()) if w not in STOP]


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def resolution(width, height):
    return {
        'width': width, 'height': height,
        'megapixels': round(width * height / 1e6, 2),
        'native4kCanvas': max(width, height) >= 3840 and min(width, height) >= 2160,
        'landscape4kHero': width >= 3840 and height >= 2160,
        'portrait4kHero': width >= 2160 and height >= 3840,
    }


def image_audit(path):
    with Image.open(path) as original:
        stored_size = list(original.size)
        image = ImageOps.exif_transpose(original).convert('RGB')
        metrics = resolution(*image.size)
        sample = image.copy()
        sample.thumbnail((512, 512))
        # Texture/edge energy is diagnostic, NOT an aesthetic quality rating.
        metrics['edgeEnergyDiagnostic'] = round(ImageStat.Stat(sample.convert('L').filter(ImageFilter.FIND_EDGES)).stddev[0], 2)
        metrics['storedSizeBeforeExif'] = stored_size
    metrics['sha256'] = file_hash(path)
    metrics['bytes'] = Path(path).stat().st_size
    metrics['upscaledByPipeline'] = False
    return metrics


def make_thumbnail(doc, xref):
    extracted = doc.extract_image(xref)
    if not extracted:
        return None
    with Image.open(io.BytesIO(extracted['image'])) as original:
        image = ImageOps.exif_transpose(original).convert('RGB')
        image.thumbnail((320, 240))
        buffer = io.BytesIO()
        image.save(buffer, 'JPEG', quality=72)
    return 'data:image/jpeg;base64,' + base64.b64encode(buffer.getvalue()).decode('ascii')


def analyze(pdf, out, thumbs=48):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    if not 0 <= thumbs <= 500:
        raise ValueError('Choose 0 to 500 thumbnails.')
    document_hash = file_hash(pdf)
    with fitz.open(pdf) as doc:
        if doc.needs_pass:
            raise ValueError('PDF is password-protected; provide an unlocked local copy.')
        toc = sorted(doc.get_toc(), key=lambda row: row[2])
        page_records, chunks, images, links, unreadable = [], [], {}, [], []
        for page_number, page in enumerate(doc, 1):
            text = page.get_text('text', sort=True).strip()
            active = [row for row in toc if row[2] <= page_number]
            section = active[-1][1] if active else 'Document'
            page_records.append({'page': page_number, 'section': section, 'text': text})
            referenced_images = page.get_images(full=True)
            image_dominant = any(i[2] >= 1000 and i[3] >= 1000 for i in referenced_images)
            if len(re.sub(r'\s', '', text)) < 80 or (image_dominant and len(text.split()) < 130):
                unreadable.append(page_number)
            words = text.split()
            # Page boundaries and overlapping windows retain source traceability.
            for offset in range(0, len(words), 260):
                fragment = ' '.join(words[offset:offset + 320])
                if fragment:
                    chunks.append({'id': f'p{page_number:04d}-{offset:04d}', 'page': page_number,
                                   'section': section, 'text': fragment})
            for item in referenced_images:
                xref, smask, width, height = item[:4]
                record = images.setdefault(xref, {
                    'id': f'pdf-{xref}', 'xref': xref, **resolution(width, height),
                    'referencedOnPages': [], 'section': section,
                    'kind': 'archive-exhibit-unreviewed', 'rightsReviewed': False,
                    'visualReviewed': False, 'publicApproved': False, 'maskXref': smask,
                    'caption': 'Archive exhibit — source and publication rights require review.'})
                if page_number not in record['referencedOnPages']:
                    record['referencedOnPages'].append(page_number)
            for link in page.get_links():
                url = link.get('uri', '')
                if url.startswith(('http://', 'https://')):
                    links.append({'page': page_number, 'url': url})
        candidates = sorted(images.values(), key=lambda v: v['width'] * v['height'], reverse=True)
        thumbnail_errors = []
        for record in candidates[:thumbs]:
            try:
                record['thumbnail'] = make_thumbnail(doc, record['xref'])
            except Exception as exc:
                thumbnail_errors.append({'id': record['id'], 'error': type(exc).__name__})
        stats = {
            'pages': len(doc), 'chunks': len(chunks), 'uniqueEmbeddedImages': len(images),
            'native4kCanvas': sum(i['native4kCanvas'] for i in candidates),
            'landscape4kHero': sum(i['landscape4kHero'] for i in candidates),
            'pagesNeedingOcrCheck': unreadable, 'thumbnailErrors': thumbnail_errors,
        }
    result = {'schemaVersion': 1, 'project': 'maisonnoirelhx', 'scope': 'private-research',
              'document': {'filename': Path(pdf).name, 'sha256': document_hash},
              'stats': stats, 'outline': toc, 'pages': page_records,
              'chunks': chunks, 'images': candidates, 'sourceLinks': links,
              'limits': ['Embedded-image references are not proof an image is displayed or licensed.',
                         'Text extraction is not a full OCR or factual-claim review.',
                         'Pixel dimensions do not establish visual quality or original native detail.',
                         'Nothing in this index is automatically approved for public publication.']}
    write_json(out / 'research-index.json', result)
    write_json(out / 'summary.json', stats)
    return stats


def rank_chunks(index, query, limit=8):
    """Explainable BM25 lexical ranking; does not pretend to use model embeddings."""
    query_terms = set(tokens(query))
    corpus = [Counter(tokens(c['section'] + ' ' + c['text'])) for c in index['chunks']]
    avg = sum(sum(c.values()) for c in corpus) / max(len(corpus), 1)
    frequency = Counter(term for terms in corpus for term in terms)
    results = []
    for chunk, terms in zip(index['chunks'], corpus):
        length = sum(terms.values())
        score = 0.0
        matched = []
        for term in query_terms:
            count = terms[term]
            if count:
                idf = math.log(1 + (len(corpus) - frequency[term] + .5) / (frequency[term] + .5))
                score += idf * count * 2.2 / (count + 1.2 * (.25 + .75 * length / max(avg, 1)))
                matched.append(term)
        if score:
            nearby = [i['id'] for i in index['images'] if chunk['page'] in i['referencedOnPages']]
            results.append({**chunk, 'score': round(score, 3), 'matchedTerms': sorted(matched),
                            'samePageImageIds': nearby})
    return sorted(results, key=lambda c: (-c['score'], c['page']))[:limit]


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise ValueError('Redirect refused; resolve the official original URL first.')


def fetch_bytes(url, *, host, headers=None, max_bytes=MAX_IMAGE_BYTES):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != host or parsed.username or parsed.password or parsed.port not in (None, 443):
        raise ValueError('Only HTTPS URLs on the expected official host are allowed.')
    req = urllib.request.Request(url, headers={'User-Agent': 'MaisonVisualResearch/1.0', **(headers or {})})
    with urllib.request.build_opener(NoRedirect).open(req, timeout=30) as response:
        data = response.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError('Download exceeds the configured asset-size limit.')
    return data


def research_pexels(query, out, allow_external=False):
    if not allow_external:
        raise ValueError('Use --allow-external-query with a generic visual query; never send private document text.')
    key = os.environ.get('PEXELS_API_KEY')
    if not key:
        raise ValueError('Set the free PEXELS_API_KEY locally. Do not paste it into source or chat.')
    if not 3 <= len(query) <= 160:
        raise ValueError('Provide a short visual query of 3–160 characters.')
    params = urllib.parse.urlencode({'query': query, 'per_page': 24, 'size': 'large', 'orientation': 'landscape'})
    data = json.loads(fetch_bytes('https://api.pexels.com/v1/search?' + params,
                                 host='api.pexels.com', headers={'Authorization': key}, max_bytes=2 * 1024 * 1024))
    assets = []
    for photo in data.get('photos', []):
        assets.append({'id': 'pexels-' + str(photo['id']), 'provider': 'pexels',
                       'kind': 'stock-mood', 'caption': photo.get('alt', ''),
                       'sourceUrl': photo['url'], 'downloadUrl': photo['src']['original'],
                       'author': photo['photographer'], 'authorUrl': photo['photographer_url'],
                       'licenseUrl': 'https://www.pexels.com/license/',
                       'creditRequiredByApi': True, 'creditLabel': 'Photos provided by Pexels',
                       'query': query, **resolution(photo['width'], photo['height']),
                       'dimensionsVerifiedFromBytes': False,
                       'rightsReviewed': False, 'visualReviewed': False, 'publicApproved': False})
    write_json(out, {'assets': assets, 'query': query, 'provider': 'pexels'})
    return {'candidates': len(assets), 'native4kMetadata': sum(a['native4kCanvas'] for a in assets),
            'note': 'Candidate dimensions are provider metadata until download/audit. API credits must be retained.'}


def download_candidates(manifest, out, limit=3):
    if not 1 <= limit <= 24:
        raise ValueError('Choose a download limit from 1 to 24.')
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    downloaded = []
    eligible = [a for a in read_json(manifest)['assets'] if a.get('native4kCanvas')]
    if not eligible:
        raise ValueError('No candidates meet the 4K canvas requirement in provider metadata.')
    for candidate in eligible[:limit]:
        url = candidate['downloadUrl']
        host = urllib.parse.urlsplit(url).hostname
        if host not in ALLOWED_IMAGE_HOSTS:
            raise ValueError('Download host is not an approved original-asset host.')
        data = fetch_bytes(url, host=host)
        # Decode before writing. This rejects HTML responses and unsupported payloads.
        with Image.open(io.BytesIO(data)) as image:
            image.verify()
        safe_id = re.sub('[^a-zA-Z0-9_-]', '-', candidate['id'])
        path = root / (safe_id + '.image')
        path.write_bytes(data)
        downloaded.append({**candidate, 'localPath': str(path.resolve()), **image_audit(path),
                           'dimensionsVerifiedFromBytes': True})
    write_json(root / 'asset-manifest.json', {'assets': downloaded})
    return {'downloaded': len(downloaded)}


def extract_originals(pdf, index_path, ids, out):
    index = read_json(index_path)
    if file_hash(pdf) != index['document']['sha256']:
        raise ValueError('The PDF does not match the analyzed source hash.')
    selected = [a for a in index['images'] if a['id'] in ids]
    if len(selected) != len(set(ids)) or not 1 <= len(selected) <= 24:
        raise ValueError('Choose 1–24 existing image IDs from this index.')
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    assets = []
    with fitz.open(pdf) as doc:
        for item in selected:
            extracted = doc.extract_image(item['xref'])
            if not extracted:
                raise ValueError('Image extraction failed for ' + item['id'])
            ext = re.sub('[^a-zA-Z0-9]', '', extracted['ext'])
            path = root / (item['id'] + '.' + ext)
            path.write_bytes(extracted['image'])
            asset = {**item, 'localPath': str(path.resolve()), **image_audit(path),
                     'dimensionsVerifiedFromBytes': True}
            asset.pop('thumbnail', None)
            if item['maskXref']:
                mask = doc.extract_image(item['maskXref'])
                if mask:
                    mask_path = root / (item['id'] + '-mask.png')
                    mask_path.write_bytes(mask['image'])
                    asset['separateMaskPath'] = str(mask_path.resolve())
            assets.append(asset)
    write_json(root / 'asset-manifest.json', {'scope': 'private-research', 'assets': assets})
    return {'originalsExtracted': len(assets), 'publicApproved': False}


def variants(path, out):
    root = Path(out)
    root.mkdir(parents=True, exist_ok=True)
    result = []
    with Image.open(path) as source:
        image = ImageOps.exif_transpose(source).convert('RGB')
        widths = sorted({min(image.width, w) for w in (640, 1280, 1920, 2560, 3840)})
        for width in widths:
            height = max(1, round(image.height * width / image.width))
            resized = image.resize((width, height), Image.Resampling.LANCZOS)
            name = f'{width}.webp'
            resized.save(root / name, 'WEBP', quality=86, method=5)
            result.append({'file': name, 'width': width, 'height': height})
    write_json(root / 'variants.json', {'source': image_audit(path), 'variants': result})
    return result


def build_plan(index_path, brief_path, out):
    index, brief = read_json(index_path), read_json(brief_path)
    result = {'project': brief['project'], 'scope': 'private-review',
              'fontSystem': brief['fontSystem'], 'sections': []}
    for section in brief['sections']:
        matches = rank_chunks(index, section['evidenceQuery'], 5)
        result['sections'].append({**section, 'evidence': matches,
            'renderPrompt': f"Architectural concept for {brief['project']}. {section['visualDirection']} "
                            'Target 3840x2160 or larger; verify delivered pixels. No text, addresses, logos, people, or factual completion claims. '
                            'Preserve real-property identity only when authorized reference photographs are supplied. '
                            'Label fictional/proposed architecture as a concept.',
            'publicationStatus': 'review-required'})
    write_json(out, result)
    return {'sections': len(result['sections']), 'matchedSections': sum(bool(s['evidence']) for s in result['sections'])}


def publication_gate(asset, hero=False):
    reasons = []
    for field in ('rightsReviewed', 'visualReviewed', 'publicApproved'):
        if asset.get(field) is not True:
            reasons.append(field + ' must be true')
    if asset.get('dimensionsVerifiedFromBytes') is not True:
        reasons.append('Verify actual file dimensions')
    if hero and not asset.get('landscape4kHero'):
        reasons.append('Landscape hero requires at least 3840×2160 without upscaling')
    if hero and asset.get('kind') not in ('property-photo', 'concept-render'):
        reasons.append('A texture, stock mood image, or archive scan is not an actual-property hero')
    if asset.get('kind') == 'concept-render' and not asset.get('publicCaption'):
        reasons.append('Concept render needs an adjacent public caption')
    if asset.get('creditRequiredByApi') and not asset.get('publicCredit'):
        reasons.append('Provider API requires public photo credit')
    return reasons


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('analyze'); p.add_argument('pdf'); p.add_argument('--out', required=True); p.add_argument('--thumbs', type=int, default=48)
    p = sub.add_parser('search'); p.add_argument('index'); p.add_argument('query'); p.add_argument('--limit', type=int, default=8); p.add_argument('--out')
    p = sub.add_parser('research'); p.add_argument('query'); p.add_argument('--out', required=True); p.add_argument('--allow-external-query', action='store_true')
    p = sub.add_parser('download'); p.add_argument('manifest'); p.add_argument('--out', required=True); p.add_argument('--limit', type=int, default=3)
    p = sub.add_parser('extract'); p.add_argument('pdf'); p.add_argument('--index', required=True); p.add_argument('--ids', nargs='+', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('audit'); p.add_argument('image'); p.add_argument('--out')
    p = sub.add_parser('variants'); p.add_argument('image'); p.add_argument('--out', required=True)
    p = sub.add_parser('plan'); p.add_argument('index'); p.add_argument('--brief', required=True); p.add_argument('--out', required=True)
    p = sub.add_parser('gate'); p.add_argument('manifest'); p.add_argument('--hero', action='store_true')
    args = parser.parse_args()
    try:
        if args.command == 'analyze': result = analyze(args.pdf, args.out, args.thumbs)
        elif args.command == 'search':
            result = rank_chunks(read_json(args.index), args.query, args.limit)
            if args.out: write_json(args.out, result)
        elif args.command == 'research': result = research_pexels(args.query, args.out, args.allow_external_query)
        elif args.command == 'download': result = download_candidates(args.manifest, args.out, args.limit)
        elif args.command == 'extract': result = extract_originals(args.pdf, args.index, args.ids, args.out)
        elif args.command == 'audit':
            result = image_audit(args.image)
            if args.out: write_json(args.out, result)
        elif args.command == 'variants': result = variants(args.image, args.out)
        elif args.command == 'plan': result = build_plan(args.index, args.brief, args.out)
        else:
            result = {a['id']: publication_gate(a, args.hero) for a in read_json(args.manifest)['assets']}
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 1 if any(result.values()) else 0
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except Exception as exc:
        # Never print request headers, API keys, or private document text on failure.
        print(f'ERROR ({type(exc).__name__}): {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
