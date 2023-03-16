import logging
import re
import time
from dataclasses import asdict

import pywintypes
import win32api
import win32gui

from common import (Display, JSONFile, Snapshot, Window, WindowHistory,
                    local_path, size_from_rect)
from services import Service
from window import capture_snapshot, restore_snapshot

log = logging.getLogger(__name__)


def enum_display_devices() -> list[Display]:
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
                result.append(Display(uid=dev_uid, name=dev_name,
                              resolution=size_from_rect(dev_rect), rect=dev_rect))
    return result


class SnapshotFile(JSONFile):
    data: list[Snapshot]

    def __init__(self):
        super().__init__(local_path('history.json'))
        self.load()

    def load(self):
        super().load(default=[])
        for index in range(len(self.data)):
            snapshot: Snapshot = Snapshot.from_json(
                self.data[index]) or Snapshot()
            self.data[index] = snapshot
            snapshot.history.sort(key=lambda a: a.time)

    def save(self):
        return super().save([asdict(i) for i in self.data])

    def restore(self, timestamp: float = None):
        with self.lock:
            snap = self.get_current_snapshot()
            if snap is None or not snap.history:
                return
            rules = self.get_rules(compatible_with=snap)

            history = snap.history

            def restore_ts(timestamp: float):
                for config in history:
                    if config.time == timestamp:
                        restore_snapshot(config.windows, rules)
                        snap.mru = timestamp
                        return True

            self._log.info(f'restore snapshot, timestamp={timestamp}')
            if timestamp == -1:
                restore_snapshot(
                    history[-1].windows, rules)
            elif timestamp:
                restore_ts(timestamp)
            else:
                if not (snap.mru and restore_ts(snap.mru)):
                    restore_snapshot(history[-1].windows, rules)

    def capture(self):
        self._log.debug('capture snapshot')
        return time.time(), enum_display_devices(), capture_snapshot()

    def get_current_snapshot(self) -> Snapshot:
        displays = enum_display_devices()

        def find():
            for ss in self.data:
                if ss.phony:
                    continue
                if ss.displays == displays:
                    return ss

        with self.lock:
            snap = find()
            if snap is None:
                self.update()
                snap = find()
            return snap

    def get_history(self):
        with self.lock:
            snap = self.get_current_snapshot()
            return snap.history

    def get_rules(self, compatible_with: Snapshot = None, exclusive=False):
        with self.lock:
            if not compatible_with:
                return self.get_current_snapshot().rules

            rules = [] if exclusive else compatible_with.rules.copy()
            for snap in self.data:
                if snap == compatible_with or not snap.phony:
                    continue
                rules.extend(r for r in snap.rules if r.fits_display_config(compatible_with.displays))
            return rules

    def clear_history(self):
        with self.lock:
            snap = self.get_current_snapshot()
            snap.history = []

    def squash(self, history: list[WindowHistory]):
        def should_keep(window: Window):
            if not win32gui.IsWindow(window.id):
                return False
            try:
                return (
                    window.id in exe_by_id
                    and window.executable == exe_by_id[window.id]
                )
            except Exception:
                return False

        index = len(history) - 1
        exe_by_id = {}
        while index > 0:
            for window in history[index].windows:
                if window.id not in exe_by_id:
                    try:
                        exe_by_id[window.id] = window.executable
                    except KeyError:
                        pass

            current = history[index].windows = list(
                filter(should_keep, history[index].windows))
            previous = history[index - 1].windows = list(
                filter(should_keep, history[index - 1].windows))

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
                history.pop(to_pop)

            index -= 1

    def prune_history(self):
        with self.lock:
            for snapshot in self.data:
                if snapshot.phony:
                    continue
                self.squash(snapshot.history)

                if len(snapshot.history) > 10:
                    snapshot.history = snapshot.history[-10:]

    def update(self):
        timestamp, displays, windows = self.capture()

        if not displays:
            return

        with self.lock:
            wh = WindowHistory(time=timestamp, windows=windows)
            for item in self.data:
                if item.displays == displays:
                    # add current config to history
                    item.history.append(wh)
                    item.mru = None
                    break
            else:
                self.data.append(Snapshot(displays=displays, history=[wh]))

            self.prune_history()


class SnapshotService(Service):
    def _runner(self, snapshot: SnapshotFile, settings: JSONFile):
        count = 0
        while not self._kill_signal.is_set():
            if not settings.get('pause_snapshots', False):
                snapshot.update()
                count += 1

            if count >= settings.get('save_freq', 1):
                snapshot.save()
                count = 0

            sleep_start = time.time()
            while time.time() - sleep_start < settings.get('snapshot_freq', 30):
                time.sleep(1)
                if self._kill_signal.is_set():
                    return
