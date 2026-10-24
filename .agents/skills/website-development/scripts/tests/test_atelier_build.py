import base64
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('build_atelier', SCRIPTS / 'build_atelier.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class AtelierBuildTests(unittest.TestCase):
    def test_committed_viewer_matches_sources_and_canonical_six_sections(self):
        html = builder.build()
        self.assertEqual(html, (builder.ASSETS / 'index.html').read_text(encoding='utf-8'))
        embedded = re.search(r'<script id="editorial-brief" type="application/json">(.*?)</script>', html, re.S)[1]
        self.assertEqual(json.loads(embedded), json.loads((SCRIPTS / 'maison-brief.json').read_text()))
        self.assertEqual(len(json.loads(embedded)['sections']), 6)

    def test_standalone_csp_hashes_match_and_network_is_disabled(self):
        html = builder.build()
        policy = re.search(r'http-equiv="Content-Security-Policy" content="([^"]+)"', html)[1]
        for directive in ["default-src 'none'", "connect-src 'none'", "form-action 'none'", "object-src 'none'", "frame-src 'none'", "worker-src 'none'", "font-src 'none'"]:
            self.assertIn(directive, policy)
        self.assertNotIn('unsafe-inline', policy)
        for tag in ('style', 'script'):
            for body in re.findall(r'<' + tag + r'(?:\s[^>]*)?>(.*?)</' + tag + '>', html, re.S):
                digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
                self.assertIn("'sha256-" + digest + "'", policy)
        self.assertNotRegex(html, r'<(?:script|link|iframe|img)\b[^>]*(?:src|href)="https?://')
        for forbidden in ('localStorage', 'sessionStorage', 'indexedDB', 'sendBeacon', 'XMLHttpRequest', 'fetch('):
            self.assertNotIn(forbidden, html)

    def test_exports_remain_rejected_by_existing_publication_gate(self):
        spec = importlib.util.spec_from_file_location('maison_visuals_gate', SCRIPTS / 'maison_visuals.py')
        visuals = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(visuals)
        code = """
const C=require(process.argv[1]); const fs=require('fs');
const i=C.normalizeIndex(JSON.parse(fs.readFileSync(process.argv[2])));
const b=JSON.parse(fs.readFileSync(process.argv[3])); const c=new Map();
C.saveCandidate(i,b,c,{sectionId:'architecture',imageId:i.images[0].id,evidenceIds:[i.chunks[0].id],proposedRole:'property-photo'});
process.stdout.write(JSON.stringify(C.exportManifest(i,b,c)));
"""
        result = subprocess.run(['node', '-e', code, str(builder.ASSETS / 'atelier-core.js'),
                                 str(builder.ASSETS / 'sample-index.json'), str(SCRIPTS / 'maison-brief.json')],
                                capture_output=True, text=True, check=True)
        asset = json.loads(result.stdout)['assets'][0]
        reasons = visuals.publication_gate(asset, hero=True)
        self.assertIn('rightsReviewed must be true', reasons)
        self.assertIn('publicApproved must be true', reasons)
        self.assertIn('Verify actual file dimensions', reasons)
        self.assertTrue(any('archive scan' in reason for reason in reasons))


if __name__ == '__main__':
    unittest.main()
