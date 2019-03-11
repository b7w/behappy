# -*- coding: utf-8 -*-
import logging
import os
import shutil

from PIL import Image

logger = logging.getLogger(__name__)


class ResizeOptions(object):
    """
    Options for resize such as width, height,
    max size - max of width/height,
    crop - need or not.
    """

    def __init__(self, width=0, height=0, crop=False, quality=95, name=None):
        """
        :type name: str
        """
        self.width = width
        self.height = height
        self.size = max(self.width, self.height)
        self.crop = crop
        self.quality = quality
        self.name = name if name else None
        if not (80 <= quality <= 100):
            raise Exception('Image QUALITY settings have to be between 80 and 100')

    @classmethod
    def from_settings(cls, setting, name=None):
        return ResizeOptions(
            width=setting['WIDTH'],
            height=setting['HEIGHT'],
            crop='CROP' in setting and setting['CROP'] is True,
            quality=setting.get('QUALITY', 95),
            name=name,
        )

    def __repr__(self):
        return 'ImageOptions(width={w}, height={h}, crop={c}, quality={q}, name={n})' \
            .format(w=self.width, h=self.height, c=self.crop, q=self.quality, n=self.name)


class BetterImage(object):
    """
    Get file with image. Resize, rotate, crop it.
    """
    ORIENTATION_KEY = 274  # cf ExifTags
    ORIENTATION_VALUES = {3: 180, 6: 270, 8: 90}

    def __init__(self, filein, orientation):
        self.file = Image.open(filein)
        self.orientation = orientation
        if self.file.mode not in ('L', 'RGB'):
            self.file = self.file.convert('RGB')
        self.type = 'JPEG'

    @property
    def width(self):
        """
        Return image width
        """
        return self.file.size[0]

    @property
    def height(self):
        """
        Return image height
        """
        return self.file.size[1]

    def resize(self, width, height):
        """
        Resize image to `width` and `width`
        """
        self.file = self.file.resize((width, height), Image.ANTIALIAS)

    def crop(self, x_offset, y_offset, width, height):
        """
        Crop image with `x_offset`, `y_offset`, `width`, `height`
        """
        self.file = self.file.crop((x_offset, y_offset, width, height))

    def rotate(self):
        if self.need_rotate():
            self.file = self.file.rotate(self.orientation)

    def crop_center(self, width, height):
        """
        Cut out an image with `width` and `height` of the center
        """
        x_offset = int((self.width - width) / 2)
        y_offset = int((self.height - height) / 2)
        self.crop(x_offset, y_offset, x_offset + width, y_offset + height)

    def is_portrait(self):
        """
        Is width < height
        """
        return self.width < self.height

    def is_landscape(self):
        """
        Is width >= height
        """
        return self.width >= self.height

    def is_bigger(self, width, height):
        """
        Is this image bigger that `width` or `height`
        """
        return self.width > width or self.height > height

    def need_rotate(self):
        return self.orientation != 0

    def scale_min_size(self, value):
        """
        Scale images size where the min size len will be `value`
        """
        if self.is_landscape():
            scale = float(self.height) / value
            width = int(self.width / scale)
            return width, value
        else:
            scale = float(self.width) / value
            height = int(self.height / scale)
            return value, height

    def scale_to(self, width, height):
        """
        Scale images size where `width` and `height` will be max values
        """
        if self.is_portrait():
            scale = float(self.height) / height
            width = int(self.width / scale)
            return width, height
        else:
            scale = float(self.width) / width
            height = int(self.height / scale)
            return width, height

    def save_to(self, fout, quality):
        """
        Save to open file. Need to close by yourself.

        :type fout: file
        :type quality: int
        """
        self.file.save(fout, self.type, quality=quality)


class ImageResizer:
    def resize(self, from_path, to_path, option, orientation):
        if not to_path.exists():
            to_path.parent.mkdir(parents=True, exist_ok=True)
            with from_path.open(mode='rb') as fin:
                resize_image = BetterImage(fin, orientation)
                bigger = resize_image.is_bigger(option.width, option.height)
                if bigger:
                    if option.crop:
                        w, h = resize_image.scale_min_size(option.size)
                        resize_image.resize(w, h)
                        resize_image.crop_center(option.width, option.height)
                    else:
                        w, h = resize_image.scale_to(option.width, option.height)
                        resize_image.resize(w, h)

                if resize_image.need_rotate():
                    resize_image.rotate()

                if bigger or resize_image.need_rotate():
                    with to_path.open(mode='wb') as fout:
                        resize_image.save_to(fout, option.quality)
                else:
                    shutil.copy2(from_path.as_posix(), to_path.as_posix())

            os.chmod(to_path.as_posix(), 0o644)
            return True
        return False
