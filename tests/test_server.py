import unittest
from pathlib import Path
from unittest.mock import patch

import server
import scan_skills


class SkillBoundaryTests(unittest.TestCase):
    def test_only_nested_skill_files_are_allowed(self):
        root = (Path.cwd() / 'test-skill-root').resolve()
        with patch.object(scan_skills, 'writable_skill_roots', return_value={'codex': root}):
            self.assertEqual(server.validated_skill_path(root / 'example' / 'SKILL.md'), root / 'example' / 'SKILL.md')
            for invalid in (root / 'SKILL.md', root / 'example' / 'config.json', root / '..' / 'outside' / 'SKILL.md'):
                with self.subTest(path=invalid):
                    with self.assertRaises(ValueError):
                        server.validated_skill_path(invalid)


if __name__ == '__main__':
    unittest.main()
