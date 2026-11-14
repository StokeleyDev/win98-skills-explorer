import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

import scan_skills
import server


class PermissionTests(unittest.TestCase):
    def test_read_allowed_in_scan_root_but_write_only_in_skills_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            writable, plugin = root / 'skills', root / 'plugins'
            with patch.object(scan_skills, 'writable_skill_roots', return_value={'claude': writable}), \
                 patch.object(scan_skills, 'configured_roots', return_value=[root]):
                plugin_skill = str(plugin / 'p' / 'SKILL.md')
                self.assertTrue(server.validated_skill_path(plugin_skill))
                with self.assertRaises(ValueError):
                    server.validated_skill_path(plugin_skill, write=True)
                self.assertTrue(server.validated_skill_path(str(writable / 'a' / 'SKILL.md'), write=True))
                with self.assertRaises(ValueError):
                    server.validated_skill_path(str(root.parent / 'x' / 'SKILL.md'))

    def test_too_broad_roots_rejected(self):
        for path in (str(Path.home()), Path.home().anchor):
            with self.subTest(path=path), self.assertRaises(ValueError):
                scan_skills.validate_config({'roots': [{'runtime': 'claude', 'source': 's', 'path': path}]})


class DeleteTests(unittest.TestCase):
    def test_delete_moves_folder_to_trash(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = Path(tmp) / 'skills' / 'demo'; skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('x'); (skill / 'helper.py').write_text('y')
            trash = Path(tmp) / 'trash'
            with patch.object(server, 'TRASH_DIR', trash), patch.dict('sys.modules', {'send2trash': None}):
                where = server.move_to_trash(skill)
            self.assertFalse(skill.exists())
            self.assertTrue((Path(where) / 'helper.py').exists())


class HttpTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.httpd = server.ThreadingHTTPServer(('127.0.0.1', 0), server.Win98SkillsHandler)
        cls.port = cls.httpd.server_address[1]
        cls.hosts = patch.object(server, 'ALLOWED_HOSTS', (f'127.0.0.1:{cls.port}',))
        cls.hosts.start()
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.httpd.shutdown(); cls.httpd.server_close(); cls.hosts.stop()

    def request(self, method, path, host=None, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        conn.putrequest(method, path, skip_host=True)
        conn.putheader('Host', host or f'127.0.0.1:{self.port}')
        for k, v in (headers or {}).items(): conn.putheader(k, v)
        conn.putheader('Content-Length', str(len(body or b'')))
        conn.endheaders(body)
        resp = conn.getresponse(); data = resp.read(); conn.close()
        return resp.status, data

    def test_get_rejects_foreign_host(self):
        self.assertEqual(self.request('GET', '/api/skills/config', host='evil.example:1998')[0], 403)

    def test_static_whitelist(self):
        self.assertEqual(self.request('GET', '/index.html')[0], 200)
        for path in ('/server.py', '/scan_config.json', '/skills_data.json', '/fonts/converted/../../server.py'):
            with self.subTest(path=path):
                self.assertEqual(self.request('GET', path)[0], 404)

    def test_bad_content_length(self):
        self.assertEqual(self.request('POST', '/api/skills/read', headers={'Content-Length': 'abc'})[0], 400)

    def post(self, path, payload, origin=None):
        headers = {'Content-Type': 'application/json'}
        if origin: headers['Origin'] = origin
        status, data = self.request('POST', path, body=json.dumps(payload).encode(), headers=headers)
        return status, json.loads(data)

    def test_foreign_origin_rejected(self):
        self.assertEqual(self.post('/api/skills/rescan', {}, origin='https://evil.example')[0], 403)

    def test_create_read_delete_cycle(self):
        with tempfile.TemporaryDirectory() as tmp:
            skills = Path(tmp).resolve() / 'skills'
            with patch.object(scan_skills, 'writable_skill_roots', return_value={'claude': skills}), \
                 patch.object(scan_skills, 'configured_roots', return_value=[]), \
                 patch.object(server, 'rescan', return_value={}), \
                 patch.object(server, 'TRASH_DIR', Path(tmp) / 'trash'), \
                 patch.dict('sys.modules', {'send2trash': None}):
                self.assertEqual(self.post('/api/skills/create', {'runtime': 'nope', 'name': 'x'})[0], 400)
                self.assertEqual(self.post('/api/skills/create', {'runtime': 'claude', 'name': '!!!'})[0], 400)
                status, created = self.post('/api/skills/create', {'runtime': 'claude', 'name': 'My Skill', 'description': 'Does: things'})
                self.assertEqual(status, 200, created)
                path = created['path']
                self.assertEqual(Path(path), skills / 'my-skill' / 'SKILL.md')
                self.assertEqual(self.post('/api/skills/create', {'runtime': 'claude', 'name': 'my-skill'})[0], 400)
                status, read = self.post('/api/skills/read', {'path': path})
                self.assertEqual(status, 200); self.assertTrue(read['writable']); self.assertIn("'Does: things'", read['content'])
                status, deleted = self.post('/api/skills/delete', {'path': path})
                self.assertEqual(status, 200, deleted)
                self.assertFalse((skills / 'my-skill').exists())
                self.assertTrue(Path(deleted['trash']).exists())
                self.assertEqual(self.post('/api/skills/delete', {'path': str(skills / 'SKILL.md')})[0], 403)


if __name__ == '__main__':
    unittest.main()
