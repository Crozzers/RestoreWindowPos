import json
import logging
import operator
import os
import re
import sys
import threading
import time
import typing
from dataclasses import dataclass, field, is_dataclass
from functools import lru_cache
from typing import Any, Callable, Iterable, Literal, Optional, Union

import pythoncom
import pywintypes
import win32api
import win32con
import win32gui
import win32process
import wmi

log = logging.getLogger(__name__)

# some basic types
XandY = tuple[int, int]
Rect = tuple[int, int, int, int]
'''X, W, Y, H'''
Placement = tuple[int, int, XandY, XandY, Rect]
'''Flags, showCmd, min pos, max pos, normal pos'''


def local_path(path, asset=False):
    if getattr(sys, 'frozen', False):
        if asset:
            base = sys._MEIPASS  # type: ignore
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


def match(a: Optional[int | str], b: Optional[int | str]) -> int:
    '''
    Check if `a` matches `b` as an integer or string.
    Values are deemed to be "matching" if they are equal in some way, with more exact equalities
    resulting in stronger matches. Integers are matched on absulute value. Strings are matched
    against `a` as a regex.

    Returns:
        A score that indicates how well the two match. 0 means no match, 1 means
        partial match and 2 means exact match.
    '''

    if a is None or b is None:
        return 1
    if a == b:
        return 2

    # both must be same type. Just do this to make type checker happy
    if isinstance(a, int) and isinstance(b, int):
        return 2 if abs(a) == abs(b) else 0

    if isinstance(a, str) and isinstance(b, str):
        try:
            return 0 if re.match(a, b, re.IGNORECASE) is None else 1
        except re.error:
            log.exception(f'fail to compile pattern "{a}"')
            return 0

    return 0


def str_to_op(op_name: str) -> Callable[[Any, Any], bool]:
    if op_name in ('lt', 'le', 'eq', 'ge', 'gt'):
        return getattr(operator, op_name)
    raise ValueError(f'invalid operation {op_name!r}')


class JSONFile():
    def __init__(self, file: str, *a, **kw):
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


@lru_cache
def load_json(file: Literal['settings',  'history']):
    '''
    Load a JSON file and cache the instance. Useful for creating global instances for settings files.
    The `.json` suffix is automatically added if missing.
    '''
    json_file = JSONFile(file + '.json')
    json_file.load()
    return json_file


