# -*- coding: utf-8 -*-
import configparser
import itertools
import shutil
from datetime import datetime
from pathlib import Path

import pkg_resources
from dateutil.parser import parse
from jinja2 import Environment, PackageLoader

from behappy.core.conf import settings
from behappy.core.model import Gallery, ImageSet, Album
from behappy.core.resize import ResizeOptions, ImageResizer
from behappy.core.utils import uid


def date_filter(value, fmt):
    return value.strftime(fmt)


def linebreaksbr_filter(value):
    return value.replace('\n', '<br/>')


class BeHappyFile:
    def __init__(self, folder):
        """
        :type folder: Path
        """
        self.folder = folder

    def new(self):
        with Path(self.folder, 'behappy.ini').open(mode='w') as f:
            title = self._title()
            date = self._parse_or_now()
            thumbnail = self._first_image()
            config = self._create(title, date, thumbnail)
            config.write(f)

    def _create(self, title, date, thumbnail):
        config = configparser.ConfigParser()
        config['album'] = dict(id=uid(), title=title, description='', date=date, tags='private')
        config['images'] = dict(thumbnail=thumbnail, include='*.jpg', exclude='')
        return config

    def _title(self):
        try:
            _, value = self.folder.name.split(' - ')
            return value.strip()
        except Exception:
            return ''

    def _parse_or_now(self):
        try:
            value, _ = self.folder.name.split(' - ')
            return parse(value.strip()).strftime('%Y-%m-%d')
        except Exception:
            print('Cannot parse time, set now')
            return datetime.now().strftime('%Y-%m-%d')

    def _first_image(self):
        for i in self.folder.glob('*.jpg'):
            return i.name
        return ''


class BeHappy:
    def __init__(self, target, tags):
        self.gallery = Gallery(settings.description())
        self.target = target
        self.tags = tags
        self.jinja = Environment(
            loader=PackageLoader('behappy.core'),
            trim_blocks=True
        )
        self.jinja.filters['date'] = date_filter
        self.jinja.filters['linebreaksbr'] = linebreaksbr_filter

    def build(self):
        self._load_albums()
        self._resize_images()
        self._copy_static_resources()
        self._write_robots()
        self._render_about_page()
        self._render_index_pages()
        self._render_year_pages()
        self._render_album_pages()
        self._render_error_page(name='404', title='404', message='Page not found')

    def _render_about_page(self):
        html = self.jinja.get_template('about.jinja2').render(**settings.templates_parameters(),
                                                              **settings.about())
        folder = Path(self.target, 'about')
        folder.mkdir(parents=True, exist_ok=True)
        with open(Path(folder, 'index.html'), mode='w') as f:
            f.write(html)

    def _render_index_pages(self):
        params = dict(title='Welcome', description=self.gallery.description, albums=self.gallery.top_albums(),
                      years=self.gallery.top_years())
        html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                **settings.templates_parameters())
        with Path(self.target, 'index.html').open(mode='w') as f:
            f.write(html)

    def _render_year_pages(self):
        groped = {}
        for album in self.gallery.top_albums():
            groped.setdefault(album.date.year, []).append(album)
        for year, albums in groped.items():
            params = dict(title='Welcome', description=self.gallery.description, albums=albums,
                          years=self.gallery.top_years(),
                          current_year=year)
            html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                    **settings.templates_parameters())
            folder = Path(self.target, 'year', str(year))
            folder.mkdir(parents=True, exist_ok=True)
            with open(Path(folder, 'index.html').as_posix(), mode='w') as f:
                f.write(html)

    def _render_album_pages(self):
        for album in self.gallery.albums():
            if album.children:
                albums = sorted(album.children, key=lambda x: x.date)
                params = dict(title=album.title, description=album.description, albums=albums,
                              back=dict(id=album.parent))
                html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                        **settings.templates_parameters())
            else:
                params = dict(album=album, images=album.image_set.images(), back=dict(id=album.parent))
                html = self.jinja.get_template('album.jinja2').render(**params,
                                                                      **settings.templates_parameters())
            with Path(self.target, 'album', str(album.id), 'index.html').open(mode='w') as f:
                f.write(html)

    def _render_error_page(self, name, title, message):
        html = self.jinja.get_template('message.jinja2').render(title=title, message=message,
                                                                **settings.templates_parameters())
        folder = Path(self.target, 'error')
        folder.mkdir(parents=True, exist_ok=True)
        with open(Path(folder, '{}.html'.format(name)), mode='w') as f:
            f.write(html)

    def _copy_static_resources(self):
        for t in ('css', 'img', 'js'):
            path = Path(self.target, t).as_posix()
            shutil.rmtree(path, ignore_errors=True)
            path_from = pkg_resources.resource_filename('behappy.core', 'templates/{}'.format(t))
            shutil.copytree(path_from, path)

    def _write_robots(self):
        with Path(self.target, 'robots.txt').open(mode='w') as f:
            f.writelines([
                'User-agent: *\n',
                'Disallow: /\n',
            ])

    def _resize_images(self):
        resizer = ImageResizer()
        for album in self.gallery.albums():
            path = Path(self.target, 'album', str(album.id))
            path.mkdir(parents=True, exist_ok=True)
            count = 0
            count_all = 0
            for image in album.image_set.images(all=True):
                for name, size in settings.image_sizes().items():
                    option = ResizeOptions.from_settings(size, name)
                    cache_path = image.cache_path(self.target, album.id, option)
                    r = resizer.resize(image.path, cache_path, option)
                    if r:
                        count += 1
                    count_all += 1

            print('[{}] {} of {} resizes'.format(album.title, count, count_all))

    def _load_albums(self):
        for p in settings.source_folders():
            inis = itertools.chain(p.glob('**/behappy.ini'), p.glob('**/behappy.*.ini'))
            for ini in inis:
                conf = configparser.ConfigParser()
                conf.read(ini)
                image_set = ImageSet(
                    path=ini.parent,
                    thumbnail=conf.get('images', 'thumbnail'),
                    include=conf.get('images', 'include', fallback=None),
                    exclude=conf.get('images', 'exclude', fallback=None),
                    sortby=conf.get('images', 'sortby', fallback='date'),
                )
                album = Album(
                    id=conf.get('album', 'id'),
                    parent=conf.get('album', 'parent', fallback=None),
                    title=conf.get('album', 'title'),
                    description=conf.get('album', 'description'),
                    date=conf.get('album', 'date'),
                    tags=conf.get('album', 'tags', fallback=''),
                    path=ini.parent,
                    image_set=image_set
                )
                if not self.tags or any(i in album.tags for i in self.tags):
                    self.gallery.add_album(album)
        for album in self.gallery.albums():
            album.children = [i for i in self.gallery.albums() if album.id == i.parent]

        albums_count = len(self.gallery.albums())
        image_count = sum(len(i.image_set.images(all=True)) for i in self.gallery.albums())
        print('Load {} albums and {} images'.format(albums_count, image_count))
