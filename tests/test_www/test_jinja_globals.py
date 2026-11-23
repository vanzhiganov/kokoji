import unittest

import kojiweb.util


class JinjaGlobalsTestCase(unittest.TestCase):
    def test_safevalue_alias_available(self):
        """Cheetah's ``SafeValue as S`` alias must survive the Jinja migration."""
        env = kojiweb.util._get_jinja_env()
        self.assertIs(env.globals.get('S'), kojiweb.util.SafeValue)
        rendered = env.from_string("{{ S(' class=\"tree\"') }}").render()
        self.assertEqual(rendered, ' class="tree"')


if __name__ == '__main__':
    unittest.main()
