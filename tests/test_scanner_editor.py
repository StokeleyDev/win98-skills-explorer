import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import scan_skills
import server

class ScannerTests(unittest.TestCase):
    def test_yaml_and_scan_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            good = root/'good'/'SKILL.md'; good.parent.mkdir()
            good.write_text('---\nname: "hello: world"\ndescription: >-\n  first line\n  second line\nmetadata:\n  list: [one, two]\n---\n# Title\n', encoding='utf-8')
            bad = root/'bad'/'SKILL.md'; bad.parent.mkdir()
            bad.write_text('---\nname: [unterminated\n---\n', encoding='utf-8')
            cfg = {'roots': [{'runtime':'codex','source':'test','path':str(root)}, {'runtime':'codex','source':'missing','path':str(root/'missing')}]}
            result = scan_skills.scan(cfg)
            self.assertEqual(len(result['codex']), 2)
            skill = next(x for x in result['codex'] if x['name'] == 'hello: world')
            self.assertEqual(skill['full_desc'], 'first line second line')
            self.assertEqual(len(result['scan_errors']), 2)
            self.assertTrue(any('Invalid front matter' in e['message'] for e in result['scan_errors']))

    def test_config_validation(self):
        with self.assertRaises(ValueError): scan_skills.validate_config({'roots':[{'runtime':'wrong','source':'x','path':'x'}]})

class SaveTests(unittest.TestCase):
    def test_conflict_and_save_preserve_disk_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp)/'SKILL.md'; p.write_bytes(b'\xef\xbb\xbfline\r\n')
            original_scan = server.scan_skills.main
            server.scan_skills.main = lambda: {'scan_errors': []}
            class Handler:
                def send_json(self, data, code=200): self.result = (code, data)
            handler = Handler()
            def post(route, payload):
                if route.endswith('/read'): server.Win98SkillsHandler.handle_read_skill(handler, payload)
                else: server.Win98SkillsHandler.handle_save_skill(handler, payload)
                return handler.result
            try:
                _, read = post('/api/skills/read', {'path':str(p)})
                p.write_bytes(b'external change\r\n')
                status, conflict = post('/api/skills/save', {'path':str(p), 'content':'my edit\n', 'version':read['version']})
                self.assertEqual(status, 409); self.assertTrue(conflict['conflict']); self.assertEqual(p.read_bytes(), b'external change\r\n')
                p.write_bytes(b'\xef\xbb\xbfline\r\n')
                _, read = post('/api/skills/read', {'path':str(p)})
                status, saved = post('/api/skills/save', {'path':str(p), 'content':'edited\n', 'version':read['version']})
                self.assertEqual(status, 200); self.assertTrue(saved['success']); self.assertEqual(p.read_bytes(), b'\xef\xbb\xbfedited\r\n')
            finally:
                server.scan_skills.main = original_scan

if __name__ == '__main__': unittest.main()
