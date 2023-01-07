import json
import logging
import os
import sys


def local_path(path, asset=False):
    if getattr(sys, 'frozen', False):
        if asset:
            base = sys._MEIPASS
        else:
            base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir))

    return os.path.abspath(os.path.join(base, path))


def size_from_rect(rect) -> tuple[int]:
    return [
        rect[2] - rect[0],
        rect[3] - rect[1]
    ]


class JSONFile():
    def __init__(self, file, *a, **kw):
        self._log = logging.getLogger(__name__).getChild(
            self.__class__.__name__
            + '.' + str(id(self))
        )
        self.file = file

    def load(self, default=None):
        try:
            with open(local_path(self.file), 'r') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.data = default if default is not None else {}
        except Exception:
            self._log.exception('failed to load file "%s"' % self.file)
            raise

    def save(self):
        try:
            with open(local_path(self.file), 'w') as f:
                json.dump(self.data, f)
        except Exception:
            self._log.exception('failed to save file "%s"' % self.file)
            raise

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def get(self, key, default=None):
        try:
            return self.data[key]
        except (IndexError, KeyError):
            return default


def format_unit(unit, value):
    if unit == 'second' and value % 60 == 0:
        unit, value = 'minute', int(value / 60)
    if value == 1:
        return f'{value} {unit}'
    return f'{value} {unit}s'