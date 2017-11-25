# -*- coding: utf-8 -*-
import configparser
import hashlib
import shutil
from datetime import datetime
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
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

    def template_path(self):
        return 'behappy/templates'

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
    def __init__(self, desc):
        self.desc = desc
        self.albums = []


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
        self.include = [i.strip() for i in include.split(',')] or []
        self.exclude = [i.strip() for i in exclude.split(',')] or []

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
    def __init__(self, id, parent, name, desc, date, path, image_set):
        self.id = id
        self.parent = parent
        self.name = name
        self.desc = desc
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
        self.gallery = Gallery(settings.desc())
        self.jinja = Environment(loader=FileSystemLoader(settings.template_path()), trim_blocks=True)
        self.jinja.filters['date'] = date_filter
        self.jinja.filters['linebreaksbr'] = linebreaksbr_filter

    def build(self):
        self._load_albums()
        self.resize_images()
        self.copy_static_resources()
        self.render_about_page()
        self.render_gallery_pages()
        self.render_album_pages()

    def render_about_page(self):
        html = self.jinja.get_template('about.jinja2').render(**settings.templates_parameters(),
                                                              **settings.about())
        with open('./target/about.html', mode='w') as f:
            f.write(html)

    def render_gallery_pages(self):
        params = dict(title='Welcome', description=self.gallery.desc, albums=self.gallery.albums)
        html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                **settings.templates_parameters())
        with open('./target/index.html', mode='w') as f:
            f.write(html)

    def render_album_pages(self):
        for album in self.gallery.albums:
            params = dict(album=album, images=album.image_set.images())
            html = self.jinja.get_template('album.jinja2').render(**params,
                                                                **settings.templates_parameters())
            with open('./target/album/{}/index.html'.format(album.id), mode='w') as f:
                f.write(html)

    def copy_static_resources(self):
        for t in ('css', 'img', 'js'):
            shutil.rmtree('./target/{}'.format(t), ignore_errors=True)
            shutil.copytree(settings.template_path() + '/{}'.format(t), './target/{}'.format(t))

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
                    id=conf.get('album', 'id'),
                    parent=conf.get('album', 'parent', fallback=None),
                    name=conf.get('album', 'name'),
                    desc=conf.get('album', 'desc'),
                    date=conf.get('album', 'date'),
                    path=ini.parent,
                    image_set=image_set
                )
                self.gallery.albums.append(album)
