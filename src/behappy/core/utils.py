# -*- coding: utf-8 -*-
import functools
import json
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from time import time_ns


def timeit(f):
    msg = '## {0} complete in {1:.0f} min {2:.1f} sec ({3}ns)'

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        start = time_ns()
        try:
            return f(*args, **kwargs)
        finally:
            elapsed = time_ns() - start
            elapsed_sec = elapsed / 10 ** 9

            print(msg.format(f.__name__, elapsed_sec // 60, elapsed_sec % 60, elapsed))

    return wrapper


def parse_exif_date(value):
    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')


def memoize(func):
    cache = func.cache = {}

    @functools.wraps(func)
    def memoized_func(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = func(*args, **kwargs)
        return cache[key]

    return memoized_func


def parse_orientation(value):
    name2angle = {
        'Rotate 180': 180,  # N3
        'Rotate 90 CW': 270,  # N6
        'Rotate 270 CW': 90,  # N8
    }
    return name2angle.get(value, 0)


class Exif:
    def __init__(self, raw):
        self._raw = raw

    @property
    def maker(self):
        return self._raw['Make']

    @property
    def model(self):
        return self._raw['Model']

    @property
    def lens_model(self):
        return self._raw['LensModel']

    @property
    def iso(self):
        return self._raw['ISO']

    @property
    def fnumber(self):
        return self._raw['FNumber']

    @property
    def exposure_time(self):
        return self._raw['ExposureTime']

    @property
    def focal_length(self):
        return self._raw['FocalLength']

    @property
    def orientation(self):
        name2angle = {
            'Rotate 180': 180,  # N3
            'Rotate 90 CW': 270,  # N6
            'Rotate 270 CW': 90,  # N8
        }
        return name2angle.get(self._raw['Orientation'], 0)

    @property
    def datetime_original(self):
        return datetime.strptime(self._raw['DateTimeOriginal'], '%Y:%m:%d %H:%M:%S')

    @property
    def style(self):
        value = self._raw.get('FilmMode', '')
        res = re.findall(r'\((\w+)\)', value)
        if res:
            return res[0]

    def info(self):
        model = '{} &nbsp; {}'.format(self.model, self.lens_model).strip()
        settings = 'ISO{} &nbsp; f/{} &nbsp; {}s'.format(self.iso, self.fnumber, self.exposure_time).strip()
        style = '{}'.format(self.style or '').strip()
        return ' &nbsp;|&nbsp; '.join(i for i in (model, settings, style) if i)


@memoize
@timeit
def read_exif(paths):
    options = '-Make -Model -LensModel -ISO -FNumber -ExposureTime -FocalLength -Orientation -DateTimeOriginal -FilmMode'
    cmd = 'exiftool {} -json -quiet'.format(options).split() + [i.as_posix() for i in paths]
    exif = json.loads(subprocess.check_output(cmd).decode('utf-8').rstrip('\r\n'))
    return [(Path(i['SourceFile']), Exif(i)) for i in exif]


def uid():
    return uuid.uuid4().hex
