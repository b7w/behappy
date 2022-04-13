# -*- coding: utf-8 -*-

from setuptools import setup

setup(
    name='behappy',
    version='0.4',
    install_requires=[i.strip() for i in open('requirements.txt').readlines() if i.strip()],
    packages=['behappy', 'behappy.core', ],
    package_dir={'': 'src'},
    include_package_data=True,
    entry_points={
        'console_scripts': [
            'behappy = behappy.cli:main',
        ],
    },
    url='https://bitbucket.org/b7w/behappy',
    license='MIT',
    author='B7W',
    author_email='b7w@isudo.ru',
    description=open('README.md').read(),
)
