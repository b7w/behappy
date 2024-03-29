# -*- coding: utf-8 -*-
import functools
import inspect
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
        if 'self' in inspect.getfullargspec(func).args:
            key = str(args[1:]) + str(kwargs)
        else:
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
        """
        :type raw: dict
        """
        self._raw = raw

    @property
    def name(self):
        return Path(self._raw.get('File:FileName', '')).stem

    @property
    def maker(self):
        return self._raw.get('EXIF:Make', '').capitalize()

    @property
    def model(self):
        return self._raw.get('EXIF:Model', '').replace(self.maker, '')

    @property
    def lens_model(self):
        return self._raw.get('EXIF:LensModel', '')

    @property
    def iso(self):
        return self._raw.get('EXIF:ISO', '')

    @property
    def fnumber(self):
        return self._raw.get('EXIF:FNumber', '')

    @property
    def exposure_time(self):
        return self._raw.get('EXIF:ExposureTime', '')

    @property
    def focal_length(self):
        return self._raw.get('EXIF:FocalLength', '')

    @property
    def orientation(self):
        name2angle = {
            'Rotate 180': 180,  # N3
            'Rotate 90 CW': 270,  # N6
            'Rotate 270 CW': 90,  # N8
        }
        return name2angle.get(self._raw.get('EXIF:Orientation'), 0)

    @property
    def datetime_original(self):
        if 'EXIF:DateTimeOriginal' in self._raw:
            s = self._raw['EXIF:DateTimeOriginal']
            return datetime.strptime(s, '%Y:%m:%d %H:%M:%S')
        if 'QuickTime:DateTimeOriginal' in self._raw:
            s = self._raw['QuickTime:DateTimeOriginal']
            return datetime.strptime(s, '%Y:%m:%d %H:%M:%S%z').replace(tzinfo=None)
        return datetime.min

    @property
    def style(self):
        value = self._raw.get('MakerNotes:FilmMode', '')
        res = re.findall(r'\((\w+)\)', value)
        if res:
            return res[0]

    def info(self):
        model = '{} {} &nbsp; {}'.format(self.maker, self.model, self.lens_model)
        settings = 'ISO{} &nbsp; f/{} &nbsp; {}s'.format(self.iso, self.fnumber, self.exposure_time)
        style = self.style or ''
        name = self.name
        info = ' &nbsp;|&nbsp; '.join(i for i in (model, settings, style, name) if i)
        return info.replace('&nbsp;', '').strip()


@memoize
def read_exif(paths):
    cmd = 'exiftool -groupNames -json -quiet'.split() + [i.as_posix() for i in paths]
    exif = json.loads(subprocess.check_output(cmd).decode('utf-8').rstrip('\r\n'))
    return [(Path(i['SourceFile']), Exif(i)) for i in exif]


def uid():
    return uuid.uuid4().hex
