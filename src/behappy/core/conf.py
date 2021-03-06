# -*- coding: utf-8 -*-
import configparser
from pathlib import Path

from pytz import timezone


class Settings:

    def __init__(self):
        self._conf = None

    def load(self, path):
        self._conf = configparser.ConfigParser()
        self._conf.read(path)

    def source_folders(self):
        paths = self._conf.get('gallery', 'source').split(';')
        return [Path(i.strip()) for i in paths if i]

    def title(self):
        return self._conf.get('gallery', 'title').strip()

    def description(self):
        return self._conf.get('gallery', 'description').strip()

    def timezone(self):
        tz = self._conf.get('gallery', 'timezone', fallback='UTC').strip()
        return timezone(tz)

    def image_sizes(self):
        sec = [i for i in self._conf.sections() if i.startswith('images:')]
        res = {}
        for sec in sec:
            name = sec.replace('images:', '')
            res[name] = {
                'WIDTH': self._conf.getint(sec, 'width'),
                'HEIGHT': self._conf.getint(sec, 'height'),
                'CROP': self._conf.getboolean(sec, 'crop', fallback=False),
            }

        return res

    def about(self):
        return {
            'title': self._conf.get('about', 'title'),
            'text': self._conf.get('about', 'text'),
        }

    def copyright(self):
        return {
            'email': self._conf.get('copyright', 'email'),
            'username': self._conf.get('copyright', 'username'),
        }

    def template_extra_html(self):
        return self._conf.get('template', 'extra_html', fallback='')

    def image_size(self, name):
        return self.image_sizes()[name]

    def templates_parameters(self):
        return {
            'copyright': self.copyright(),
            'EXTRA_HTML': self.template_extra_html()
        }


settings = Settings()
