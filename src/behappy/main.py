# -*- coding: utf-8 -*-
import configparser
import hashlib
import itertools
import os
import shutil
from datetime import datetime
from pathlib import Path

import pkg_resources
from jinja2 import Environment, PackageLoader
from pytz import timezone

from behappy.resize import ResizeOptions, ImageResizer


class Settings:
    def __init__(self):
        pass

    def source_folders(self):
        paths = os.environ['SOURCE_FOLDERS'].split(':')
        return [Path(i) for i in paths]

    def description(self):
        return 'Gallery description'

    def timezone(self):
        return timezone('UTC')

    def image_sizes(self):
        return {
            'small': {
                'WIDTH': 300,
                'HEIGHT': 300,
                'CROP': True,
            },
            'big': {
                'WIDTH': 1920,
                'HEIGHT': 1080,
            },
        }

    def image_size(self, name):
        return self.image_sizes()[name]

    def about(self):
        return {
            'title': '~Hello~',
            'text': '''My name is B7W, because a love monochrome photos.

So what can I write here, nothing clever it seems.
Main target of this resource is share photos in good quality.

So look, feel, be happy :-)''',
        }

    def copyright(self):
        return {
            'email': 'mailto:bviewer@isudo.ru',
            'username': 'B7W',
        }

    def template_extra_html(self):
        return ''

    def templates_parameters(self):
        return {
            'copyright': self.copyright(),
            'EXTRA_HTML': self.template_extra_html()
        }


settings = Settings()


class Gallery:
    def __init__(self, description):
        self.description = description
        self.albums = []

    def years(self):
        return list(reversed(list(set(i.date.year for i in self.albums))))


class Image:
    def __init__(self, path):
        """
       :type path: pathlib.Path
       """
        self.path = path

    @property
    def id(self):
        return self._hash_for(self.path.as_posix())

    def uri(self, album_id, size_name):
        size_options = ResizeOptions.from_settings(settings.image_size(size_name), size_name)
        cache_name = self._cache_name(size_options)
        return Path('/album/{}/{}/{}.jpg'.format(album_id, size_options.name, cache_name))

    def cache_path(self, album_id, size_options):
        return Path('./target', Path(self.uri(album_id, size_options.name)).relative_to('/'))

    def _cache_name(self, size_options):
        option_pack = tuple()
        option_pack += (size_options.height, size_options.width, size_options.quality, size_options.crop)
        option_pack += (size_options.name, self.path.absolute().as_posix(), self.path.stat().st_ctime,)
        return self._hash_for(str(option_pack))

    def _hash_for(self, content):
        return hashlib.sha1(bytes(content, encoding='utf-8')).hexdigest()


class ImageSet:
    def __init__(self, path, thumbnail, include, exclude):
        """
        :type path: pathlib.Path
        """
        self.path = path
        self.thumbnail_path = thumbnail
        self.include = self._split(include)
        self.exclude = self._split(exclude)

    def _split(self, value):
        if value:
            return [i.strip() for i in value.split(',') if i.strip()]
        return []

    def images(self, all=False):
        result = set()
        for i in self.include:
            for p in self.path.glob(i):
                result.add(p.absolute())
        for i in self.exclude:
            for p in self.path.glob(i):
                result.remove(p.absolute())
        if self.thumbnail_path and all:
            thumbnail = Path(self.path, self.thumbnail_path)
            if thumbnail.exists():
                result.add(thumbnail.absolute())
            else:
                raise Exception('Can not find thumbnail: {}'.format(thumbnail))
        return [Image(p) for p in sorted(result)]

    @property
    def thumbnail(self):
        if self.thumbnail_path:
            thumbnail = Path(self.path, self.thumbnail_path)
            if thumbnail.exists():
                return Image(thumbnail.absolute())
        return None

    def __str__(self):
        return str(self.__dict__)


class Album:
    def __init__(self, id, parent, title, description, date, path, image_set):
        self.id = id
        self.parent = parent
        self.title = title
        self.description = description
        self.date = datetime.strptime(date, '%Y-%m-%d').replace(tzinfo=settings.timezone())
        self.path = path
        self.image_set = image_set

    def uri(self):
        return '/album/{}/'.format(self.id)

    def __str__(self):
        return str(self.__dict__)


