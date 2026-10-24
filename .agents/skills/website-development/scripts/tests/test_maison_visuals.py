import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

import fitz
from PIL import Image

MODULE = Path(__file__).resolve().parents[1] / 'maison_visuals.py'
spec = importlib.util.spec_from_file_location('maison_visuals', MODULE)
visuals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(visuals)


class PipelineTests(unittest.TestCase):
    def test_4k_rules_and_no_upscale(self):
        self.assertFalse(visuals.resolution(4000, 1000)['native4kCanvas'])
        self.assertTrue(visuals.resolution(2160, 3840)['native4kCanvas'])
        self.assertFalse(visuals.resolution(2160, 3840)['landscape4kHero'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'small.png'
            Image.new('RGB', (1672, 941), 'gray').save(source)
            produced = visuals.variants(source, root / 'variants')
            self.assertLessEqual(max(i['width'] for i in produced), 1672)
            self.assertFalse(visuals.image_audit(source)['native4kCanvas'])

    def test_full_401_page_ingestion_and_source_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pdf = root / 'test.pdf'
            doc = fitz.open()
            for number in range(401):
                page = doc.new_page()
                page.insert_text((40, 40), f'Archive page {number + 1}. ' + ('Water irrigation evidence.' if number == 400 else 'Architectural materials.'))
            doc.save(pdf)
            doc.close()
            stats = visuals.analyze(pdf, root / 'private', 0)
            index = visuals.read_json(root / 'private/research-index.json')
            self.assertEqual(stats['pages'], 401)
            matches = visuals.rank_chunks(index, 'water irrigation')
            self.assertEqual(matches[0]['page'], 401)
            self.assertEqual(index['scope'], 'private-research')

    def test_publication_boundaries(self):
        unknown = {'id': 'scan', 'kind': 'archive-exhibit-unreviewed', 'landscape4kHero': True}
        self.assertTrue(visuals.publication_gate(unknown, True))
        approved = {'rightsReviewed': True, 'visualReviewed': True, 'publicApproved': True,
                    'dimensionsVerifiedFromBytes': True, 'landscape4kHero': True,
                    'kind': 'concept-render', 'publicCaption': 'Architectural concept.'}
        self.assertEqual(visuals.publication_gate(approved, True), [])
        approved['creditRequiredByApi'] = True
        self.assertTrue(any('credit' in e for e in visuals.publication_gate(approved)))

    def test_no_external_query_without_opt_in_or_secret(self):
        with self.assertRaises(ValueError):
            visuals.research_pexels('courtyard', 'unused.json', False)
        with self.assertRaises(ValueError):
            visuals.fetch_bytes('http://images.pexels.com/image.jpg', host='images.pexels.com')
        with self.assertRaises(ValueError):
            visuals.fetch_bytes('https://localhost/image.jpg', host='images.pexels.com')


if __name__ == '__main__':
    unittest.main()
