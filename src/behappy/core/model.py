# -*- coding: utf-8 -*-
import hashlib
from datetime import datetime
from functools import cache, cached_property
from pathlib import Path
from typing import List

from behappy.core.conf import settings
from behappy.core.resize import ResizeOptions
from behappy.core.utils import read_exif, file_stamp, CacheManager, Exif


class Gallery:
    def __init__(self, title, description):
        self.title = title
        self.description = description
        self._albums: List[Album] = []
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
    VERSION = 1

    def __init__(self, path: Path, exif: Exif = None,
                 date=None, orientation=None, exif_info=None, stamp=None, hash=None):
        self.path = path
        if exif:
            self.date = exif.datetime_original
            self.orientation = exif.orientation
            self.exif_info = exif.info()
            self.stamp = file_stamp(self.VERSION, self.path)
            self.hash = hashlib.blake2b(self.path.read_bytes()).hexdigest()
        else:
            self.date = date
            self.orientation = orientation
            self.exif_info = exif_info
            self.stamp = stamp
            self.hash = hash

    @property
    def id(self):
        return self._hash_for(self.path.as_posix())

    def uri(self, album_id, size_name):
        size_options = ResizeOptions.from_settings(settings.image_size(size_name), size_name)
        cache_name = self._cache_name(size_options)
        return Path('/album/{}/{}/{}.jpg'.format(album_id, size_options.name, cache_name))

    def size_for(self, size_name):
        s = settings.image_size(size_name)
        return dict(width=s['WIDTH'], height=s['HEIGHT'])

    def cache_path(self, target, album_id, size_options):
        return Path(target, Path(self.uri(album_id, size_options.name)).relative_to('/'))

    def _cache_name(self, size_options):
        option_pack = tuple()
        option_pack += (size_options.height, size_options.width, size_options.quality, size_options.crop)
        option_pack += (size_options.name, self.hash,)
        if self.orientation:
            option_pack += ('orientation', self.orientation,)
        return self._hash_for(str(option_pack))

    def _hash_for(self, content):
        return hashlib.blake2b(bytes(content, encoding='utf-8'), digest_size=32).hexdigest()

    def serialize(self):
        return {'path': self.path.absolute().as_posix(),
                'date': self.date,
                'orientation': self.orientation,
                'exif_info': self.exif_info,
                'stamp': self.stamp,
                'hash': self.hash, }

    @classmethod
    def make_stamp(cls, source: Path):
        return file_stamp(cls.VERSION, source)

    @classmethod
    def deserialize(cls, source):
        path = source['path']
        date = source['date']
        orientation = source['orientation']
        exif_info = source['exif_info']
        stamp = source['stamp']
        hash = source['hash']
        return Image(Path(path), date=date, orientation=orientation, exif_info=exif_info, stamp=stamp, hash=hash)

    def __repr__(self):
        return str(self.__dict__)


class Video:
    VERSION = 1

    def __init__(self, path: Path, exif: Exif = None, date=None, exif_info=None, stamp=None, hash=None):
        self.path = path
        if exif:
            self.date = exif.datetime_original
            self.exif_info = exif.info()
            self.stamp = file_stamp(self.VERSION, self.path)
            self.hash = self._hash()
        else:
            self.date = date
            self.exif_info = exif_info
            self.stamp = stamp
            self.hash = hash

    @property
    def id(self):
        return self._hash_for(self.path.as_posix())

    def uri(self, album_id):
        cache_name = self._cache_name()
        return Path('/album/{}/{}/{}.mp4'.format(album_id, 'video', cache_name))

    def cache_path(self, target, album_id):
        return Path(target, Path(self.uri(album_id)).relative_to('/'))

    def _cache_name(self):
        return self._hash_for(self.hash)

    def _hash_for(self, content):
        return hashlib.blake2b(bytes(content, encoding='utf-8'), digest_size=32).hexdigest()

    def _hash(self):
        h = hashlib.blake2b()
        with self.path.open('rb') as f:
            buffer = f.read(2 * 1024 * 1024)
            while buffer:
                h.update(buffer)
                buffer = f.read(2 * 1024 * 1024)
        return h.hexdigest()

    def serialize(self):
        return {'path': self.path.absolute().as_posix(),
                'date': self.date,
                'exif_info': self.exif_info,
                'stamp': self.stamp,
                'hash': self.hash, }

    @classmethod
    def make_stamp(cls, source: Path):
        return file_stamp(cls.VERSION, source)

    @classmethod
    def deserialize(cls, source):
        path = source['path']
        date = source['date']
        exif_info = source['exif_info']
        stamp = source['stamp']
        hash = source['hash']
        return Video(Path(path), date=date, exif_info=exif_info, stamp=stamp, hash=hash)

    def __repr__(self):
        return str(self.__dict__)


