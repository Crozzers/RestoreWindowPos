import json
import logging
import operator
import os
import re
import sys
import threading
import time
import typing
from typing import Callable, Any, Union
from dataclasses import dataclass, field, is_dataclass

import win32con

log = logging.getLogger(__name__)

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


def match(a: int | str, b: int | str) -> int:
    '''`b` must be of the same type as `a`'''
    if a is None or b is None:
        return 1
    if a == b:
        return 2

    if isinstance(a, int):
        return 2 if abs(a) == abs(b) else 0

    try:
        return 0 if re.match(a, b, re.IGNORECASE) is None else 1
    except re.error:
        log.exception(f'fail to compile pattern "{a}"')
        return 0


def str_to_op(op_name: str) -> Callable[[Any, Any], bool]:
    if op_name in ('lt', 'le', 'eq', 'ge', 'gt'):
        return getattr(operator, op_name)
    raise ValueError(f'invalid operation {op_name!r}')


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
                if isinstance(value, tuple):
                    # only convert sub items in tuple because tuple
                    # types are positional
                    try:
                        value = field_type(sub_types[i](
                            value[i]) for i in range(len(value)))
                    except ValueError:
                        pass
            else:
                if issubclass(field_type, JSONType):
                    value = field_type.from_json(data[field_name])
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


@dataclass
class WindowType(JSONType):
    size: XandY
    rect: Rect
    placement: Placement

    def fits_display(self, display: 'Display') -> bool:
        rect = self.rect
        if self.placement[1] == win32con.SW_SHOWMINIMIZED:
            rect = self.placement[4]
        if self.placement[1] == win32con.SW_SHOWMAXIMIZED:
            offset = 8
        else:
            # check if a window might be snapped and give it a bit more room
            if (
                abs(self.size[0] - (display.resolution[0] // 2)) <= 10
                or abs(self.size[1] - (display.resolution[1] // 2)) <= 10
            ):
                offset = 5
            else:
                offset = 0
        return (
            rect[0] >= display.rect[0] - offset
            and rect[1] >= display.rect[1] - offset
            and rect[2] <= display.rect[2] + offset
            and rect[3] <= display.rect[3] + offset
        )

    def fits_display_config(self, displays: list['Display']) -> bool:
        return any(self.fits_display(d) for d in displays)


@dataclass(slots=True)
class Window(WindowType):
    id: int
    name: str
    executable: str


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
    comparison_params: dict[str, str | list[str]] = field(default_factory=dict)
    '''
    Optional member detailing how comparisons should be made between members of
    this class and members of another class
    '''

    def matches(self, display: 'Display'):
        # check UIDs
        if display.uid and not match(self.uid, display.uid):
            return False
        # check names
        if display.name and not match(self.name, display.name):
            return False
        # check resolution
        for index, metric in enumerate(zip(display.resolution, self.resolution)):
            if 0 in metric:
                continue
            op = self.comparison_params.get('resolution', ('eq', 'eq'))[index]
            if not str_to_op(op)(*metric):
                return False
        else:
            return True

    def matches_config(self, config: list['Display']):
        return any(self.matches(d) for d in config)

    def set_res(self, index, value):
        self.resolution = list(self.resolution)
        self.resolution[index] = value
        self.resolution = tuple(self.resolution)


@dataclass(slots=True)
class Rule(WindowType):
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
    phony: str = ''

    @classmethod
    def from_json(cls, data: dict):
        if 'history' not in data:
            if 'windows' in data:
                data['history'] = [{
                    'time': time.time(),
                    'windows': data.pop('windows')
                }]
        if 'phony' in data:
            if data['phony'] is False:
                data['phony'] = ''
            elif data['phony'] is True:
                if data['displays'] == []:
                    data['phony'] = 'Global'
                else:
                    data['phony'] = 'Unnamed Layout'

        return super(cls, cls).from_json(data)


def display_configs_match(current: list[Display], displays: list[Display]):
    for d2 in displays:
        # all of the displays in the config must match at least once to the
        # current config. If there are no matches, break
        if not d2.matches_config(current):
            break
    else:
        # all displays match at least once to the current config
        # so return True
        return True
