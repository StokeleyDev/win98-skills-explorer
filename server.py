import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import threading
from datetime import datetime
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PORT = 1998
BASE_DIR = Path(__file__).parent.resolve()
TRASH_DIR = BASE_DIR / '.trash'

# Import the scanner logic
sys.path.insert(0, str(BASE_DIR))
import scan_skills

ALLOWED_HOSTS = (f'localhost:{PORT}', f'127.0.0.1:{PORT}')
ALLOWED_ORIGINS = tuple(f'http://{host}' for host in ALLOWED_HOSTS)
STATIC_FILES = {'/index.html', '/app.js', '/app.css', '/98.css', '/skills_data.js'}
STATIC_PREFIXES = ('/fonts/converted/', '/docs/')
READ_ROUTES = ('/api/skills/read', '/api/skills/open_folder')
WRITE_ROUTES = ('/api/skills/save', '/api/skills/delete')

# One scan at a time: requests are served on threads, and the scanner rewrites shared files.
SCAN_LOCK = threading.Lock()


def rescan():
    with SCAN_LOCK:
        return scan_skills.main()


def _inside(path, root):
    root = root.resolve()
    return path.is_relative_to(root) and path.parent != root


def validated_skill_path(value, write=False):
    """Resolve a SKILL.md path. Reads are allowed anywhere under a configured scan root;
    writes and deletes only under the runtime's own skills directory."""
    if not isinstance(value, (str, os.PathLike)) or not str(value):
        raise ValueError('Path is required')
    path = Path(value).expanduser().resolve()
    if path.name != 'SKILL.md':
        raise ValueError('Only SKILL.md files can be managed')
    roots = list(scan_skills.writable_skill_roots().values())
    if not write:
        roots += scan_skills.configured_roots()
    if not any(_inside(path, root) for root in roots):
        raise ValueError('Path outside configured skill directories')
    return path


def atomic_write(path, data):
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix='.tmp-', suffix='.part')
    try:
        with os.fdopen(fd, 'wb') as f:
            f.write(data)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def move_to_trash(folder):
    """Send to the system Recycle Bin when send2trash is installed, else to ./.trash."""
    try:
        from send2trash import send2trash
        send2trash(str(folder))
        return 'Recycle Bin'
    except ImportError:
        TRASH_DIR.mkdir(exist_ok=True)
        target = TRASH_DIR / f"{datetime.now():%Y%m%d-%H%M%S}-{folder.name}"
        shutil.move(str(folder), str(target))
        return str(target)


