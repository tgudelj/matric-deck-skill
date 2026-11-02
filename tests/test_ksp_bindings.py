"""Synthetic KSP 1 bindings; no game, real settings or input execution."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/matric-decks/scripts'
sys.path.insert(0, str(SCRIPTS))
import game_bindings as games

FIXTURE = '''// Synthetic settings, not defaults
VERSION = synthetic
SYNTH_STAGE
{
 primary = Space
 secondary = Joystick1Button0
 group = 0
 switchState = Any
}
SYNTH_DIGIT {
 primary = Alpha3
 secondary = Keypad3
}
SYNTH_UNKNOWN
{
 primary = UnknownKey
 secondary = None
}
MODIFIER_KEY
{
 primary = LeftAlt
}
AXIS_SYNTH
{
 PRIMARY
 {
  name = Synthetic device
  axis = 2
  inv = True
  sensitivity = 0.75
  deadzone = 0.1
  modeMask = 3
 }
 SECONDARY
 {
  name = None
  axis = -1
 }
}
'''


class KspTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'settings.cfg'
        self.path.write_text(FIXTURE, encoding='utf-8', newline='\n')

    def test_keys_slots_unbound_unknown_and_modifier_only(self):
        report = games.inventory('ksp', [self.path], required=['missing', 'SYNTH_STAGE'])
        rows = report['bindings']
        self.assertEqual(rows[0]['candidate']['KeyCode'], 32)
        self.assertEqual(rows[1]['device'], 'Joystick1')
        self.assertEqual([b['candidate']['KeyCode'] for b in rows[2:4]], [51, 99])
        self.assertIsNone(rows[4]['candidate'])
        self.assertTrue(rows[5]['unbound'])
        self.assertIsNone(rows[6]['candidate'])
        self.assertEqual(report['missing_actions'], ['missing'])
        self.assertEqual(report['profiles'][0]['raw'], FIXTURE)
        self.assertEqual(self.path.read_text(), FIXTURE)

    def test_axis_settings_and_explicit_vjoy_mapping(self):
        report = games.inventory('ksp', [self.path])
        axis = report['bindings'][-2]
        self.assertEqual(axis['settings']['axis']['modeMask'], '3')
        self.assertIsNone(axis['candidate'])
        self.assertTrue(report['bindings'][-1]['unbound'])
        devices = {'Synthetic device': {'DeviceId': 1, 'buttons': 0, 'axes': [50], 'povs': 0,
                   'inputs': {'axis:2': {'kind': 'axis', 'axis': 50, 'invert': True}}}}
        candidate = games.inventory('ksp', [self.path], devices)['bindings'][-2]['candidate']
        self.assertEqual(candidate['Axis'], 50)
        self.assertTrue(candidate['InvertAxis'])

    def test_discovery_rejects_mod_settings_and_cli_no_overwrite(self):
        other = self.root / 'mod'
        other.mkdir()
        (other / 'settings.cfg').write_text('ModSettings\n{\n enabled = True\n}\n')
        self.assertEqual(len(games.discover('ksp', self.root)['candidates']), 1)
        output = self.root / 'report.json'
        args = [sys.executable, '-B', str(SCRIPTS / 'game_bindings.py'), 'inventory', '--game',
                'ksp', '--profile', str(self.path), '--output', str(output)]
        result = subprocess.run(args, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(output.read_text())['game'], 'ksp')
        self.assertEqual(subprocess.run(args, capture_output=True).returncode, 2)

    def test_invalid_syntax_and_legacy_axis(self):
        for text in ('Broken\n{', '}\n', 'Node\nOther\n{\n}', 'Node { primary = X }'):
            self.path.write_text(text)
            with self.assertRaises(ValueError):
                games.inventory('ksp', [self.path])
        self.path.write_text('AXIS_OLD\n{\n name = None\n id = None\n}\n')
        self.assertTrue(games.inventory('ksp', [self.path])['bindings'][0]['unbound'])

    def test_switch_state_preserved_without_automatic_tap(self):
        self.path.write_text(FIXTURE.replace('switchState = Any', 'switchState = Docking'))
        row = games.inventory('ksp', [self.path])['bindings'][0]
        self.assertIsNone(row['candidate'])
        self.assertIn(['switchState', 'Docking'], row['settings']['node']['values'])


if __name__ == '__main__':
    unittest.main()
