import ctypes
import ctypes.wintypes
import logging
import time
from typing import Iterator

import pyvda
import win32con
import win32gui
from comtypes import GUID

from common import Rule, Window, load_json, match
from services import Service

log = logging.getLogger(__name__)


class TitleBarInfo(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.wintypes.DWORD),
                ('rcTitleBar', ctypes.wintypes.RECT),
                ('rgState', ctypes.wintypes.DWORD * 6)]


class WindowSpawnService(Service):
    def _runner(self):
        def get_windows() -> set[int]:
            hwnds = set()
            win32gui.EnumWindows(lambda h, *_: hwnds.add(h), None)
            return hwnds

        settings = load_json('settings')
        old = get_windows()
        while not self._kill_signal.wait(timeout=0.1):
            if not settings.get('on_window_spawn', {}).get('enabled', False):
                time.sleep(1)
                continue
            new = get_windows() - old
            if new:
                # wait for window to load in before checking validity
                time.sleep(0.1)
                try:
                    windows = [Window.from_hwnd(h) for h in new if is_window_valid(h)]
                except Exception:
                    self.log.info('failed to get list of newly spawned windows')
                self._run_callback('default', windows)
            old.update(new)


def is_window_cloaked(hwnd) -> bool:
    # https://stackoverflow.com/a/64597308
    # https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/nf-dwmapi-dwmgetwindowattribute
    # https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
    cloaked = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    if cloaked.value != 0:
        try:
            # this seems to do a pretty decent job catching all cloaked windows
            # whilst allowing windows on other v_desktops
            app_view = pyvda.AppView(hwnd=hwnd)
            if app_view.desktop_id == GUID():  # GUID({"00000000..."})
                return True
            assert app_view.desktop.number > 0
        except Exception:
            return True
    return False


def is_window_valid(hwnd: int) -> bool:
    if not win32gui.IsWindow(hwnd):
        return False
    if not win32gui.IsWindowVisible(hwnd):
        return False
    if not win32gui.GetWindowText(hwnd):
        return False
    if win32gui.GetWindowRect(hwnd) == (0, 0, 0, 0):
        return False
    if is_window_cloaked(hwnd):
        return False

    titlebar = TitleBarInfo()
    titlebar.cbSize = ctypes.sizeof(titlebar)
    ctypes.windll.user32.GetTitleBarInfo(hwnd, ctypes.byref(titlebar))
    return not titlebar.rgState[0] & win32con.STATE_SYSTEM_INVISIBLE


def capture_snapshot() -> list[Window]:
    def callback(hwnd, *_):
        if is_window_valid(hwnd):
            snapshot.append(Window.from_hwnd(hwnd))

    snapshot = []
    win32gui.EnumWindows(callback, None)
    return snapshot


def find_matching_rules(rules: list[Rule], window: Window) -> Iterator[Rule]:
    matching: list[tuple[int, Rule]] = []
    for rule in rules:
        points = 0
        for attr in ('name', 'executable'):
            rv = getattr(rule, attr)
            wv = getattr(window, attr)
            p = match(rv, wv)
            if not p:
                break
            if rv:
                points += p
        else:
            matching.append((points, rule))
    return (i[1] for i in sorted(matching, reverse=True, key=lambda m: m[0]))


def apply_rules(rules: list[Rule], window: Window):
    for rule in find_matching_rules(rules, window):
        window.set_pos(rule.rect, rule.placement)


def restore_snapshot(snap: list[Window], rules: list[Rule] = None):
    def callback(hwnd, extra):
        if not is_window_valid(hwnd):
            return

        window = Window.from_hwnd(hwnd)
        for item in snap:
            if item.rect == (0, 0, 0, 0):
                return

            if hwnd != item.id:
                continue

            if window.rect == item.rect:
                return

            try:
                placement = item.placement
            except KeyError:
                placement = None

            log.info(
                f'restore window "{window.name}" {window.rect} -> {item.rect}')
            window.set_pos(item.rect, placement)
            return
        else:
            if not rules:
                return
            for rule in find_matching_rules(rules, window):
                log.info(f'apply rule "{rule.rule_name}" to "{window.name}"')
                window.set_pos(rule.rect, rule.placement)

    win32gui.EnumWindows(callback, None)
