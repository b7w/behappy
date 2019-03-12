# -*- coding: utf-8 -*-
import functools
import json
import subprocess
import uuid
from datetime import datetime
from pathlib import Path


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


@memoize
def read_exif_dates(paths):
    cmd = 'exiftool -datetimeoriginal -orientation -json -quiet'.split() + [i.as_posix() for i in paths]
    exif = json.loads(subprocess.check_output(cmd).decode('utf-8').rstrip('\r\n'))
    return [(Path(i['SourceFile']), parse_exif_date(i.get('DateTimeOriginal')), parse_orientation(i.get('Orientation')))
            for i in exif if i.get('DateTimeOriginal')]


def uid():
    return uuid.uuid4().hex
