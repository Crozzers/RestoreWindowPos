import json
import logging
import os
import sys
import threading
import time
import typing
from dataclasses import dataclass, field, is_dataclass

# some basic types
XandY = tuple[int, int]
Rect = tuple[int, int, int, int]
Placement = tuple[int, int, XandY, XandY, Rect]


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


def single_call(func):
    has_been_called = False

    def inner_func(*a, **kw):
        nonlocal has_been_called
        if has_been_called:
            return
        has_been_called = True
        return func(*a, **kw)

    return inner_func


def size_from_rect(rect: Rect) -> XandY:
    return (
        rect[2] - rect[0],
        rect[3] - rect[1]
    )


def reverse_dict_lookup(d: dict, value):
    return list(d.keys())[list(d.values()).index(value)]


class JSONFile():
    def __init__(self, file, *a, **kw):
        self._log = logging.getLogger(__name__).getChild(
            self.__class__.__name__
            + '.' + str(id(self))
        )
        self.file = file
        self.lock = threading.RLock()

    def load(self, default=None):
        with self.lock:
            try:
                with open(local_path(self.file), 'r') as f:
                    self.data = json.load(f)
            except (FileNotFoundError, json.decoder.JSONDecodeError):
                self.data = default if default is not None else {}
            except Exception:
                self._log.exception('failed to load file "%s"' % self.file)
                raise

    def save(self, data=None):
        with self.lock:
            if data is None:
                data = self.data
            try:
                with open(local_path(self.file), 'w') as f:
                    json.dump(data, f)
            except Exception:
                self._log.exception('failed to save file "%s"' % self.file)
                raise

    def set(self, key, value):
        with self.lock:
            self.data[key] = value
            self.save()

    def get(self, key, default=None):
        with self.lock:
            try:
                return self.data[key]
            except (IndexError, KeyError):
                return default


def tuple_convert(item, to=tuple, from_=list):
    if isinstance(item, from_):
        item = to(tuple_convert(sub, to=to, from_=from_) for sub in item)
    return item


class JSONType:
    @classmethod
    def from_json(cls, data: dict):
        if is_dataclass(data):
            return data

        init_data = {}
        hints = typing.get_type_hints(cls)
        for field_name, field_type in hints.items():
            if field_name not in data:
                continue
            sub_types = typing.get_args(field_type)
            if sub_types and issubclass(sub_types[0], JSONType):
                value = field_type(
                    filter(None, (sub_types[0].from_json(i) for i in data[field_name])))
            elif sub_types:
                value = tuple_convert(
                    data[field_name], to=field_type, from_=tuple | list)
            else:
                try:
                    value = field_type(data[field_name])
                except TypeError:
                    value = data[field_name]
            init_data[field_name] = value

        try:
            return cls(**init_data)
        except TypeError:
            return None


@dataclass(slots=True)
class Window(JSONType):
    id: int
    name: str
    executable: str
    size: XandY
    rect: Rect
    placement: Placement


@dataclass(slots=True)
class WindowHistory(JSONType):
    time: float
    windows: list[Window] = field(default_factory=list)


@dataclass(slots=True)
class Display(JSONType):
    uid: str
    name: str
    resolution: XandY
    rect: Rect


@dataclass(slots=True)
class Rule(JSONType):
    size: XandY
    rect: Rect
    placement: Placement
    name: str | None = None
    executable: str | None = None
    rule_name: str | None = None

    def __post_init__(self):
        if self.rule_name is None:
            # TODO: create name from window name and/or exe
            self.rule_name = 'Unnamed rule'


@dataclass(slots=True)
class Snapshot(JSONType):
    displays: list[Display] = field(default_factory=list)
    history: list[WindowHistory] = field(default_factory=list)
    mru: float | None = None
    rules: list[Rule] = field(default_factory=list)
    phony: bool = False

    @classmethod
    def from_json(cls, data: dict):
        if 'history' not in data:
            if 'windows' in data:
                data['history'] = [{
                    'time': time.time(),
                    'windows': data.pop('windows')
                }]
        return super(cls, cls).from_json(data)
