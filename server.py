import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler

PORT = 1998
BASE_DIR = Path(__file__).parent.resolve()

# Import the scanner logic
sys.path.insert(0, str(BASE_DIR))
import scan_skills

def validated_skill_path(value):
    path = Path(value).expanduser().resolve()
    if path.name != 'SKILL.md' or not any(path.is_relative_to(root.resolve()) and path.parent != root.resolve() for root in scan_skills.writable_skill_roots().values()):
        raise ValueError('Only SKILL.md files inside configured skill directories can be managed')
    return path

class Win98SkillsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def do_GET(self):
        if self.path == '/api/skills/list':
            self.handle_list_skills()
        else:
            super().do_GET()

    def do_POST(self):
        if self.headers.get('Host') not in (f'localhost:{PORT}', f'127.0.0.1:{PORT}'):
            self.send_json({'error': 'Invalid host'}, 403)
            return
        origin = self.headers.get('Origin')
        if origin and origin not in (f'http://localhost:{PORT}', f'http://127.0.0.1:{PORT}'):
            self.send_json({'error': 'Invalid origin'}, 403)
            return
        content_len = int(self.headers.get('Content-Length', 0))
        if content_len < 0 or content_len > 1_048_576:
            self.send_json({'error': 'Request too large'}, 413)
            return
        post_data = self.rfile.read(content_len).decode('utf-8')
        try:
            req_json = json.loads(post_data) if post_data else {}
        except Exception:
            req_json = {}

        if not isinstance(req_json, dict):
            self.send_json({'error': 'Expected a JSON object'}, 400)
            return
        if self.path in ('/api/skills/read', '/api/skills/save', '/api/skills/delete', '/api/skills/open_folder'):
            try:
                req_json['path'] = str(validated_skill_path(req_json.get('path', '')))
            except (ValueError, OSError, TypeError):
                self.send_json({'error': 'Path outside configured skill directories'}, 403)
                return

        if self.path == '/api/skills/rescan':
            self.handle_rescan()
        elif self.path == '/api/skills/read':
            self.handle_read_skill(req_json)
        elif self.path == '/api/skills/save':
            self.handle_save_skill(req_json)
        elif self.path == '/api/skills/delete':
            self.handle_delete_skill(req_json)
        elif self.path == '/api/skills/create':
            self.handle_create_skill(req_json)
        elif self.path == '/api/skills/open_folder':
            self.handle_open_folder(req_json)
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'{"error": "Not found"}')

    def send_json(self, data, code=200):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

    def handle_list_skills(self):
        json_path = BASE_DIR / 'skills_data.json'
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding='utf-8'))
        else:
            scan_skills.main()
            data = json.loads((BASE_DIR / 'skills_data.json').read_text(encoding='utf-8'))
        self.send_json(data)

    def handle_rescan(self):
        try:
            scan_skills.main()
            data = json.loads((BASE_DIR / 'skills_data.json').read_text(encoding='utf-8'))
            self.send_json({'success': True, 'data': data})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_read_skill(self, req):
        file_path = req.get('path', '')
        p = Path(file_path)
        if p.exists() and p.is_file():
            try:
                content = p.read_text(encoding='utf-8', errors='ignore')
                self.send_json({'success': True, 'content': content, 'name': p.parent.name})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        else:
            self.send_json({'success': False, 'error': 'File not found'}, 404)

    def handle_save_skill(self, req):
        file_path = req.get('path', '')
        new_content = req.get('content', '')
        p = Path(file_path)
        if p.exists() and p.is_file():
            try:
                p.write_text(new_content, encoding='utf-8')
                scan_skills.main()
                self.send_json({'success': True})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        else:
            self.send_json({'success': False, 'error': 'File not found'}, 404)

    def handle_delete_skill(self, req):
        file_path = req.get('path', '')
        p = Path(file_path)
        # Safety checks: must end in SKILL.md and be inside approved directories
        if not p.name.endswith('SKILL.md'):
            self.send_json({'success': False, 'error': 'Target is not a valid SKILL.md file'}, 400)
            return

        skill_dir = p.parent
        # Disallow deleting root directories
        if len(skill_dir.parts) < 3:
            self.send_json({'success': False, 'error': 'Cannot delete root directory'}, 400)
            return

        try:
            shutil.rmtree(skill_dir)
            scan_skills.main()
            data = json.loads((BASE_DIR / 'skills_data.json').read_text(encoding='utf-8'))
            self.send_json({'success': True, 'deleted': str(skill_dir), 'data': data})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_create_skill(self, req):
        runtime = req.get('runtime', 'antigravity').lower()
        name = req.get('name', '').strip()
        description = req.get('description', '').strip()

        if not name:
            self.send_json({'success': False, 'error': 'Skill name is required'}, 400)
            return

        # Sanitize name
        clean_name = "".join([c if c.isalnum() or c in '-_' else '-' for c in name]).lower()

        if runtime == 'claude':
            target_dir = (scan_skills.CLAUDE_ROOT / 'skills') / clean_name
        elif runtime == 'codex':
            target_dir = (scan_skills.CODEX_ROOT / 'skills') / clean_name
        else: # antigravity
            target_dir = scan_skills.WORKSPACE_SKILLS / clean_name

        if target_dir.exists():
            self.send_json({'success': False, 'error': f'Skill "{clean_name}" already exists!'}, 400)
            return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
            skill_md = target_dir / 'SKILL.md'
            content = f"""---
name: {clean_name}
description: "{description if description else 'Description of ' + clean_name}"
---

# {name}

## Overview
{description if description else 'Provide a clear explanation of this skill here.'}

## Instructions
1. Step 1...
2. Step 2...
"""
            skill_md.write_text(content, encoding='utf-8')
            scan_skills.main()
            data = json.loads((BASE_DIR / 'skills_data.json').read_text(encoding='utf-8'))
            self.send_json({'success': True, 'path': str(skill_md), 'data': data})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_open_folder(self, req):
        file_path = req.get('path', '')
        p = Path(file_path)
        if p.exists():
            try:
                # Use Windows explorer to highlight the file
                subprocess.Popen(['explorer.exe', f'/select,{str(p)}'])
                self.send_json({'success': True})
            except Exception as e:
                self.send_json({'success': False, 'error': str(e)}, 500)
        else:
            self.send_json({'success': False, 'error': 'Path does not exist'}, 404)

def run():
    server_address = ('127.0.0.1', PORT)
    httpd = HTTPServer(server_address, Win98SkillsHandler)
    print(f"Windows 98 Skills Explorer Server running at http://localhost:{PORT}")
    httpd.serve_forever()

if __name__ == '__main__':
    run()
