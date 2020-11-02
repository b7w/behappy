from datetime import datetime
from pathlib import Path
from unittest import TestCase
from urllib.request import urlretrieve

from behappy.core.utils import parse_orientation, read_exif


class TestUtils(TestCase):

    def setUp(self):
        self.test_img1 = Path('tmp/image-01.jpg')
        if not self.test_img1.exists():
            url = 'https://s3-eu-west-1.amazonaws.com/b7w.distributions/behappy/tests/image-01.jpg'
            self.test_img1.parent.mkdir(exist_ok=True)
            urlretrieve(url, filename=self.test_img1.as_posix())

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

    def test_exif_properties(self):
        _, exif = read_exif([Path(self.test_img1)])[0]

        self.assertEqual(exif.name, 'image-01')
        self.assertEqual(exif.maker, 'Fujifilm')
        self.assertEqual(exif.model, 'X-T30')
        self.assertEqual(exif.lens_model, 'XF35mmF2 R WR')
        self.assertEqual(exif.iso, 320)
        self.assertEqual(exif.fnumber, 2.0)
        self.assertEqual(exif.exposure_time, '1/420')
        self.assertEqual(exif.focal_length, '35.0 mm')
        self.assertEqual(exif.orientation, 0)
        self.assertEqual(exif.datetime_original, datetime(2019, 8, 21, 18, 49, 49))
        self.assertEqual(exif.style, 'Astia')

    def test_exif_info(self):
        _, exif = read_exif([Path(self.test_img1)])[0]

        self.assertEqual(exif.info(), 'Fujifilm X-T30  XF35mmF2 R WR | ISO320  f/2.0  1/420s | Astia | image-01')
