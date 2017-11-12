# -*- coding: utf-8 -*-
import configparser
from datetime import datetime
from pathlib import Path

from pytz import timezone

from behappy.resize import ResizeOptions, ImageResizer


class Settings:
    def __init__(self):
        pass

    def source_folders(self):
        return [Path('/Users/B7W/Documents/Photos/').absolute(), ]

    def desc(self):
        return 'Gallery desc'

    def timezone(self):
        return timezone('UTC')

    def image_sizes(self):
        return {
            'tiny': {
                'WIDTH': 150,
                'HEIGHT': 150,
                'CROP': True,
                'QUALITY': 85,
            },
            'small': {
                'WIDTH': 300,
                'HEIGHT': 300,
                'CROP': True,
            },
            'big': {
                'WIDTH': 1920,
                'HEIGHT': 1080,
            },
            'full': {
                'WIDTH': 10 ** 6,
                'HEIGHT': 10 ** 6,
            },
        }

    def image_size(self, name):
        return self.image_sizes()[name]


class Gallery:
    def __init__(self, desc):
        self.desc = desc
        self.albums = []


class ImageSet:
    def __init__(self, path, thumbnail, include, exclude):
        self.path = path
        self.thumbnail = thumbnail
        self.include = [i.strip() for i in include.split(',')] or []
        self.exclude = [i.strip() for i in exclude.split(',')] or []

    def images(self):
        result = set()
        for i in self.include:
            for p in self.path.glob(i):
                result.add(p.absolute())
        for i in self.exclude:
            for p in self.path.glob(i):
                result.remove(p.absolute())
        return sorted(result)

    def __str__(self):
        return str(self.__dict__)


class Album:
    def __init__(self, settings, uid, parent, name, desc, date, path, image_set):
        self.settings = settings
        self.uid = uid
        self.parent = parent
        self.name = name
        self.desc = desc
        self.date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=self.settings.timezone())
        self.path = path
        self.image_set = image_set

    def __str__(self):
        return str(self.__dict__)


class BeHappy:
    def __init__(self, settings):
        self.settings = settings
        self.gallery = Gallery(settings.desc())

    def build(self):
        self._load_albums()
        for album in self.gallery.albums:
            path = Path('./target/album/{}'.format(album.uid))
            path.mkdir(parents=True, exist_ok=True)
            for image in album.image_set.images():
                for name, size in self.settings.image_sizes().items():
                    option = ResizeOptions.from_settings(size, name)
                    resizer = ImageResizer()
                    resizer.resize(album, image, option)

    def _load_albums(self):
        for p in self.settings.source_folders():
            inis = p.glob('**/behappy.ini')
            for ini in inis:
                conf = configparser.ConfigParser()
                conf.read(ini)
                image_set = ImageSet(
                    path=ini.parent,
                    thumbnail=conf.get('images', 'thumbnail'),
                    include=conf.get('images', 'include'),
                    exclude=conf.get('images', 'exclude', fallback=None),
                )
                album = Album(
                    self.settings,
                    uid=conf.get('album', 'id'),
                    parent=conf.get('album', 'parent', fallback=None),
                    name=conf.get('album', 'name'),
                    desc=conf.get('album', 'desc'),
                    date=conf.get('album', 'date'),
                    path=ini.parent,
                    image_set=image_set
                )
                self.gallery.albums.append(album)
