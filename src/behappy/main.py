# -*- coding: utf-8 -*-
import configparser
import itertools
import shutil
from pathlib import Path

import pkg_resources
from jinja2 import Environment, PackageLoader

from behappy.conf import settings
from behappy.model import Gallery, ImageSet, Album
from behappy.resize import ResizeOptions, ImageResizer


def date_filter(value, fmt):
    return value.strftime(fmt)


def linebreaksbr_filter(value):
    return value.replace('\n', '<br/>')


class BeHappy:
    def __init__(self, tags):
        self.gallery = Gallery(settings.description())
        self.tags = tags
        self.jinja = Environment(
            loader=PackageLoader('behappy'),
            trim_blocks=True
        )
        self.jinja.filters['date'] = date_filter
        self.jinja.filters['linebreaksbr'] = linebreaksbr_filter

    def build(self):
        self._load_albums()
        self._resize_images()
        self._copy_static_resources()
        self._render_about_page()
        self._render_index_pages()
        self._render_year_pages()
        self._render_album_pages()
        self._render_error_page(name='404', title='404', message='Page not found')

    def _render_about_page(self):
        html = self.jinja.get_template('about.jinja2').render(**settings.templates_parameters(),
                                                              **settings.about())
        folder = Path('./target/about')
        folder.mkdir(parents=True, exist_ok=True)
        with open(Path(folder, 'index.html'), mode='w') as f:
            f.write(html)

    def _render_index_pages(self):
        params = dict(title='Welcome', description=self.gallery.description, albums=self.gallery.top_albums(),
                      years=self.gallery.top_years())
        html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                **settings.templates_parameters())
        with open('./target/index.html', mode='w') as f:
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
            folder = Path('./target/year/{}'.format(year))
            folder.mkdir(parents=True, exist_ok=True)
            with open(Path(folder, 'index.html').as_posix(), mode='w') as f:
                f.write(html)

    def _render_album_pages(self):
        for album in self.gallery.albums():
            if album.children:
                params = dict(title=album.title, description=album.description, albums=album.children,
                              back=dict(id=album.parent))
                html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                        **settings.templates_parameters())
            else:
                params = dict(album=album, images=album.image_set.images(), back=dict(id=album.parent))
                html = self.jinja.get_template('album.jinja2').render(**params,
                                                                      **settings.templates_parameters())
            with open('./target/album/{}/index.html'.format(album.id), mode='w') as f:
                f.write(html)

    def _render_error_page(self, name, title, message):
        html = self.jinja.get_template('message.jinja2').render(title=title, message=message,
                                                                **settings.templates_parameters())
        folder = Path('./target/error')
        folder.mkdir(parents=True, exist_ok=True)
        with open(Path(folder, '{}.html'.format(name)), mode='w') as f:
            f.write(html)

    def _copy_static_resources(self):
        for t in ('css', 'img', 'js'):
            shutil.rmtree('./target/{}'.format(t), ignore_errors=True)
            path = pkg_resources.resource_filename('behappy', 'templates/{}'.format(t))
            shutil.copytree(path, './target/{}'.format(t))

    def _resize_images(self):
        resizer = ImageResizer()
        for album in self.gallery.albums():
            path = Path('./target/album/{}'.format(album.id))
            path.mkdir(parents=True, exist_ok=True)
            count = 0
            count_all = 0
            for image in album.image_set.images(all=True):
                for name, size in settings.image_sizes().items():
                    option = ResizeOptions.from_settings(size, name)
                    r = resizer.resize(image.path, image.cache_path(album.id, option), option)
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
