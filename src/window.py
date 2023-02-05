import ctypes
import ctypes.wintypes
import logging
import re
import threading

import pythoncom
import pywintypes
import win32con
import win32gui
import win32process
import wmi

from common import Placement, Rect, Rule, Window, size_from_rect

log = logging.getLogger(__name__)


class TitleBarInfo(ctypes.Structure):
    _fields_ = [('cbSize', ctypes.wintypes.DWORD),
                ('rcTitleBar', ctypes.wintypes.RECT),
                ('rgState', ctypes.wintypes.DWORD * 6)]


def is_window_valid(hwnd: int) -> bool:
    if not win32gui.IsWindow(hwnd):
        return False
    if not win32gui.IsWindowVisible(hwnd):
        return False
    if not win32gui.GetWindowText(hwnd):
        return False
    if win32gui.GetWindowRect(hwnd) == (0, 0, 0, 0):
        return False

    # https://stackoverflow.com/a/64597308
    # https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/nf-dwmapi-dwmgetwindowattribute
    # https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/ne-dwmapi-dwmwindowattribute
    cloaked = ctypes.c_int(0)
    ctypes.windll.dwmapi.DwmGetWindowAttribute(
        hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked))
    if cloaked.value != 0:
        return False

    titlebar = TitleBarInfo()
    titlebar.cbSize = ctypes.sizeof(titlebar)
    ctypes.windll.user32.GetTitleBarInfo(hwnd, ctypes.byref(titlebar))
    return not titlebar.rgState[0] & win32con.STATE_SYSTEM_INVISIBLE


def from_hwnd(hwnd: int) -> Window:
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


def capture_snapshot() -> list[Window]:
    def callback(hwnd, *_):
        if is_window_valid(hwnd):
            snapshot.append(from_hwnd(hwnd))

    snapshot = []
    win32gui.EnumWindows(callback, None)
    return snapshot


def find_matching_rules(rules: list[Rule], window: Window):
    def match(pattern, text):
        if pattern == text:
            return True
        try:
            return re.match(pattern, text, re.IGNORECASE)
        except re.error:
            log.exception(f'fail to compile pattern "{pattern}"')
            return False

    for rule in rules:
        name_match = rule.name is None or match(rule.name, window.name)
        exe_match = rule.executable is None or match(
            rule.executable, window.executable)
        if name_match and exe_match:
            yield rule


def apply_positioning(hwnd: int, rect: Rect, placement: Placement = None):
    try:
        if placement:
            win32gui.SetWindowPlacement(hwnd, placement)
        w, h = size_from_rect(rect)
        win32gui.MoveWindow(hwnd, *rect[:2], w, h, 0)
    except pywintypes.error as e:
        log.error('err moving window %s : %s' %
                  (win32gui.GetWindowText(hwnd), e))


def restore_snapshot(snap: list[Window], rules: list[Rule] = None):
    def callback(hwnd, extra):
        if not is_window_valid(hwnd):
            return

        window = from_hwnd(hwnd)
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

            log.debug(
                f'restore window "{window["name"]}" {window["rect"]} -> {item.rect}')
            apply_positioning(hwnd, item.rect, placement)
            return
        else:
            if not rules:
                return
            for rule in find_matching_rules(rules, window):
                log.debug(f'apply rule "{rule.rule_name}" to "{window.name}"')
                apply_positioning(hwnd, rule.rect, rule.placement)

    win32gui.EnumWindows(callback, None)
