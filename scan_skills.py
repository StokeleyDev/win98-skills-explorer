import os
import re
import json
from pathlib import Path

HOME = Path.home()
WORKSPACE_SKILLS = Path(os.getenv('WORKSPACE_SKILLS_DIR', str(Path.cwd().parent / '.agents' / 'skills'))).expanduser().resolve()
CODEX_ROOT = Path(os.getenv('CODEX_HOME', str(HOME / '.codex'))).expanduser().resolve()
CLAUDE_ROOT = Path(os.getenv('CLAUDE_CONFIG_DIR', str(HOME / '.claude'))).expanduser().resolve()
GEMINI_ROOT = Path(os.getenv('GEMINI_HOME', str(HOME / '.gemini'))).expanduser().resolve()

def writable_skill_roots():
    return {'antigravity': WORKSPACE_SKILLS, 'codex': CODEX_ROOT / 'skills', 'claude': CLAUDE_ROOT / 'skills'}

def parse_skill(p, source_label):
    try:
        content = p.read_text(encoding='utf-8', errors='ignore')
        m = re.match(r'^---\s*\n(.*?)\n---', content, re.DOTALL)
        name = p.parent.name
        desc = ''
        if m:
            fm = m.group(1)
            name_m = re.search(r'^name:\s*(.+)$', fm, re.MULTILINE)
            if name_m:
                name = name_m.group(1).strip('"\' ')
            
            desc_m = re.search(r'^description:\s*(?:>-\s*|>\s*|\|\s*)?\n?([^\n].*?)(?=\n[a-zA-Z0-9_-]+:|\Z)', fm, re.DOTALL | re.MULTILINE)
            if desc_m:
                desc = desc_m.group(1).strip('"\' ')
                desc = re.sub(r'\s+', ' ', desc)

        if not desc:
            lines = [l.strip() for l in content.split('\n') if l.strip() and not l.startswith('#') and not l.startswith('---')]
            desc = lines[0] if lines else 'No description available.'

        short_desc = desc.split('. ')[0]
        if len(short_desc) > 130:
            short_desc = short_desc[:127] + '...'
        elif not short_desc.endswith('.'):
            short_desc += '.'

        return {
            'name': name,
            'short_desc': short_desc,
            'full_desc': desc,
            'path': str(p),
            'source': source_label,
            'folder': p.parent.name
        }
    except Exception as e:
        return {
            'name': p.parent.name,
            'short_desc': f'Error reading: {e}',
            'full_desc': str(e),
            'path': str(p),
            'source': source_label,
            'folder': p.parent.name
        }

def collect_unique(paths_with_sources):
    seen = {}
    for p, source in paths_with_sources:
        parsed = parse_skill(p, source)
        key = parsed['name'].lower()
        if key not in seen:
            seen[key] = parsed
        else:
            if 'cache' in seen[key]['path'] and 'cache' not in parsed['path']:
                seen[key] = parsed
    return sorted(list(seen.values()), key=lambda x: x['name'].lower())

