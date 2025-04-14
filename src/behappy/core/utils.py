# -*- coding: utf-8 -*-
import functools
import hashlib
import inspect
import os
import re
import subprocess
import uuid
from datetime import datetime
from pathlib import Path
from time import time_ns
from typing import List

import orjson


def timeit(f):
    msg = '## {0} complete in {1:.0f} min {2:.1f} sec ({3}ns)'

    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        start = time_ns()
        try:
            return f(*args, **kwargs)
        finally:
            elapsed = time_ns() - start
            elapsed_sec = elapsed / 10**9

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


def search_files(paths: List[Path], pattern: re.Pattern):
    results = []
    for path in paths:
        for root, dirs, files in os.walk(path):
            for f in files:
                if pattern.match(f):
                    results.append(Path(root, f))
    return results


def parse_orientation(value):
    name2angle = {
        'Rotate 180': 180,  # N3
        'Rotate 90 CW': 270,  # N6
        'Rotate 270 CW': 90,  # N8
    }
    return name2angle.get(value, 0)


class Exif:
    def __init__(self, raw: dict):
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
        model = f'{self.maker} {self.model}  {self.lens_model}'
        settings = f'ISO{self.iso}  f/{self.fnumber}  {self.exposure_time}s'
        style = self.style or ''
        name = self.name
        info = ' | '.join(i for i in (model, settings, style, name) if i)
        return info.strip()


class CacheManager:

    def __init__(self, original_path: Path, name):
        self.path = original_path.with_suffix('.cache.json')
        self.name = name
        if self.path.exists():
            self._state = orjson.loads(self.path.read_bytes())
        else:
            self._state = {}

    def load_list(self, key: str, factory, verification):
        cache = self._state.get(key)
        if not cache:
            print(f'[{self.name}] Empty cache {key}')
            return []
        current = sorted([factory.make_stamp(i) for i in verification])
        saved = sorted([i['stamp'] for i in cache])
        if current == saved:
            return [factory.deserialize(i) for i in cache]
        print(f'[{self.name}] Skip cache {key}')
        return []

    def save_list(self, key: str, values):
        self._state[key] = [i.serialize() for i in values]
        self.path.write_bytes(orjson.dumps(self._state))


@memoize
def read_exif(paths):
    cmd = 'exiftool -groupNames -json -quiet'.split() + [i.as_posix() for i in paths]
    output = subprocess.check_output(cmd)
    exif = orjson.loads(output)
    return [(Path(i['SourceFile']), Exif(i)) for i in exif]


def file_stamp(version: int, path: Path) -> str:
    stat = path.stat()
    content = (version, stat.st_birthtime, stat.st_size, stat.st_ctime, stat.st_mtime,)
    return hashlib.blake2b(bytes(str(content), encoding='utf-8'), digest_size=32).hexdigest()


def uid():
    return uuid.uuid4().hex
