# -*- coding: utf-8 -*-
import csv
from collections import namedtuple
from pathlib import Path

import click

Row = namedtuple('Row', 'id, parent_id, title, description, thumbnail, date, path')

Album = namedtuple('Album', 'id, parent_id, title, description, path, thumbnail, date, images')


def album_directory(paths, last=True):
    """
    :rtype: Path
    """
    if last:
        return sorted(paths, key=lambda x: len(x.as_posix()), reverse=True)[0]
    first = sorted(paths, key=lambda x: len(x.as_posix()))[0]
    p = list(paths)
    p.remove(first)
    while not all((first in i.parents) for i in p):
        first = first.parent
    return first


def relative_to(path, root):
    """
    :type path: Path
    :type root: Path
    """
    r = Path(root)
    t = 0
    while True:
        try:
            p = Path(path).relative_to(r)
            return Path('../' * t, *p.parts[t:])
        except ValueError:
            t += 1
            r = r.parent


def map_to_real(path, share_mapping):
    p = path.as_posix()
    for frm, to in share_mapping:
        p = p.replace(frm, to, 1)
    return Path(p)


def convert(root, share_mapping, select_last):
    with open('/Users/B7W/Downloads/gallery.txt') as f:
        reader = csv.reader(f, delimiter=';')
        rows = [Row(*i) for i in reader]
        albums_id2paths = {}
        for r in rows:
            if r.parent_id != ' c8827bb6':
                albums_id2paths.setdefault(r.id, set()).add(Path(r.path).parent)
        albums = []
        for id, paths in albums_id2paths.items():
            a = next(i for i in rows if i.id == id)
            path = album_directory(paths, id in select_last)
            path = map_to_real(path, share_mapping)
            album = Album(
                id=id,
                parent_id=a.parent_id,
                title=a.title,
                description=a.description,
                path=path,
                thumbnail=relative_to(a.thumbnail, path),
                date=a.date,
                images=[relative_to(i.path, path) for i in rows if i.id == id],
            )
            albums.append(album)

        for album in albums:
            path = Path(root, album.path)
            print(path)
            exists = path.exists()
            print(exists, album)


@click.command(help='Share mapping')
@click.option('--root', help='Viewer share path')
@click.option('--share-mapping', multiple=True, help='Share mapping')
@click.option('--select-last', multiple=True, help='Viewer share path')
def main(root, share_mapping, select_last):
    """
    Convert bviewer albums to behappy.ini

    SELECT
      core_album.id,
      core_album.parent_id,
      core_album.title,
      core_album.description,
      (SELECT core_image.path
       FROM core_image
       WHERE core_image.id = thumbnail_id) AS thumbnail,
      to_char(core_album.time, 'YYYY-MM-DD')  AS date,
      core_image.path
    FROM core_album
      JOIN core_image ON core_album.id = core_image.album_id
    ORDER BY core_album.id
    """
    share_mapping = [tuple(it.split(':')) for it in share_mapping]
    convert(root, share_mapping, select_last)


if __name__ == '__main__':
    main()
