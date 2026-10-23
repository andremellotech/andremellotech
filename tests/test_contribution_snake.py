"""The animation consumes real calendar cells without teleporting or colliding."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))


class ContributionSnake(unittest.TestCase):
    def snake_states(self, cells):
        try:
            from contribution_snake import snake_states
        except ImportError:
            self.fail('The contribution animation generator is not available yet')
        return snake_states(cells)

    def test_consumes_only_active_days_with_contiguous_collision_free_motion(self):
        cells = [dict(column=0, row=0, count=3, level=2),
                 dict(column=3, row=6, count=1, level=1),
                 dict(column=2, row=1, count=0, level=0)]
        states = self.snake_states(cells)
        self.assertTrue(states)
        self.assertFalse(states[0]['eaten'])
        self.assertEqual(states[-1]['eaten'], {(0, 0), (3, 6)})
        for previous, current in zip(states, states[1:]):
            self.assertLessEqual(len(current['eaten'] - previous['eaten']), 1)
            self.assertTrue(previous['eaten'] <= current['eaten'])
            self.assertEqual(current['body'][1:], previous['body'][:-1])
            a, b = previous['body'][0], current['body'][0]
            self.assertEqual(abs(a[0]-b[0]) + abs(a[1]-b[1]), 1)
            self.assertEqual(len(set(current['body'])), len(current['body']))
        self.assertEqual(states[0]['body'], states[-1]['body'], 'The loop must join without jumping')

    def test_empty_calendar_does_not_invent_activity(self):
        for cells in ([], [dict(column=52, row=4, count=0, level=0)]):
            states = self.snake_states(cells)
            self.assertTrue(states)
            self.assertTrue(all(not state['eaten'] for state in states))


if __name__ == '__main__':
    unittest.main()
