"""Keep changing GitHub language names legible without colliding with shares."""
from pathlib import Path
import sys, unittest
from PIL import Image, ImageDraw
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
import status_panel
from design import font


class LanguageLegend(unittest.TestCase):
    def layout(self, rows):
        draw = ImageDraw.Draw(Image.new('RGBA', (1200, 640)))
        measure = lambda value: draw.textlength(value, font=font(18))
        layout = getattr(status_panel, 'language_legend', None)
        self.assertIsNotNone(layout, 'Language labels must reserve room for their percentages')
        result = layout(rows, sum(value for _, value in rows), measure)
        for item in result:
            self.assertGreaterEqual(item['x'], 762)
            self.assertLessEqual(item['right'], 1156)
            self.assertLessEqual(item['x'] + 18 + measure(item['name']) + 12,
                                 item['right'] - measure(item['share']))
            self.assertGreaterEqual(item['y'], 184)
            self.assertLessEqual(item['y'] + 24, 332)
        return result

    def test_long_names_do_not_overlap_shares(self):
        rows = [('Jupyter Notebook', 50), ('Visual Basic .NET', 20), ('HTML', 10),
                ('Python', 10), ('JavaScript', 5), ('Outras', 5)]
        result = self.layout(rows)
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0]['name'], rows[0][0])
        self.assertEqual(result[0]['share'], '50,0%')

    def test_an_exceptionally_long_name_is_abbreviated_without_shrinking_type(self):
        result = self.layout([('Uma linguagem com um nome excepcionalmente longo ' * 4, 1)])
        self.assertTrue(result[0]['name'].endswith('…'))
        self.assertEqual(result[0]['share'], '100,0%')

    def test_an_empty_language_mix_has_no_invented_entries(self):
        self.assertEqual(self.layout([]), [])
