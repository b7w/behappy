# -*- coding: utf-8 -*-
import configparser
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
            return Path('../' * t, p)
        except ValueError:
            t += 1
            r = r.parent


def map_to_real(path, share_mapping):
    p = path.as_posix()
    for frm, to in share_mapping:
        p = p.replace(frm, to, 1)
    return Path(p)


def write_ini(album, full_name=False):
    """
    :param full_name: bool
    :param album: Album
    """
    name = 'behappy.ini' if not full_name else 'behappy.{}.ini'.format(album.id)
    with Path(album.path, name).open(mode='w') as f:
        config = configparser.ConfigParser()
        config['album'] = dict(id=album.id, title=album.title, description=album.description, date=album.date)
        if album.parent_id:
            config['album']['parent'] = album.parent_id
        config['images'] = dict(thumbnail=album.thumbnail, include=', '.join(i.as_posix() for i in album.images))
        config.write(f)


def convert(dump, root, top_album, share_mapping, select_last):
    with open(dump) as f:
        reader = csv.reader(f, delimiter=';')
        rows = [Row(*i) for i in reader]
        albums_id2paths = {}
        for r in rows:
            albums_id2paths.setdefault(r.id, set()).add(Path(r.path).parent)
        albums = []
        for id, paths in albums_id2paths.items():
            a = next(i for i in rows if i.id == id)
            path = album_directory(paths, id in select_last)
            parent_id = a.parent_id if a.parent_id != top_album else None
            album = Album(
                id=id,
                parent_id=parent_id,
                title=a.title,
                description=a.description,
                path=Path(root, map_to_real(path, share_mapping)),
                thumbnail=relative_to(a.thumbnail, path),
                date=a.date,
                images=[relative_to(i.path, path) for i in rows if i.id == id],
            )
            albums.append(album)

        path2album = {}
        for album in albums:
            path2album.setdefault(album.path, []).append(album)

        for pack in path2album.values():
            if len(pack) > 1:
                for album in pack:
                    write_ini(album, full_name=len(pack) > 1)
            else:
                write_ini(pack[0])


@click.command(help='Convert bviewer db to behappy.ini')
@click.option('--dump', help='Query in csv format')
@click.option('--root', help='Viewer share path')
@click.option('--top-album', help='Top album')
@click.option('--share-mapping', multiple=True, help='Share mapping')
@click.option('--select-last', multiple=True, help='Viewer share path')
def main(dump, root, top_album, share_mapping, select_last):
    """
    Convert bviewer albums to behappy.ini

    Run query on bviewer db and export as csv (';' as delimiter)

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
    convert(dump, root, top_album, share_mapping, select_last)


if __name__ == '__main__':
    main()
