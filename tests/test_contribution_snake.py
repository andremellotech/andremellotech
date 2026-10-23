"""Preserve the official snk animation while adapting its surrounding panel."""
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image, ImageSequence
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from themes import THEMES
from snake_fixture import write_snake_fixture


class ContributionSnake(unittest.TestCase):
    def setUp(self):
        self.scratch = Path(__file__).resolve().parents[1]/'work/snake-unit-tests'
        self.scratch.mkdir(parents=True, exist_ok=True)

    def test_preserves_source_motion_duration_loop_and_transparent_surround(self):
        from contribution_snake import render_snake
        with tempfile.TemporaryDirectory(dir=self.scratch) as directory:
            root = Path(directory)
            write_snake_fixture(root)
            render_snake(root, THEMES['light'])
            with Image.open(root/'assets/contribution-snake-light.gif') as result:
                self.assertEqual(result.info.get('loop'), 0)
                frames = [frame.convert('RGBA') for frame in ImageSequence.Iterator(result)]
                result.seek(0)
                self.assertEqual(sum(frame.info.get('duration', 0) for frame in ImageSequence.Iterator(result)), 360)
                self.assertEqual(len(frames), 3)
                self.assertTrue(all(frame.getpixel((0, 0))[3] == 0 for frame in frames))
                self.assertNotEqual(frames[0].tobytes(), frames[1].tobytes())
                self.assertEqual(frames[0].crop((0, 0, 1200, 60)).tobytes(),
                                 frames[-1].crop((0, 0, 1200, 60)).tobytes())

    def test_missing_official_source_stops_instead_of_substituting_a_different_snake(self):
        from contribution_snake import render_snake
        with tempfile.TemporaryDirectory(dir=self.scratch) as directory:
            root = Path(directory)
            (root/'assets').mkdir()
            Image.new('RGBA', (1200, 316)).save(root/'assets/activity-light.png')
            with self.assertRaises(FileNotFoundError) as caught:
                render_snake(root, THEMES['light'])
            self.assertIn('snake-source-light.gif', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
