import json
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
        self.file = file

    def load(self, default=None):
        try:
            with open(local_path(self.file), 'r') as f:
                self.data = json.load(f)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            self.data = default if default is not None else {}

    def save(self):
        with open(local_path(self.file), 'w') as f:
            json.dump(self.data, f)

    def set(self, key, value):
        self.data[key] = value
        self.save()

    def get(self, key, default=None):
        try:
            return self.data[key]
        except (IndexError, KeyError):
            return default