def tuple_convert(item: Iterable, to=tuple, from_: type = list):
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
    resizable: bool = True

    def __post_init__(self):
        self.resizable = self.is_resizable()

    @property
    def parent(self) -> Optional['Window']:
        p_id = win32gui.GetParent(self.id)
        if p_id == 0:
            return None
        return self.from_hwnd(p_id)

    def center_on(self, coords: XandY):
        '''
        Centers the window around a point, making sure to keep it on screen
        '''
        # get basic centering coords
        w, h = self.get_size()
        x = coords[0] - (w // 2)
        y = coords[1] - (h // 2)
        display = win32api.MonitorFromPoint(coords, win32con.MONITOR_DEFAULTTONEAREST)
        # use working area rather than total monitor area so we don't move window into the taskbar
        display_rect = win32api.GetMonitorInfo(display)['Work']
        dx, dy, drx, dry = display_rect
        # make sure bottom right corner is on-screen
        x, y = min(drx - w, x), min(dry - h, y)
        # make sure x, y >= top left corner of display
        x, y = max(dx, x), max(dy, y)
        self.move((x, y))

    def focus(self):
        '''
        Raises a window and brings it to the top of the Z order.

        Called 'focus' rather than 'raise' because the latter is a keyword
        '''
        win32gui.BringWindowToTop(self.id)
        win32gui.ShowWindow(self.id, win32con.SW_SHOWNORMAL)

    @classmethod
    def from_hwnd(cls, hwnd: int) -> 'Window':
        if threading.current_thread() != threading.main_thread():
            pythoncom.CoInitialize()
        w = wmi.WMI()
        # https://stackoverflow.com/a/14973422
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        exe = w.query(
            f'SELECT ExecutablePath FROM Win32_Process WHERE ProcessId = {pid}')[0]
        rect = win32gui.GetWindowRect(hwnd)

        return Window(id=hwnd, name=win32gui.GetWindowText(hwnd),
                      executable=exe.ExecutablePath,
                      size=size_from_rect(rect),
                      rect=rect,
                      placement=win32gui.GetWindowPlacement(hwnd)
                      )

    def get_placement(self) -> Placement:
        self.placement = win32gui.GetWindowPlacement(self.id)
        return self.placement

    def get_rect(self) -> Rect:
        self.rect = win32gui.GetWindowRect(self.id)
        return self.rect

    def get_size(self) -> XandY:
        return size_from_rect(self.get_rect())

    def is_minimised(self) -> bool:
        return self.get_placement()[1] == win32con.SW_SHOWMINIMIZED

    def is_resizable(self) -> bool:
        return win32gui.GetWindowLong(self.id, win32con.GWL_STYLE) & win32con.WS_THICKFRAME

    def move(self, coords: XandY):
        '''
        Move the window to a new position. This does not resize the window or
        adjust placement
        '''
        size = size_from_rect(win32gui.GetWindowRect(self.id))
        win32gui.MoveWindow(self.id, *coords, *size, False)
        self.refresh()

    def refresh(self):
        '''Re-fetch stale window information'''
        self.rect = self.get_rect()
        self.placement = self.get_placement()
        self.size = size_from_rect(self.rect)
        self.name = win32gui.GetWindowText(self.id)
        self.resizable = self.is_resizable()

    def set_pos(self, rect: Rect, placement: Optional[Placement] = None):
        '''
        Set the position, size and placement of the window
        '''
        try:
            if self.is_resizable():
                w, h = size_from_rect(rect)
            else:
                # if the window is not resizeable, make sure we don't resize it.
                # includes 95 era system dialogs and the Outlook reminder window
                w, h = self.get_size()
                if placement:
                    placement = (*placement[:-1], (*rect[:2], rect[0] + w, rect[1] + h))

            if placement:
                win32gui.SetWindowPlacement(self.id, placement)

            win32gui.MoveWindow(self.id, *rect[:2], w, h, True)
            log.debug(f'move window {self.id}, X,Y:{rect[:2]!r}, W:{w}, H:{h}')
            self.refresh()
        except pywintypes.error as e:
            log.error('err moving window %s : %s' %
                      (win32gui.GetWindowText(self.id), e))


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
        res = list(self.resolution)
        res[index] = value
        self.resolution = tuple(res)  # type: ignore


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
    comparison_params: dict[str, str | list[str]] = field(default_factory=dict)
    '''
    Optional member detailing how comparisons should be made between members of
    this class and members of another class
    '''

    def cleanup(self, prune=True, ttl=0, maximum=10):
        '''
        Perform a variety of operations to clean up the window history

        Args:
            prune: remove windows that no longer exist
            ttl: remove captures older than this. Set to 0 to ignore
            maximum: max number of captures to keep
        '''
        self.squash_history(prune)
        if ttl != 0:
            current = time.time()
            self.history = [i for i in self.history if current - i.time <= ttl]
        if len(self.history) > maximum:
            self.history = self.history[-maximum:]

    @classmethod
    def from_json(cls, data: dict) -> Optional['Snapshot']:
        '''
        Returns:
            A new snapshot, or None if `data` is falsey
        '''
        if not data:
            return None

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

    def last_known_process_instance(self, process: str, title: Optional[str] = None) -> Window | None:
        def compare_titles(base: str, other: str):
            base_chunks = base.split()
            if base == other:
                # shortcut
                return len(base_chunks)
            score = 0
            for a, b in zip(reversed(base_chunks), reversed(other.split())):
                if a != b:
                    return score
                score += 1
            return score

        contenders: list = []
        for history in reversed(self.history):
            for window in reversed(history.windows):
                if window.executable == process:
                    if not title:
                        return window
                    contenders.append(window)

        if not title:
            return None

        contenders.sort(key=lambda x: compare_titles(title, x.name), reverse=True)
        if contenders:
            return contenders[0]

    # use union because `|` doesn't like string forward refs
    def matches_display_config(self, config: Union[list[Display], 'Snapshot']) -> bool:
        '''
        Whether this snapshot is deemed compatible with a another snapshot/list
        of displays.
        Can operate in 2 modes depending on how `self.comparison_params` are set.
        If set to 'all' mode every display in this snapshot must find a match
        within `config`. Otherwise, only one match needs to be found.
        '''
        if isinstance(config, Snapshot):
            config = config.displays
        matches, misses = 0, 0
        for display in self.displays:
            if display.matches_config(config):
                matches += 1
            else:
                misses += 1

        mode = self.comparison_params.get('displays')
        if mode == 'all':
            return misses == 0
        return matches >= 1

    def squash_history(self, prune=True):
        '''
        Squashes the window history by merging overlapping captures and
        removing duplicates.

        Args:
            prune: remove windows that no longer exist
        '''
        def should_keep(window: Window) -> bool:
            try:
                if prune:
                    return (
                        # window exists and hwnd still belongs to same process
                        win32gui.IsWindow(window.id) == 1
                        and window.id in exe_by_id
                        and window.executable == exe_by_id[window.id]
                    )
                return (
                    # hwnd is not in use by another window
                    window.id not in exe_by_id
                    or window.executable == exe_by_id[window.id]
                )
            except Exception:
                return False

        index = len(self.history) - 1
        exe_by_id = {}
        while index > 0:
            for window in self.history[index].windows:
                if window.id not in exe_by_id:
                    try:
                        exe_by_id[window.id] = window.executable
                    except KeyError:
                        pass

            current = self.history[index].windows = list(
                filter(should_keep, self.history[index].windows))
            previous = self.history[index - 1].windows = list(
                filter(should_keep, self.history[index - 1].windows))

            if len(current) > len(previous):
                # if current is greater but contains all the items of previous
                smaller, greater = previous, current
                to_pop = index - 1
            else:
                # if current is lesser but all items are already in previous
                smaller, greater = current, previous
                to_pop = index

            for window_a in smaller:
                if window_a in greater:
                    continue

                for window_b in greater:
                    if (
                        window_a.id == window_b.id
                        and window_a.rect == window_b.rect
                        and window_a.placement == window_b.placement
                    ):
                        break
                else:
                    break
            else:
                # successful loop, all items in smaller are already present in greater.
                # remove smaller
                self.history.pop(to_pop)

            index -= 1
