import ctypes
import ctypes.wintypes
import logging
import re
import sys
import threading

import pythoncom
import pywintypes
import win32con
import win32gui
import win32process
import wmi

from common import size_from_rect

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
    window = from_hwnd(hwnd)
    if not window['name']:
        return False
    if window['rect'] == (0, 0, 0, 0):
        return False
    if window['executable'] == sys.executable:
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


def from_hwnd(hwnd: int) -> dict:
    if threading.current_thread() != threading.main_thread():
        pythoncom.CoInitialize()
    w = wmi.WMI()
    # https://stackoverflow.com/a/14973422
    _, pid = win32process.GetWindowThreadProcessId(hwnd)
    exe = w.query(
        f'SELECT ExecutablePath FROM Win32_Process WHERE ProcessId = {pid}')[0]

    return {
        'name': win32gui.GetWindowText(hwnd),
        'rect': win32gui.GetWindowRect(hwnd),
        'executable': exe.ExecutablePath
    }


def capture_snapshot() -> list[dict]:
    def callback(hwnd, extra):
        if is_window_valid(hwnd):
            window = from_hwnd(hwnd)
            snapshot.append(
                {
                    'id': hwnd,
                    'name': window['name'],
                    'executable': window['executable'],
                    'size': size_from_rect(window['rect']),
                    'rect': window['rect'],
                    'placement': win32gui.GetWindowPlacement(hwnd)
                }
            )

    snapshot = []
    win32gui.EnumWindows(callback, None)
    return snapshot


def find_matching_rules(rules: list[dict], window: dict):
    def match(pattern, text):
        if pattern == text:
            return True
        try:
            return re.match(pattern, text)
        except re.error:
            log.exception(f'fail to compile pattern "{pattern}"')
            return False

    for rule in rules:
        name_match = rule.get('name') is None or match(
            rule.get('name'), window['name'])
        exe_match = rule.get('executable') is None or match(
            rule.get('executable'), window['executable'])
        if name_match and exe_match:
            yield rule


def apply_positioning(hwnd: int, rect: tuple, placement: list = None):
    try:
        if placement:
            win32gui.SetWindowPlacement(hwnd, placement)
        win32gui.MoveWindow(
            hwnd, *rect[:2], rect[2] - rect[0], rect[3] - rect[1], 0)
    except pywintypes.error as e:
        log.error('err moving window %s : %s' %
                  (win32gui.GetWindowText(hwnd), e))
        pass


def restore_snapshot(snap: list[dict], rules: list[dict] = None):
    def callback(hwnd, extra):
        if not is_window_valid(hwnd):
            return

        window = from_hwnd(hwnd)
        for item in snap:
            rect = tuple(item['rect'])
            if rect == (0, 0, 0, 0):
                return

            if hwnd != item['id']:
                continue

            if window['rect'] == rect:
                return

            try:
                placement = item['placement']
            except KeyError:
                placement = None

            log.debug(
                f'restore window "{window["name"]}" {window["rect"]} -> {rect}')
            apply_positioning(hwnd, rect, placement)
            return
        else:
            if not rules:
                return
            for rule in find_matching_rules(rules, window):
                log.debug(
                    f'apply rule {rule.get("name") or rule.get("executable")} to "{window["name"]}"')
                apply_positioning(hwnd, rule.get(
                    'rect'), rule.get('placement'))

    win32gui.EnumWindows(callback, None)
