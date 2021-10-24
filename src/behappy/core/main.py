# -*- coding: utf-8 -*-
import configparser
import io
import itertools
import mimetypes
import shutil
from datetime import datetime
from multiprocessing.pool import Pool
from pathlib import Path

import boto3
import pkg_resources
from dateutil.parser import parse
from jinja2 import Environment, PackageLoader

from behappy.core.conf import settings
from behappy.core.model import Gallery, ImageSet, VideoSet, Album
from behappy.core.resize import ResizeOptions, ImageResizer
from behappy.core.utils import uid, timeit


def date_filter(value, fmt):
    return value.strftime(fmt)


def linebreaksbr_filter(value):
    return value.replace('\n', '<br/>')


def _resize_image(img, cache_path, option):
    resizer = ImageResizer()
    r = resizer.resize(img.path, cache_path, option, img.orientation)
    if r:
        return 1
    return 0


class BeHappyFile:
    def __init__(self, folder):
        """
        :type folder: Path
        """
        self.folder = folder

    def new(self):
        title = self._title()
        date = self._parse_or_now()
        thumbnail = self._first_image()
        config = self._create(title, date, thumbnail)
        buffer = io.StringIO()
        config.write(buffer)

        with Path(self.folder, 'behappy.ini').open(mode='w') as f:
            buffer.seek(0)
            f.write(buffer.read().strip() + '\n')

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


class BeHappySync:
    def __init__(self, folder, profile, bucket):
        """
        :type folder: Path
        """
        self.folder = folder
        self._session = boto3.session.Session(profile_name=profile)
        self._bucket = self._session.resource('s3').Bucket(name=bucket)
        self._cloudfront = self._session.client('cloudfront')

    def s3(self):
        objects = list(self._bucket.objects.all())
        files = [i.relative_to(self.folder).as_posix() for i in self.folder.glob('**/*') if
                 i.is_file() and not i.name.startswith('.')]
        print('Load {} s3 objects and {} local files'.format(len(objects), len(files)))

        # upload new album/*.jpg
        new_images = set(i for i in files if i.endswith('.jpg')) - \
                     set(i.key for i in objects if i.key.endswith('.jpg'))
        print('{} images for upload: {}'.format(len(new_images), ','.join(new_images)))
        for i in new_images:
            self._s3_upload(i)

        # upload other
        other = set(i for i in files if not i.endswith('.jpg'))
        print('{} files for upload: {}'.format(len(other), ', '.join(other)))
        for i in other:
            self._s3_upload(i)

        # delete removed files
        for_delete = set(i.key for i in objects) - set(files)
        print('{} files for delete: {}'.format(len(for_delete), ', '.join(for_delete)))
        for i in objects:
            if i.key in for_delete:
                i.delete()

    def cloudfront_invalidate(self, distribution_id):
        files = [i.relative_to(self.folder).as_posix() for i in self.folder.glob('**/*.html') if
                 i.is_file() and not i.name.startswith('.')]
        print('Find {} html files'.format(len(files)))
        print('\n'.join(files))
        self._cloudfront.create_invalidation(
            DistributionId=distribution_id,
            InvalidationBatch={
                'Paths': {
                    'Quantity': len(files),
                    'Items': ['/{}'.format(f) for f in files]
                },
                'CallerReference': 'my-references-{}'.format(datetime.now())
            }
        )

    def _s3_upload(self, key):
        file = Path(self.folder, key)
        content_type = mimetypes.types_map.get(file.suffix, 'application/octet-stream')
        self._bucket.upload_file(file.as_posix(), key, ExtraArgs={'ContentType': content_type})