class ImageSet:
    def __init__(self, path: Path, thumbnail, include, exclude, sortby, cache_manager: CacheManager):
        self.path = path
        self.thumbnail_path = thumbnail
        self.include = self._split(include)
        self.exclude = self._split(exclude)
        self.sortby = sortby
        self._cache = cache_manager

    def _split(self, value):
        if value:
            return [i.strip() for i in value.split(',') if i.strip()]
        return []

    def _filter_hidden(self, iterable):
        for path in iterable:
            if not path.name.startswith('.'):
                yield path

    @cache
    def _images(self):
        result = set()
        for i in self.include:
            for p in self._filter_hidden(self.path.glob(i)):
                result.add(p.absolute())
        for i in self.exclude:
            for p in self._filter_hidden(self.path.glob(i)):
                result.remove(p.absolute())
        return result

    def images(self):
        result = self._images()
        images = self._cache.load_list('images', Image, result)
        if not images:
            images = [Image(p, e) for p, e in read_exif(list(result))] if result else []
            self._cache.save_list('images', images)
        return sorted(images, key=lambda x: getattr(x, self.sortby))

    def images_count(self):
        return len(self.images())

    @cached_property
    def thumbnail(self):
        if self.thumbnail_path:
            thumbnail = Path(self.path, self.thumbnail_path)
            if thumbnail.exists():
                path, exif = read_exif([thumbnail.absolute()])[0]
                return Image(path, exif=exif)
        return None

    def __repr__(self):
        return str(self.__dict__)


class VideoSet:
    def __init__(self, path: Path, include, exclude, sortby, cache_manager: CacheManager):
        self.path = path
        self.include = self._split(include)
        self.exclude = self._split(exclude)
        self.sortby = sortby
        self._cache = cache_manager

    def _split(self, value):
        if value:
            return [i.strip() for i in value.split(',') if i.strip()]
        return []

    def _filter_hidden(self, iterable):
        for path in iterable:
            if not path.name.startswith('.'):
                yield path

    @cache
    def _videos(self):
        result = set()
        for i in self.include:
            for p in self._filter_hidden(self.path.glob(i)):
                result.add(p.absolute())
        for i in self.exclude:
            for p in self._filter_hidden(self.path.glob(i)):
                result.remove(p.absolute())
        return result

    def videos(self):
        result = self._videos()
        videos = self._cache.load_list('videos', Video, result)
        if not videos:
            videos = [Video(p, exif=e) for p, e in read_exif(list(result))] if result else []
            self._cache.save_list('videos', videos)
        return sorted(videos, key=lambda x: getattr(x, self.sortby))

    def __repr__(self):
        return str(self.__dict__)


class Album:
    def __init__(self, id, parent, title, description, date, tags, hidden, path, image_set, video_set):
        self.id = id
        self.parent = parent
        self.children = []
        self.title = title
        self.description = description
        self.date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=settings.timezone())
        self.tags = set([i.strip() for i in tags.split(',') if i.strip()])
        self.hidden = hidden
        self.path = path
        self.image_set: ImageSet = image_set
        self.video_set: VideoSet = video_set

    def uri(self):
        return '/album/{}/'.format(self.id)

    def __repr__(self):
        return str(self.__dict__)
