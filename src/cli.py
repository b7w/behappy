# -*- coding: utf-8 -*-
import os
from http.server import HTTPServer, SimpleHTTPRequestHandler
from time import time

import click

from behappy.main import BeHappy


@click.group()
def cli():
    pass


@cli.command()
@click.option('--count', default=1, help='Number of greetings.')
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
    try:
        t = time()
        print('# done {0:.4f} second'.format(time() - t))
    except Exception as e:
        print('#! Error:', e)