def date_filter(value, fmt):
    return value.strftime(fmt)


def linebreaksbr_filter(value):
    return value.replace('\n', '<br/>')


class BeHappy:
    def __init__(self):
        self.gallery = Gallery(settings.description())
        self.jinja = Environment(
            loader=PackageLoader('behappy'),
            trim_blocks=True
        )
        self.jinja.filters['date'] = date_filter
        self.jinja.filters['linebreaksbr'] = linebreaksbr_filter

    def build(self):
        self._load_albums()
        self.resize_images()
        self.copy_static_resources()
        self.render_about_page()
        self.render_gallery_pages()
        self.render_gallery_per_year_pages()
        self.render_album_pages()
        self.render_error_page(name='404', title='404', message='Page not found')

    def render_about_page(self):
        html = self.jinja.get_template('about.jinja2').render(**settings.templates_parameters(),
                                                              **settings.about())
        folder = Path('./target/about')
        folder.mkdir(parents=True, exist_ok=True)
        with open(Path(folder, 'index.html'), mode='w') as f:
            f.write(html)

    def render_gallery_pages(self):
        params = dict(title='Welcome', description=self.gallery.description, albums=self.gallery.albums,
                      years=self.gallery.years())
        html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                **settings.templates_parameters())
        with open('./target/index.html', mode='w') as f:
            f.write(html)

    def render_gallery_per_year_pages(self):
        groped = {}
        for album in self.gallery.albums:
            groped.setdefault(album.date.year, []).append(album)
        for year, albums in groped.items():
            params = dict(title='Welcome', description=self.gallery.description, albums=albums,
                          years=self.gallery.years(),
                          current_year=year)
            html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                    **settings.templates_parameters())
            folder = Path('./target/year/{}'.format(year))
            folder.mkdir(parents=True, exist_ok=True)
            with open(Path(folder, 'index.html').as_posix(), mode='w') as f:
                f.write(html)

    def render_album_pages(self):
        for album in self.gallery.albums:
            params = dict(album=album, images=album.image_set.images())
            html = self.jinja.get_template('album.jinja2').render(**params,
                                                                  **settings.templates_parameters())
            with open('./target/album/{}/index.html'.format(album.id), mode='w') as f:
                f.write(html)

    def render_error_page(self, name, title, message):
        html = self.jinja.get_template('message.jinja2').render(title=title, message=message,
                                                                **settings.templates_parameters())
        folder = Path('./target/error')
        folder.mkdir(parents=True, exist_ok=True)
        with open(Path(folder, '{}.html'.format(name)), mode='w') as f:
            f.write(html)

    def copy_static_resources(self):
        for t in ('css', 'img', 'js'):
            shutil.rmtree('./target/{}'.format(t), ignore_errors=True)
            path = pkg_resources.resource_filename('behappy', 'templates/{}'.format(t))
            shutil.copytree(path, './target/{}'.format(t))

    def resize_images(self):
        resizer = ImageResizer()
        for album in self.gallery.albums:
            path = Path('./target/album/{}'.format(album.id))
            path.mkdir(parents=True, exist_ok=True)
            for image in album.image_set.images(all=True):
                for name, size in settings.image_sizes().items():
                    option = ResizeOptions.from_settings(size, name)
                    resizer.resize(image.path, image.cache_path(album.id, option), option)

    def _load_albums(self):
        for p in settings.source_folders():
            inis = itertools.chain(p.glob('**/behappy.ini'), p.glob('**/behappy.*.ini'))
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
                    id=conf.get('album', 'id'),
                    parent=conf.get('album', 'parent', fallback=None),
                    title=conf.get('album', 'title'),
                    description=conf.get('album', 'description'),
                    date=conf.get('album', 'date'),
                    path=ini.parent,
                    image_set=image_set
                )
                self.gallery.albums.append(album)
        albums_count = len(self.gallery.albums)
        image_count = sum(len(i.image_set.images(all=True)) for i in self.gallery.albums)
        print('Found {} albums and {} images'.format(albums_count, image_count))
