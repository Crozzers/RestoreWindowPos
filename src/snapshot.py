import ctypes
import logging
import re
import threading
import time

import pythoncom
import pywintypes
import win32api
import win32gui
import win32process
import wmi

from common import JSONFile, local_path, size_from_rect

log = logging.getLogger(__name__)


def enum_display_devices():
    result = []
    for monitor in win32api.EnumDisplayMonitors():
        try:
            info = win32api.GetMonitorInfo(monitor[0])
        except pywintypes.error:
            log.exception(f'GetMonitorInfo failed on handle {monitor[0]}')
            continue
        dev_rect = info['Monitor']
        for adaptor_index in range(5):
            try:
                device = win32api.EnumDisplayDevices(
                    info['Device'], adaptor_index, 1)
                dev_uid = re.findall(r'UID[0-9]+', device.DeviceID)[0]
                dev_name = device.DeviceID.split('#')[1]
            except Exception:
                pass
            else:
                result.append({
                    'uid': dev_uid,
                    'name': dev_name,
                    'resolution': size_from_rect(dev_rect),
                    'rect': list(dev_rect)
                })
    return result


class Window:
    _log = log.getChild('Window')

    @staticmethod
    def is_window_valid(hwnd: int) -> bool:
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
        if ctypes.windll.dwmapi.DwmGetWindowAttribute(hwnd, 14, ctypes.byref(cloaked), ctypes.sizeof(cloaked)):
            # if this throws error then assume window is safe
            cloaked = 0
        return cloaked == 0

    @staticmethod
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

    @classmethod
    def capture_snapshot(cls) -> list[dict]:
        def callback(hwnd, extra):
            if cls.is_window_valid(hwnd):
                window = cls.from_hwnd(hwnd)
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

    @classmethod
    def find_matching_rules(cls, rules: list[dict], window: dict):
        def match(pattern, text):
            if pattern == text:
                return True
            try:
                return re.match(pattern, text)
            except re.error:
                cls._log.exception(f'fail to compile pattern "{pattern}"')
                return False

        for rule in rules:
            name_match = rule.get('name') is None or match(rule.get('name'), window['name'])
            exe_match = rule.get('executable') is None or match(rule.get('executable'), window['executable'])
            if name_match and exe_match:
                yield rule

    @classmethod
    def apply_positioning(cls, hwnd: int, rect: tuple, placement: list = None):
        try:
            if placement:
                win32gui.SetWindowPlacement(hwnd, placement)
            win32gui.MoveWindow(
                hwnd, *rect[:2], rect[2] - rect[0], rect[3] - rect[1], 0)
        except pywintypes.error as e:
            cls._log.error('err moving window %s : %s' %
                           (win32gui.GetWindowText(hwnd), e))
            pass

    @classmethod
    def restore_snapshot(cls, snap: list[dict], rules: list[dict] = None):
        def callback(hwnd, extra):
            if not cls.is_window_valid(hwnd):
                return

            window = cls.from_hwnd(hwnd)
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

                cls._log.debug(
                    f'restore window "{window["name"]}" {window["rect"]} -> {rect}')
                cls.apply_positioning(hwnd, rect, placement)
                return
            else:
                if not rules:
                    return
                for rule in cls.find_matching_rules(rules, window):
                    cls._log.debug(
                        f'apply rule {rule.get("name") or rule.get("executable")} to "{window["name"]}"')
                    cls.apply_positioning(hwnd, rule.get(
                        'rect'), rule.get('placement'))

        win32gui.EnumWindows(callback, None)


class Snapshot(JSONFile):
    def __init__(self):
        super().__init__(local_path('history.json'))
        self.load()
        self.lock = threading.RLock()

    def load(self):
        super().load(default=[])
        for snapshot in self.data:
            if 'history' in snapshot:
                snapshot['history'].sort(key=lambda a: a.get('time'))
            else:
                if 'windows' in snapshot:
                    snapshot['history'] = [{
                        'time': time.time(),
                        'windows': snapshot.pop('windows')
                    }]
                else:
                    snapshot['history'] = []

    def restore(self, timestamp=None):
        with self.lock:
            snap = self.get_current_snapshot()
            if snap is None or snap.get('history') is None:
                return

            history = snap['history']

            def restore_ts(timestamp):
                for config in history:
                    if config['time'] == timestamp:
                        Window.restore_snapshot(
                            config['windows'], snap.get('rules'))
                        snap['mru'] = timestamp
                        return True

            self._log.info(f'restore snapshot, timestamp={timestamp}')
            if timestamp == -1:
                Window.restore_snapshot(
                    history[-1]['windows'], snap.get('rules'))
            elif timestamp:
                restore_ts(timestamp)
            else:
                if not (snap.get('mru') and restore_ts(snap.get('mru'))):
                    Window.restore_snapshot(
                        history[-1]['windows'], snap.get('rules'))

    def capture(self):
        self._log.debug('capture snapshot')
        return time.time(), enum_display_devices(), Window.capture_snapshot()

    def get_current_snapshot(self):
        displays = enum_display_devices()

        with self.lock:
            for ss in self.data:
                if ss['displays'] == displays:
                    return ss

    def get_history(self):
        with self.lock:
            snap = self.get_current_snapshot()
            if snap is not None:
                return snap['history']

    def clear_history(self):
        with self.lock:
            snap = self.get_current_snapshot()
            if snap is not None:
                snap['history'] = []

    def squash(self, history):
        index = len(history) - 1
        while index > 0:
            current = history[index]['windows']
            previous = history[index - 1]['windows']

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
                    # in future compare program of origin
                    if window_a['id'] == window_b['id']:
                        if window_a['rect'] == window_b['rect']:
                            if window_a['placement'] == window_b['placement']:
                                break
                else:
                    break
            else:
                # successful loop, all items in smaller are already present in greater.
                # remove smaller
                history.pop(to_pop)

            index -= 1

    def prune_history(self):
        with self.lock:
            for snapshot in self.data:
                self.squash(snapshot['history'])

                if len(snapshot['history']) > 10:
                    snapshot['history'] = snapshot['history'][-10:]

    def update(self):
        timestamp, displays, windows = self.capture()

        if not displays:
            return

        with self.lock:
            for item in self.data:
                if item['displays'] == displays:
                    # add current config to history
                    item['history'].append({
                        'time': timestamp,
                        'windows': windows
                    })
                    item['mru'] = None
                    break
            else:
                self.data.append({
                    'displays': displays,
                    'history': [{
                        'time': timestamp,
                        'windows': windows
                    }]
                })

            self.prune_history()
