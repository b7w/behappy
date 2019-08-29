# -*- coding: utf-8 -*-
import hashlib
from datetime import datetime
from pathlib import Path

from behappy.core.conf import settings
from behappy.core.resize import ResizeOptions
from behappy.core.utils import read_exif


class Gallery:
    def __init__(self, title, description):
        self.title = title
        self.description = description
        self._albums = []
        self._ids = {}

    def add_album(self, album):
        if album.id not in self._ids:
            self._albums.append(album)
            self._ids[album.id] = album
        else:
            title = self._ids[album.id].title
            path = self._ids[album.id].path
            msg = 'Gallery already have album "{}" with id {}\n{}\n{}'
            raise Exception(msg.format(title, album.id, path, album.path))

    def albums(self):
        return sorted(self._albums, key=lambda x: x.date, reverse=True)

    def top_years(self):
        return sorted(set(i.date.year for i in self.top_albums()), reverse=True)

    def top_albums(self):
        return sorted([i for i in self._albums if not i.parent and not i.hidden], key=lambda x: x.date, reverse=True)

    def top_hidden_albums(self):
        return sorted([i for i in self._albums if not i.parent and i.hidden], key=lambda x: x.date, reverse=True)


class Image:
    def __init__(self, path, exif):
        """
       :type path: pathlib.Path
       :type exif: behappy.core.utils.Exif
       """
        self.path = path
        self.date = exif.datetime_original
        self.orientation = exif.orientation
        self.exif_info = exif.info()

    @property
    def id(self):
        return self._hash_for(self.path.as_posix())

    def uri(self, album_id, size_name):
        size_options = ResizeOptions.from_settings(settings.image_size(size_name), size_name)
        cache_name = self._cache_name(size_options)
        return Path('/album/{}/{}/{}.jpg'.format(album_id, size_options.name, cache_name))

    def cache_path(self, target, album_id, size_options):
        return Path(target, Path(self.uri(album_id, size_options.name)).relative_to('/'))

    def _cache_name(self, size_options):
        option_pack = tuple()
        option_pack += (size_options.height, size_options.width, size_options.quality, size_options.crop)
        option_pack += (size_options.name, self.path.absolute().as_posix(), self.path.stat().st_ctime,)
        if self.orientation:
            option_pack += ('orientation', self.orientation,)
        return self._hash_for(str(option_pack))

    def _hash_for(self, content):
        return hashlib.sha1(bytes(content, encoding='utf-8')).hexdigest()

    def __repr__(self):
        return str(self.__dict__)


class ImageSet:
    def __init__(self, path, thumbnail, include, exclude, sortby):
        """
        :type path: pathlib.Path
        """
        self.path = path
        self.thumbnail_path = thumbnail
        self.include = self._split(include)
        self.exclude = self._split(exclude)
        self.sortby = sortby

    def _split(self, value):
        if value:
            return [i.strip() for i in value.split(',') if i.strip()]
        return []

    def _filter_hidden(self, iterable):
        for path in iterable:
            if not path.name.startswith('.'):
                yield path

    def images(self, all=False):
        result = set()
        for i in self.include:
            for p in self._filter_hidden(self.path.glob(i)):
                result.add(p.absolute())
        for i in self.exclude:
            for p in self._filter_hidden(self.path.glob(i)):
                result.remove(p.absolute())
        if self.thumbnail_path and all:
            thumbnail = Path(self.path, self.thumbnail_path)
            if thumbnail.exists():
                result.add(thumbnail.absolute())
            else:
                raise Exception('Can not find thumbnail: {}'.format(thumbnail))
        images = [Image(p, e) for p, e in read_exif(list(result))]
        return sorted(images, key=lambda x: getattr(x, self.sortby))

    @property
    def thumbnail(self):
        if self.thumbnail_path:
            thumbnail = Path(self.path, self.thumbnail_path)
            if thumbnail.exists():
                path, exif = read_exif([thumbnail.absolute()])[0]
                return Image(path, exif)
        return None

    def __repr__(self):
        return str(self.__dict__)


class Album:
    def __init__(self, id, parent, title, description, date, tags, hidden, path, image_set):
        self.id = id
        self.parent = parent
        self.children = []
        self.title = title
        self.description = description
        self.date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=settings.timezone())
        self.tags = set([i.strip() for i in tags.split(',') if i.strip()])
        self.hidden = hidden
        self.path = path
        self.image_set = image_set

    def uri(self):
        return '/album/{}/'.format(self.id)

    def __repr__(self):
        return str(self.__dict__)