def scan_all_agents():
    agents = []

    # 1. Built-in Antigravity Subagents
    agents.append({
        'name': 'hallmark-designer',
        'runtime': 'Antigravity',
        'role': 'Anti-AI-Slop Designer & Auditor',
        'description': 'Specialized anti-AI-slop UI designer and auditor based on Hallmark. Audits code, runs sloplint, and crafts bespoke layouts.',
        'model': 'Gemini 3.8 Flash (Inherit)',
        'tools': ['Read/Write/Edit', 'Run Command (sloplint)', 'MCP Tools', 'Search Web'],
        'status': 'Active',
        'path': str(WORKSPACE_SKILLS / 'hallmark')
    })
    agents.append({
        'name': 'research',
        'runtime': 'Antigravity',
        'role': 'Codebase & Web Researcher',
        'description': 'Research subagent with read-only tools for exploring codebase, searching web, and analyzing documentation.',
        'model': 'Gemini 3.8 Flash (Inherit)',
        'tools': ['Search Web', 'Read Files', 'Code Search'],
        'status': 'Active',
        'path': str(GEMINI_ROOT / 'antigravity' / 'builtin' / 'agents' / 'research')
    })
    agents.append({
        'name': 'image-generator',
        'runtime': 'Antigravity',
        'role': 'Image Synthesis & Visuals',
        'description': 'Generates and edits images from a brief and replies with saved file paths.',
        'model': 'Gemini 3.8 Flash (Inherit)',
        'tools': ['Image Generation', 'Write Files'],
        'status': 'Standby',
        'path': str(GEMINI_ROOT / 'antigravity' / 'builtin' / 'agents' / 'image-generator')
    })
    agents.append({
        'name': 'self',
        'runtime': 'Antigravity',
        'role': 'Full Pair Programmer Subagent',
        'description': 'Subagent that inherits parent configuration, all write/run tools, system prompt and model for complex delegation.',
        'model': 'Gemini 3.8 Flash (Inherit)',
        'tools': ['Full Workspace Tools', 'Subagent Management', 'MCP Tools'],
        'status': 'Active',
        'path': str(GEMINI_ROOT / 'antigravity' / 'builtin' / 'agents' / 'self')
    })

    # 2. Project agents from c:\bat\.agents\skills\*\agents\openai.yaml
    seen_names = set(a['name'] for a in agents)
    for yaml_path in WORKSPACE_SKILLS.rglob('openai.yaml'):
        try:
            skill_name = yaml_path.parent.parent.name
            agent_name = f"{skill_name}-agent"
            if agent_name not in seen_names:
                text = yaml_path.read_text(encoding='utf-8', errors='ignore')
                desc = f"Specialized OpenAI/Codex agent for {skill_name}"
                for line in text.split('\n'):
                    if 'description:' in line:
                        desc = line.split('description:')[1].strip('"\' ')
                agents.append({
                    'name': agent_name,
                    'runtime': 'Workspace (.agents)',
                    'role': f'{skill_name.capitalize()} Specialist',
                    'description': desc,
                    'model': 'GPT-4o / Codex',
                    'tools': ['Workspace Tools', 'File Edit'],
                    'status': 'Ready',
                    'path': str(yaml_path)
                })
                seen_names.add(agent_name)
        except Exception:
            pass

    # 3. Claude Plugins Agents
    claude_plugins = (CLAUDE_ROOT / 'plugins')
    if claude_plugins.exists():
        for p in claude_plugins.rglob('plugin.json'):
            try:
                data = json.loads(p.read_text(encoding='utf-8', errors='ignore'))
                name = data.get('name', p.parent.name)
                agent_name = f"claude-{name}"
                if agent_name not in seen_names:
                    agents.append({
                        'name': agent_name,
                        'runtime': 'Claude Code',
                        'role': f'Claude {name.capitalize()} Agent',
                        'description': data.get('description', f'Plugin agent for {name}'),
                        'model': 'Claude 3.7 Sonnet',
                        'tools': ['Claude Tools', 'Bash', 'File Edit'],
                        'status': 'Ready',
                        'path': str(p)
                    })
                    seen_names.add(agent_name)
            except Exception:
                pass

    return agents

def main():
    print("Scanning installed skills & agents...")

    # 1. Antigravity Skills
    agy_paths = []
    for p in WORKSPACE_SKILLS.rglob('SKILL.md'):
        agy_paths.append((p, 'Workspace (.agents)'))
    for p in (GEMINI_ROOT / 'antigravity' / 'builtin' / 'skills').rglob('SKILL.md'):
        agy_paths.append((p, 'Antigravity Built-in'))
    for p in (GEMINI_ROOT / 'config' / 'plugins').rglob('SKILL.md'):
        agy_paths.append((p, 'Gemini Plugin'))
    for p in (GEMINI_ROOT / 'config' / 'skills').rglob('SKILL.md'):
        agy_paths.append((p, 'Gemini Global'))

    antigravity_skills = collect_unique(agy_paths)

    # 2. Codex Skills
    codex_paths = []
    codex_root = CODEX_ROOT
    if codex_root.exists():
        for p in codex_root.rglob('SKILL.md'):
            codex_paths.append((p, 'Codex System'))

    codex_skills = collect_unique(codex_paths)

    # 3. Claude Skills
    claude_paths = []
    claude_root = CLAUDE_ROOT
    if claude_root.exists():
        for p in claude_root.rglob('SKILL.md'):
            claude_paths.append((p, 'Claude Config'))

    claude_skills = collect_unique(claude_paths)

    # 4. Agents
    agents = scan_all_agents()

    data = {
        'antigravity': antigravity_skills,
        'codex': codex_skills,
        'claude': claude_skills,
        'agents': agents,
        'updated_at': __import__('datetime').date.today().isoformat()
    }

    out_dir = Path(__file__).parent
    json_path = out_dir / 'skills_data.json'
    js_path = out_dir / 'skills_data.js'

    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    json_path.write_text(json_str, encoding='utf-8')
    js_path.write_text(f"window.SKILLS_DATA = {json_str};\n", encoding='utf-8')

    print(f"Done!")
    print(f"  Antigravity: {len(antigravity_skills)} skills")
    print(f"  Codex:       {len(codex_skills)} skills")
    print(f"  Claude:      {len(claude_skills)} skills")
    print(f"  Agents:      {len(agents)} agents")
    print(f"  Saved JSON:  {json_path}")
    print(f"  Saved JS:    {js_path}")

if __name__ == '__main__':
    main()
