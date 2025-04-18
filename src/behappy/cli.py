# -*- coding: utf-8 -*-
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

import click

from behappy.core.conf import settings
from behappy.core.main import BeHappy, BeHappyFile, BeHappySync
from behappy.core.utils import timeit


@click.group()
def main():
    pass


@main.command()
@click.option('--target', default='target', help='Path to build folder')
@click.option('--conf', default='behappy.ini', help='Path to config')
@click.option('--tags', default='', help='Filter albums by tags')
@click.option('--processes', default='4', type=int, help='Pool size')
@timeit
def build(target, conf, tags, processes):
    """
    Build static site
    """
    settings.load(conf)

    tags = set([i.strip() for i in tags.split(',') if i.strip()])
    blog = BeHappy(target, tags)
    blog.build(processes)


@main.command()
@click.option('--target', default='target', help='Path to build folder')
@click.option('--port', default='8000', help='Path to build folder')
def server(target, port):
    """
    Run test web server
    """
    if not os.path.exists(target):
        os.mkdir(target)
    os.chdir(target)

    httpd = HTTPServer(('0.0.0.0', int(port)), SimpleHTTPRequestHandler)
    print('# server at http://127.0.0.1:{0}'.format(port))
    httpd.serve_forever()


@main.command()
def new():
    """
    Create new album.
    """
    folder = Path('.').absolute()
    file = BeHappyFile(folder)
    file.new()


@main.command()
@click.option('--target', default='target', help='Path to build folder')
@click.option('--profile', default=None, help='AWS profile')
@click.option('--endpoint', default=None, help='S3 endpoint url')
@click.option('--bucket', help='S3 bucket name')
@click.option('--cloudfront', default=None, help='AWS cloudfront distribution id')
@timeit
def sync(target, profile, endpoint, bucket, cloudfront):
    """
    Run test web server
    """
    folder = Path(target)
    be_sync = BeHappySync(folder, profile, endpoint, bucket)
    print('Sync S3')
    be_sync.s3()
    if cloudfront:
        print('Invalidate CloudFront')
        be_sync.cloudfront_invalidate(cloudfront)


if __name__ == '__main__':
    main()
