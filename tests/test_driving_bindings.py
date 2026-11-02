"""Synthetic driving input fixtures; no real profiles or input execution."""
import json
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/matric-decks/scripts'
sys.path.insert(0, str(SCRIPTS))
import game_bindings as games


class DrivingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def save(self, name, data):
        path = self.root / name
        path.write_bytes(data if isinstance(data, bytes) else data.encode('utf-8'))
        return path

    def test_scs_simple_keys_complex_expressions_and_source_preservation(self):
        text = 'SiiNunit\n{\nconfig_lines[0]: "device joy synthetic"\nconfig_lines[1]: "mix horn `keyboard.h?0`"\nconfig_lines[2]: "mix lights `keyboard.h?0 | joy.b1?0`"\nconfig_lines[3]: "mix unused `0`"\n}'
        path = self.save('controls.sii', text)
        report = games.inventory('ets2', [path], required=['horn', 'missing'])
        self.assertEqual(report['bindings'][0]['candidate']['KeyCode'], 72)
        self.assertIsNone(report['bindings'][1]['candidate'])
        self.assertTrue(report['bindings'][2]['unbound'])
        self.assertEqual(report['profiles'][0]['raw'], text)
        self.assertEqual(report['missing_actions'], ['missing'])
        self.assertEqual(len(games.discover('ets2', self.root)['candidates']), 1)
        self.assertEqual(path.read_text(), text)

    def test_farming_keyboard_chord_devices_components_and_unbound(self):
        data = '<inputBinding version="1"><devices><device id="SYNTHETIC"/></devices><actionBinding action="SYNTH_HORN"><binding device="KB_MOUSE_DEFAULT" input="KEY_lshift KEY_h" index="1"/><binding device="SYNTHETIC" input="AXIS_1" axisComponent="-" inputComponent="+" neutralInput="0" index="2"/><binding device="KB_MOUSE_DEFAULT" input="" index="3"/></actionBinding></inputBinding>'
        path = self.save('inputBinding.xml', data)
        rows = games.inventory('farmingsimulator', [path])['bindings']
        self.assertEqual(rows[0]['candidate']['Modifiers'], ['LSHIFT'])
        self.assertIsNone(rows[1]['candidate'])
        self.assertEqual(rows[1]['settings']['binding']['axisComponent'], '-')
        self.assertTrue(rows[2]['unbound'])
        self.assertEqual(len(games.discover('farmingsimulator', self.root)['candidates']), 1)

    def test_acc_context_modifiers_long_presses_and_raw_axes(self):
        doc = {'keyboardSettings': {'raceCommandButtonList': [
            {'actionType': 'SynthHorn', 'key': {'key': 'H', 'bCtrl': True}},
            {'actionType': 'SynthClear', 'key': {'key': 'None'}}]},
            'commandDevices': [{'raceCommandButtonList': [{'buttonIndex': 3,
                'instantActionCode': 'SynthLights', 'extendedActionCode': 'SynthLong',
                'extendedTime': 2, 'pinkieInstanceActionCode': 'SynthPinkie'}],
                'axisList': [{'axisCode': 'SynthBrake', 'minRange': 1, 'maxRange': -1}]}]}
        path = self.save('controls.json', json.dumps(doc).encode('utf-16'))
        report = games.inventory('acc', [path])
        self.assertEqual(report['bindings'][0]['candidate']['Modifiers'], ['LCONTROL'])
        self.assertTrue(report['bindings'][1]['unbound'])
        self.assertEqual(len(report['bindings']), 5)
        self.assertTrue(all(b['candidate'] is None for b in report['bindings'][2:]))
        self.assertEqual(report['profiles'][0]['document'], doc)
        self.save('unrelated.json', '{"foo":1}')
        self.assertEqual(len(games.discover('acc', self.root)['candidates']), 1)
        doc['keyboardSettings']['raceCommandButtonList'] = [
            {'actionType': 'UnknownSchema', 'key': 'H'},
            {'actionType': 'BadModifier', 'key': {'key': 'H', 'bCtrl': 'false'}}]
        rows = games.inventory('acc', [self.save('controls.json', json.dumps(doc))])['bindings']
        self.assertFalse(rows[0]['unbound'])
        self.assertIsNone(rows[0]['candidate'])
        self.assertIsNone(rows[1]['candidate'])

    def iracing(self, version=20, kind=4):
        record = b'SyntheticHorn\0' + struct.pack('<5I', 0, 1, kind, 72, 0xC0000) + bytes(48)
        payload = b'opaque' + b'LRTC' + struct.pack('<II', 8, len(record)) + record + b'  '
        return b'GFCC' + struct.pack('<II', version, len(payload)) + payload

    def test_iracing_binary_records_are_bounded_and_remain_manual(self):
        data = self.iracing()
        path = self.save('controls.cfg', data)
        report = games.inventory('iracing', [path])
        binding = report['bindings'][0]
        self.assertEqual(binding['action'], 'SyntheticHorn')
        self.assertEqual(binding['settings']['modifiers'], 0xC0000)
        self.assertIsNone(binding['candidate'])
        self.assertEqual(report['profiles'][0]['global_hex'], b'opaque'.hex())
        self.assertEqual(len(games.discover('iracing', self.root)['candidates']), 1)
        self.assertEqual(path.read_bytes(), data)
        for invalid in (data[:-1], self.iracing(version=21), b'GFCC', b'garbage'):
            path.write_bytes(invalid)
            with self.assertRaises(ValueError):
                games.inventory('iracing', [path])

    def test_invalid_documents_no_guessed_inputs_and_size_limits(self):
        for game, name, data in [('ets2', 'controls.sii', 'ScsC encrypted'),
                                  ('acc', 'controls.json', '{}'),
                                  ('farmingsimulator', 'inputBinding.xml', '<wrong/>')]:
            with self.assertRaises(ValueError):
                games.inventory(game, [self.save(name, data)])
        path = self.save('controls.cfg', b'')
        with path.open('wb') as stream:
            stream.truncate(games.MAX_BYTES + 1)
        with self.assertRaises(ValueError):
            games.inventory('iracing', [path])

    def test_cli_game_choices_output_no_overwrite_and_conflicts(self):
        path = self.save('inputBinding.xml', '<inputBinding><actionBinding action="A"><binding device="KB_MOUSE_DEFAULT" input="KEY_h"/></actionBinding><actionBinding action="B"><binding device="KB_MOUSE_DEFAULT" input="KEY_h"/></actionBinding></inputBinding>')
        output = self.root / 'report.json'
        cmd = [sys.executable, '-B', str(SCRIPTS / 'game_bindings.py'), 'inventory', '--game',
               'farmingsimulator', '--profile', str(path), '--output', str(output)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(output.read_text())['conflicts'])
        self.assertEqual(subprocess.run(cmd, capture_output=True).returncode, 2)


if __name__ == '__main__':
    unittest.main()