class Win98SkillsHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(BASE_DIR), **kwargs)

    def host_ok(self):
        if self.headers.get('Host') not in ALLOWED_HOSTS:
            self.send_json({'error': 'Invalid host'}, 403)
            return False
        return True

    def do_HEAD(self):
        self.send_error(405)

    def do_GET(self):
        if not self.host_ok():
            return
        route = self.path.split('?', 1)[0]
        if route == '/api/skills/list':
            self.handle_list_skills()
        elif route == '/api/skills/config':
            self.handle_get_config()
        elif route == '/' or route in STATIC_FILES or (route.startswith(STATIC_PREFIXES) and '..' not in route):
            super().do_GET()
        else:
            self.send_json({'error': 'Not found'}, 404)

    def do_POST(self):
        if not self.host_ok():
            return
        origin = self.headers.get('Origin')
        if origin and origin not in ALLOWED_ORIGINS:
            self.send_json({'error': 'Invalid origin'}, 403)
            return
        try:
            content_len = int(self.headers.get('Content-Length', 0))
        except ValueError:
            self.send_json({'error': 'Invalid Content-Length'}, 400)
            return
        if content_len < 0 or content_len > 1_048_576:
            self.send_json({'error': 'Request too large'}, 413)
            return
        try:
            post_data = self.rfile.read(content_len).decode('utf-8')
            req_json = json.loads(post_data) if post_data else {}
        except (UnicodeError, json.JSONDecodeError):
            self.send_json({'error': 'Invalid JSON'}, 400)
            return

        if not isinstance(req_json, dict):
            self.send_json({'error': 'Expected a JSON object'}, 400)
            return
        if self.path in READ_ROUTES + WRITE_ROUTES:
            try:
                req_json['path'] = str(validated_skill_path(req_json.get('path'), write=self.path in WRITE_ROUTES))
            except (ValueError, OSError, TypeError):
                self.send_json({'success': False, 'error': 'Path outside configured skill directories or read-only'}, 403)
                return

        handlers = {
            '/api/skills/rescan': lambda: self.handle_rescan(),
            '/api/skills/config': lambda: self.handle_save_config(req_json),
            '/api/skills/read': lambda: self.handle_read_skill(req_json),
            '/api/skills/save': lambda: self.handle_save_skill(req_json),
            '/api/skills/delete': lambda: self.handle_delete_skill(req_json),
            '/api/skills/create': lambda: self.handle_create_skill(req_json),
            '/api/skills/open_folder': lambda: self.handle_open_folder(req_json),
        }
        handler = handlers.get(self.path)
        if handler:
            handler()
        else:
            self.send_json({'error': 'Not found'}, 404)

    def send_json(self, data, code=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def handle_list_skills(self):
        json_path = BASE_DIR / 'skills_data.json'
        if json_path.exists():
            data = json.loads(json_path.read_text(encoding='utf-8'))
        else:
            data = rescan()
        self.send_json(data)

    def handle_rescan(self):
        try:
            self.send_json({'success': True, 'data': rescan()})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_get_config(self):
        try:
            self.send_json({'success': True, 'config': scan_skills.load_config()})
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            self.send_json({'success': False, 'error': str(exc)}, 400)

    def handle_save_config(self, req):
        try:
            config = scan_skills.validate_config(req.get('config'))
            atomic_write(scan_skills.CONFIG_PATH, (json.dumps(config, ensure_ascii=False, indent=2) + '\n').encode('utf-8'))
            self.send_json({'success': True, 'data': rescan()})
        except (OSError, ValueError, TypeError) as exc:
            self.send_json({'success': False, 'error': str(exc)}, 400)

    def handle_read_skill(self, req):
        p = Path(req.get('path', ''))
        try:
            raw = p.read_bytes()
            content = raw.decode('utf-8-sig')
            self.send_json({'success': True, 'content': content, 'name': p.parent.name,
                            'version': hashlib.sha256(raw).hexdigest(),
                            'writable': scan_skills.is_writable(p)})
        except (OSError, UnicodeError) as exc:
            self.send_json({'success': False, 'error': str(exc)}, 404)

    def handle_save_skill(self, req):
        p = Path(req.get('path', ''))
        content = req.get('content')
        expected = req.get('version')
        if not isinstance(content, str) or not isinstance(expected, str):
            self.send_json({'success': False, 'error': 'File content and version are required.'}, 400)
            return
        try:
            current = p.read_bytes()
            if hashlib.sha256(current).hexdigest() != expected:
                self.send_json({'success': False, 'conflict': True,
                                'error': 'The file changed on disk since it was opened. Your text has not been saved.'}, 409)
                return
            # Preserve a UTF-8 BOM and the file's predominant line ending.
            newline = '\r\n' if current.count(b'\r\n') > current.count(b'\n') / 2 else '\n'
            normalized = content.replace('\r\n', '\n').replace('\r', '\n')
            raw = (b'\xef\xbb\xbf' if current.startswith(b'\xef\xbb\xbf') else b'') + normalized.replace('\n', newline).encode('utf-8')
            atomic_write(p, raw)
            version = hashlib.sha256(raw).hexdigest()
        except (OSError, UnicodeError) as exc:
            self.send_json({'success': False, 'error': str(exc)}, 500)
            return
        try:
            self.send_json({'success': True, 'version': version, 'data': rescan()})
        except Exception as exc:
            self.send_json({'success': True, 'version': version, 'warning': f'File saved, but rescan failed: {exc}'})

    def handle_delete_skill(self, req):
        skill_dir = Path(req['path']).parent
        try:
            where = move_to_trash(skill_dir)
            self.send_json({'success': True, 'deleted': str(skill_dir), 'trash': where, 'data': rescan()})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_create_skill(self, req):
        runtime = str(req.get('runtime', 'antigravity')).lower()
        name = str(req.get('name', '')).strip()
        description = str(req.get('description', '')).strip()
        roots = scan_skills.writable_skill_roots()
        if runtime not in roots:
            self.send_json({'success': False, 'error': f'Unknown runtime "{runtime}"'}, 400)
            return

        clean_name = ''.join(c if c.isalnum() or c in '-_' else '-' for c in name).lower().strip('-_')
        if not clean_name:
            self.send_json({'success': False, 'error': 'Skill name must contain letters or digits'}, 400)
            return

        target_dir = roots[runtime] / clean_name
        if target_dir.exists():
            self.send_json({'success': False, 'error': f'Skill "{clean_name}" already exists!'}, 400)
            return

        try:
            target_dir.mkdir(parents=True)
            skill_md = target_dir / 'SKILL.md'
            metadata = scan_skills.yaml.safe_dump(
                {'name': clean_name, 'description': description or 'Description of ' + clean_name},
                allow_unicode=True, sort_keys=False)
            content = f"---\n{metadata}---\n\n# {name}\n\n## Overview\n{description or 'Provide a clear explanation of this skill here.'}\n\n## Instructions\n1. Step 1...\n2. Step 2...\n"
            skill_md.write_text(content, encoding='utf-8')
            self.send_json({'success': True, 'path': str(skill_md), 'data': rescan()})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)

    def handle_open_folder(self, req):
        p = Path(req.get('path', ''))
        if not p.exists():
            self.send_json({'success': False, 'error': 'Path does not exist'}, 404)
            return
        try:
            if sys.platform == 'win32':
                subprocess.Popen(['explorer.exe', f'/select,{p}'])
            elif sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', str(p)])
            else:
                subprocess.Popen(['xdg-open', str(p.parent)])
            self.send_json({'success': True})
        except Exception as e:
            self.send_json({'success': False, 'error': str(e)}, 500)


def run():
    httpd = ThreadingHTTPServer(('127.0.0.1', PORT), Win98SkillsHandler)
    print(f"Windows 98 Skills Explorer Server running at http://localhost:{PORT}")
    httpd.serve_forever()


if __name__ == '__main__':
    run()
