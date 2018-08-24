# -*- coding: utf-8 -*-
import os
from functools import wraps
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from time import time

import click

from behappy.core.conf import settings
from behappy.core.main import BeHappy, BeHappyFile


def timeit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        start = time()
        try:
            f(*args, **kwargs)
        finally:
            elapsed = int(time() - start)
            print('## {0} complete in {1:d} min {2:d} sec'.format(f.__name__, elapsed // 60, elapsed % 60))

    return wrapper


@click.group()
def main():
    pass


@main.command()
@click.option('--target', default='target', help='Path to build folder')
@click.option('--conf', default='behappy.ini', help='Path to config')
@click.option('--tags', default='', help='Filter albums by tags')
@timeit
def build(target, conf, tags):
    """
    Build static site
    """
    settings.load(conf)

    tags = set([i.strip() for i in tags.split(',') if i.strip()])
    blog = BeHappy(target, tags)
    blog.build()


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


if __name__ == '__main__':
    main()
