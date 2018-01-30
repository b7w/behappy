# -*- coding: utf-8 -*-
import json
import subprocess
from pathlib import Path

from dateutil.parser import parse


def read_exif_dates(paths):
    cmd = 'exiftool -datetimeoriginal -json -quiet'.split() + [i.as_posix() for i in paths]
    exif = json.loads(subprocess.check_output(cmd).decode('utf-8').rstrip('\r\n'))
    return [(Path(i['SourceFile']), parse(i.get('DateTimeOriginal'))) for i in exif if i.get('DateTimeOriginal')]