class BeHappy:
    def __init__(self, target, tags):
        self.gallery = Gallery(settings.title(), settings.description())
        self.target = target
        self.tags = tags
        self.jinja = Environment(
            loader=PackageLoader('behappy.core'),
            trim_blocks=True
        )
        self.jinja.filters['date'] = date_filter
        self.jinja.filters['linebreaksbr'] = linebreaksbr_filter
        self.jinja.globals['now'] = datetime.now()

    def build(self):
        print('Start..')
        self._load_albums()
        self._resize_images()
        self._copy_video()
        self._copy_static_resources()
        self._write_robots()
        self._render_about_page()
        self._render_index_page()
        self._render_year_pages()
        self._render_album_pages()
        self._render_error_page(name='404', title='404', message='Page not found')
        print('Done!')

    @timeit
    def _render_about_page(self):
        html = self.jinja.get_template('about.jinja2').render(**settings.templates_parameters(),
                                                              **settings.about())
        folder = Path(self.target, 'about')
        folder.mkdir(parents=True, exist_ok=True)
        with Path(folder, 'index.html').open(mode='w') as f:
            f.write(html)

    @timeit
    def _render_index_page(self):
        params = dict(title=self.gallery.title,
                      html_title='',
                      description=self.gallery.description,
                      albums=self.gallery.top_albums(),
                      years=self.gallery.top_years())
        html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                **settings.templates_parameters())
        with Path(self.target, 'index.html').open(mode='w') as f:
            f.write(html)

    @timeit
    def _render_year_pages(self):
        groped = {}
        for album in self.gallery.top_albums():
            groped.setdefault(album.date.year, []).append(album)
        for year, albums in groped.items():
            params = dict(title=self.gallery.title,
                          html_title='Year {}'.format(year),
                          description=self.gallery.description,
                          albums=albums,
                          years=self.gallery.top_years(),
                          current_year=year)
            html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                    **settings.templates_parameters())
            folder = Path(self.target, 'year', str(year))
            folder.mkdir(parents=True, exist_ok=True)
            with Path(folder, 'index.html').open(mode='w') as f:
                f.write(html)

    @timeit
    def _render_album_pages(self):
        for album in self.gallery.albums():
            if album.children:
                albums = sorted(album.children, key=lambda x: x.date)
                params = dict(title=album.title,
                              html_title=album.title,
                              description=album.description,
                              albums=albums,
                              back=dict(id=album.parent))
                html = self.jinja.get_template('gallery.jinja2').render(**params,
                                                                        **settings.templates_parameters())
            else:
                params = dict(album=album,
                              images=album.image_set.images(),
                              videos=album.video_set.videos(),
                              back=dict(id=album.parent))
                html = self.jinja.get_template('album.jinja2').render(**params,
                                                                      **settings.templates_parameters())
            with Path(self.target, 'album', str(album.id), 'index.html').open(mode='w') as f:
                f.write(html)

    @timeit
    def _render_error_page(self, name, title, message):
        html = self.jinja.get_template('message.jinja2').render(title=title, message=message,
                                                                **settings.templates_parameters())
        folder = Path(self.target, 'error')
        folder.mkdir(parents=True, exist_ok=True)
        with Path(folder, '{}.html'.format(name)).open(mode='w') as f:
            f.write(html)

    @timeit
    def _copy_static_resources(self):
        for t in ('css', 'img', 'js'):
            path = Path(self.target, t).as_posix()
            shutil.rmtree(path, ignore_errors=True)
            path_from = pkg_resources.resource_filename('behappy.core', 'templates/{}'.format(t))
            shutil.copytree(path_from, path)

    @timeit
    def _write_robots(self):
        with Path(self.target, 'robots.txt').open(mode='w') as f:
            f.writelines([
                'User-agent: *\n',
                'Disallow: /\n',
            ])

    @timeit
    def _resize_images(self):
        with Pool() as pool:
            for album in self.gallery.albums():
                path = Path(self.target, 'album', str(album.id))
                path.mkdir(parents=True, exist_ok=True)
                tasks = []
                for image in album.image_set.images(all=True):
                    for name, size in settings.image_sizes().items():
                        option = ResizeOptions.from_settings(size, name)
                        cache_path = image.cache_path(self.target, album.id, option)
                        tasks.append((image, cache_path, option,))
                result = pool.starmap(_resize_image, tasks)

                print('[{}] {} of {} resizes'.format(album.title, sum(result), len(result)))

    @timeit
    def _copy_video(self):
        for album in self.gallery.albums():
            total = 0
            copied = 0
            path = Path(self.target, 'album', str(album.id))
            path.mkdir(parents=True, exist_ok=True)
            for video in album.video_set.videos():
                total += 1
                Path(path, 'video').mkdir(exist_ok=True)
                cache_path = video.cache_path(self.target, album.id)
                if not cache_path.exists():
                    copied += 1
                    shutil.copy(video.path, cache_path)

            print('[{}] {} of {} copied videos'.format(album.title, copied, total))

    @timeit
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
                video_set = VideoSet(
                    path=ini.parent,
                    include=conf.get('videos', 'include', fallback=None),
                    exclude=conf.get('videos', 'exclude', fallback=None),
                    sortby=conf.get('videos', 'sortby', fallback='date'),
                )
                album = Album(
                    id=conf.get('album', 'id'),
                    parent=conf.get('album', 'parent', fallback=None),
                    title=conf.get('album', 'title'),
                    description=conf.get('album', 'description'),
                    date=conf.get('album', 'date'),
                    tags=conf.get('album', 'tags', fallback=''),
                    hidden=conf.getboolean('album', 'hidden', fallback=False),
                    path=ini.parent,
                    image_set=image_set,
                    video_set=video_set
                )
                if not self.tags or any(i in album.tags for i in self.tags):
                    self.gallery.add_album(album)
        for album in self.gallery.albums():
            album.children = [i for i in self.gallery.albums() if album.id == i.parent]

        albums_count = len(self.gallery.albums())
        image_count = sum(len(i.image_set.images(all=True)) for i in self.gallery.albums())
        print('Load {} albums and {} images'.format(albums_count, image_count))
        if self.gallery.top_hidden_albums():
            print('Find {} hidden albums:'.format(len(self.gallery.top_hidden_albums())))
            for album in self.gallery.top_hidden_albums():
                print('\t{} [{}] {} images'.format(album.id, album.title, len(album.image_set.images())))
