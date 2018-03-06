# -*- coding: utf-8 -*-
import os
from functools import wraps
from http.server import HTTPServer, SimpleHTTPRequestHandler

import click

from behappy.core.conf import settings
from behappy.core.main import BeHappy
from time import time


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
def cli():
    pass


@cli.command()
@click.option('--conf', default='behappy.ini', help='Path to config')
@click.option('--tags', default='', help='Filter albums by tags')
@timeit
def build(conf, tags):
    """
    Build static site
    """
    settings.load(conf)

    tags = set([i.strip() for i in tags.split(',') if i.strip()])
    blog = BeHappy(tags)
    blog.build()


@cli.command()
def server(port=8000):
    """
    Run test web server
    """
    if not os.path.exists('target'):
        os.mkdir('target')
    os.chdir('target')

    httpd = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print('# server at http://127.0.0.1:{0}'.format(port))
    httpd.serve_forever()


@cli.command()
def new():
    """
    Create new album.
    """
    pass


if __name__ == '__main__':
    cli()
