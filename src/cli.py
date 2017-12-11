# -*- coding: utf-8 -*-
import os
from functools import wraps
from http.server import HTTPServer, SimpleHTTPRequestHandler
from time import time

import click

from behappy.main import BeHappy


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
@click.option('--count', default=1, help='Number of greetings.')
@timeit
def build(count):
    """
    Build static site
    """
    blog = BeHappy()
    blog.build()


@cli.command()
def server(port=8000):
    """
    Run test web server
    """
    if not os.path.exists(conf.DEPLOY_PATH):
        os.mkdir(conf.DEPLOY_PATH)
    os.chdir(conf.DEPLOY_PATH)

    httpd = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    print('# server at http://127.0.0.1:{0}'.format(port))
    httpd.serve_forever()


@cli.command()
def clear():
    """
    Remove deploy directory
    """
    pass


@cli.command()
def new(url):
    """
    Create new post file. Get url name of new post.
    """
    pass


if __name__ == '__main__':
    cli()
