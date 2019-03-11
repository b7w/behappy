from unittest import TestCase

from behappy.core.utils import parse_orientation


class TestUtils(TestCase):

    def test_parse_orientation(self):
        self.assertEqual(parse_orientation(None), 0)
        self.assertEqual(parse_orientation('Horizontal (normal)'), 0)
        self.assertEqual(parse_orientation('Mirror horizontal'), 0)
        self.assertEqual(parse_orientation('Rotate 180'), 180)
        self.assertEqual(parse_orientation('Mirror vertical'), 0)
        self.assertEqual(parse_orientation('Mirror horizontal and rotate 270 CW'), 0)
        self.assertEqual(parse_orientation('Rotate 90 CW'), 270)
        self.assertEqual(parse_orientation('Mirror horizontal and rotate 90 CW'), 0)
        self.assertEqual(parse_orientation('Rotate 270 CW'), 90)
