# -*- coding: utf-8 -*-
import os
from pathlib import Path

from pytz import timezone


class Settings:
    def __init__(self):
        pass

    def source_folders(self):
        paths = os.environ['SOURCE_FOLDERS'].split(':')
        return [Path(i) for i in paths]

    def description(self):
        return 'Gallery description'

    def timezone(self):
        return timezone('UTC')

    def image_sizes(self):
        return {
            'small': {
                'WIDTH': 300,
                'HEIGHT': 300,
                'CROP': True,
            },
            'big': {
                'WIDTH': 1920,
                'HEIGHT': 1080,
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
