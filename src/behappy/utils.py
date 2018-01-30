# -*- coding: utf-8 -*-
import json
import subprocess
from datetime import datetime
from pathlib import Path


def parse_exif_date(value):
    return datetime.strptime(value, '%Y:%m:%d %H:%M:%S')


def read_exif_dates(paths):
    cmd = 'exiftool -datetimeoriginal -json -quiet'.split() + [i.as_posix() for i in paths]
    exif = json.loads(subprocess.check_output(cmd).decode('utf-8').rstrip('\r\n'))
    return [(Path(i['SourceFile']), parse_exif_date(i.get('DateTimeOriginal')))
            for i in exif if i.get('DateTimeOriginal')]
