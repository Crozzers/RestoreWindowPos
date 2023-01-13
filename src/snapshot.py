import logging
import re
import threading
import time

import pywintypes
import win32api
import win32gui

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

    def capture_snapshot():
        def callback(hwnd, extra):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                if not title or rect == (0, 0, 0, 0):
                    return
                snapshot.append(
                    {
                        'id': hwnd,
                        'name': title,
                        'size': size_from_rect(rect),
                        'rect': rect,
                        'placement': win32gui.GetWindowPlacement(hwnd)
                    }
                )

        snapshot = []
        win32gui.EnumWindows(callback, None)
        return snapshot

    @classmethod
    def restore_snapshot(cls, snap: dict):
        def callback(hwnd, extra):
            for item in snap:
                if hwnd != item['id']:
                    continue

                rect = tuple(item['rect'])
                current = win32gui.GetWindowRect(hwnd)
                if current == rect:
                    return

                try:
                    placement = item['placement']
                except KeyError:
                    placement = None

                try:
                    if placement:
                        win32gui.SetWindowPlacement(hwnd, placement)
                    win32gui.MoveWindow(
                        hwnd, *rect[:2], rect[2] - rect[0], rect[3] - rect[1], 0)
                    cls._log.debug(
                        f'restore window "{win32gui.GetWindowText(hwnd)}" {current} -> {rect}')
                except pywintypes.error as e:
                    cls._log.error('err moving window %s : %s' %
                                   (win32gui.GetWindowText(hwnd), e))
                    pass

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
                        Window.restore_snapshot(config['windows'])
                        snap['mru'] = timestamp
                        return True

            if timestamp:
                restore_ts(timestamp)
            elif timestamp == -1:
                Window.restore_snapshot(history[-1]['windows'])
            else:
                if not (snap.get('mru') and restore_ts(snap.get('mru'))):
                    Window.restore_snapshot(history[-1]['windows'])

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
                    if window_a['id'] == window_b['id']:  # in future compare program of origin
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
