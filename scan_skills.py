import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR / 'vendor'))
import yaml

HOME = Path.home()
WORKSPACE_SKILLS = Path(os.getenv('WORKSPACE_SKILLS_DIR', str(Path.cwd().parent / '.agents' / 'skills'))).expanduser().resolve()
CODEX_ROOT = Path(os.getenv('CODEX_HOME', str(HOME / '.codex'))).expanduser().resolve()
CLAUDE_ROOT = Path(os.getenv('CLAUDE_CONFIG_DIR', str(HOME / '.claude'))).expanduser().resolve()
GEMINI_ROOT = Path(os.getenv('GEMINI_HOME', str(HOME / '.gemini'))).expanduser().resolve()

def writable_skill_roots():
    return {'antigravity': WORKSPACE_SKILLS, 'codex': CODEX_ROOT / 'skills', 'claude': CLAUDE_ROOT / 'skills'}

CONFIG_PATH = BASE_DIR / 'scan_config.json'
RUNTIMES = ('antigravity', 'codex', 'claude')
DEFAULT_CONFIG = {'roots': [
    {'runtime': 'antigravity', 'source': 'Workspace (.agents)', 'path': str(WORKSPACE_SKILLS)},
    {'runtime': 'antigravity', 'source': 'Antigravity Built-in', 'path': str(GEMINI_ROOT / 'antigravity' / 'builtin' / 'skills')},
    {'runtime': 'antigravity', 'source': 'Gemini Plugin', 'path': str(GEMINI_ROOT / 'config' / 'plugins')},
    {'runtime': 'antigravity', 'source': 'Gemini Global', 'path': str(GEMINI_ROOT / 'config' / 'skills')},
    {'runtime': 'codex', 'source': 'Codex skills and cache', 'path': str(CODEX_ROOT)},
    {'runtime': 'claude', 'source': 'Claude Config', 'path': str(CLAUDE_ROOT)},
]}

def validate_config(config):
    if not isinstance(config, dict) or not isinstance(config.get('roots'), list):
        raise ValueError('Configuration must contain a roots array.')
    for i, root in enumerate(config['roots'], 1):
        if not isinstance(root, dict) or root.get('runtime') not in RUNTIMES:
            raise ValueError(f'Root {i}: runtime must be antigravity, codex or claude.')
        if any(not isinstance(root.get(key), str) or not root[key].strip() for key in ('source', 'path')):
            raise ValueError(f'Root {i}: source and path must be non-empty strings.')
        expanded = os.path.expandvars(os.path.expanduser(root['path']))
        if not Path(expanded).is_absolute():
            raise ValueError(f'Root {i}: path must be absolute after expanding environment variables.')
    return config

def load_config():
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG
    return validate_config(json.loads(CONFIG_PATH.read_text(encoding='utf-8-sig')))

def parse_skill(path, source, errors=None):
    errors = errors if errors is not None else []
    name, desc = path.parent.name, ''
    try:
        content = path.read_text(encoding='utf-8-sig')
        match = re.match(r'\A---[ \t]*\r?\n(.*?)^---[ \t]*(?:\r?\n|$)', content, re.DOTALL | re.MULTILINE)
        if match:
            try:
                meta = yaml.safe_load(match.group(1)) or {}
                if not isinstance(meta, dict):
                    raise ValueError('Front matter must be a YAML mapping')
                if meta.get('name') is not None:
                    if not isinstance(meta['name'], str): raise ValueError('name must be a string')
                    name = meta['name']
                if meta.get('description') is not None:
                    if not isinstance(meta['description'], str): raise ValueError('description must be a string')
                    desc = meta['description'].strip()
            except (yaml.YAMLError, ValueError) as exc:
                errors.append({'path': str(path), 'message': f'Invalid front matter: {exc}'})
        elif content.startswith('---'):
            errors.append({'path': str(path), 'message': 'Front matter has no closing --- delimiter.'})
        if not desc:
            body = content[match.end():] if match else content
            lines = [line.strip() for line in body.splitlines() if line.strip() and not line.startswith(('#', '---'))]
            desc = lines[0] if lines else 'No description available.'
    except (OSError, UnicodeError) as exc:
        errors.append({'path': str(path), 'message': str(exc)})
        desc = f'Error reading file: {exc}'
    short = re.sub(r'\s+', ' ', desc).split('. ')[0]
    if len(short) > 130: short = short[:127] + '...'
    elif not short.endswith('.'): short += '.'
    return {'name': name, 'short_desc': short, 'full_desc': desc, 'path': str(path), 'source': source, 'folder': path.parent.name}

def scan(config):
    data = {key: [] for key in RUNTIMES}
    errors, seen = [], {key: set() for key in RUNTIMES}
    for root in validate_config(config)['roots']:
        path = Path(os.path.expandvars(os.path.expanduser(root['path'])))
        if not path.is_dir():
            errors.append({'path': str(path), 'message': 'Configured directory does not exist or is not accessible.'})
            continue
        def onerror(exc):
            errors.append({'path': str(exc.filename or path), 'message': str(exc)})
        for folder, dirs, files in os.walk(path, onerror=onerror, followlinks=False):
            for filename in files:
                if filename != 'SKILL.md': continue
                skill_path = Path(folder) / filename
                try: key = str(skill_path.resolve()).casefold()
                except OSError as exc:
                    errors.append({'path': str(skill_path), 'message': str(exc)}); continue
                runtime = root['runtime']
                if key in seen[runtime]: continue
                seen[runtime].add(key)
                data[runtime].append(parse_skill(skill_path, root['source'], errors))
    for key in RUNTIMES:
        data[key].sort(key=lambda item: (item['name'].casefold(), item['path'].casefold()))
    data.update(agents=[], agents_notice='Agent runtime information is not available from this scanner.',
                updated_at=datetime.now(timezone.utc).isoformat(), scan_errors=errors)
    return data

def main():
    data = scan(load_config())
    text = json.dumps(data, ensure_ascii=False, indent=2)
    (BASE_DIR / 'skills_data.json').write_text(text, encoding='utf-8')
    (BASE_DIR / 'skills_data.js').write_text(f'window.SKILLS_DATA = {text};\n', encoding='utf-8')
    print(f"Scan complete: {sum(len(data[k]) for k in RUNTIMES)} skills, {len(data['scan_errors'])} errors")
    return data

if __name__ == '__main__': main()
