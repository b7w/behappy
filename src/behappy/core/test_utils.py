from unittest import TestCase

from behappy.core.utils import orientation


class TestUtils(TestCase):

    def test_orientation(self):
        self.assertEqual(orientation('Horizontal (normal)'), 0)
        self.assertEqual(orientation('Mirror horizontal'), 0)
        self.assertEqual(orientation('Rotate 180'), 180)
        self.assertEqual(orientation('Mirror vertical'), 0)
        self.assertEqual(orientation('Mirror horizontal and rotate 270 CW'), 0)
        self.assertEqual(orientation('Rotate 90 CW'), 270)
        self.assertEqual(orientation('Mirror horizontal and rotate 90 CW'), 0)
        self.assertEqual(orientation('Rotate 270 CW'), 90)
