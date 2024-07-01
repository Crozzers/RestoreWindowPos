import logging
import re
import time
from dataclasses import asdict
from typing import Iterator, Literal, Optional

import pywintypes
import win32api

from common import Display, JSONFile, Snapshot, WindowHistory, load_json, local_path, size_from_rect
from services import Service
from window import capture_snapshot, restore_snapshot

log = logging.getLogger(__name__)


def enum_display_devices() -> list[Display]:
    result = []
    for monitor in win32api.EnumDisplayMonitors():
        try:
            info = win32api.GetMonitorInfo(monitor[0])  # type: ignore
        except pywintypes.error:
            log.exception(f'GetMonitorInfo failed on handle {monitor[0]}')
            continue
        dev_rect = info['Monitor']
        for adaptor_index in range(5):
            try:
                device = win32api.EnumDisplayDevices(info['Device'], adaptor_index, 1)
                dev_uid = re.findall(r'UID[0-9]+', device.DeviceID)[0]
                dev_name = device.DeviceID.split('#')[1]
            except Exception:
                pass
            else:
                result.append(Display(uid=dev_uid, name=dev_name, resolution=size_from_rect(dev_rect), rect=dev_rect))
    return result


class SnapshotFile(JSONFile):
    data: list[Snapshot]

    def __init__(self):
        super().__init__(local_path('history.json'))
        self.load()

    def load(self):
        super().load(default=[])
        g_phony_found = False
        for index in range(len(self.data)):
            snapshot: Snapshot = Snapshot.from_json(self.data[index]) or Snapshot()
            self.data[index] = snapshot
            snapshot.history.sort(key=lambda a: a.time)

            if snapshot.phony == 'Global' and snapshot.displays == []:
                g_phony_found = True

        if not g_phony_found:
            self.data.append(Snapshot(phony='Global'))

        self.data = list(filter(None, self.data))

    def save(self):
        with self.lock:
            return super().save([asdict(i) for i in self.data])

    def restore(self, timestamp: Optional[float] = None):
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
                restore_snapshot(history[-1].windows, rules)
            elif timestamp:
                restore_ts(timestamp)
            else:
                if not (snap.mru and restore_ts(snap.mru)):
                    restore_snapshot(history[-1].windows, rules)

    def capture(self):
        """
        Captures the info for a snapshot but does not update the history.
        Use `update` instead.
        """
        self._log.info('capture snapshot')
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

    def get_compatible_snapshots(self, compatible_with: Optional[Snapshot] = None) -> Iterator[Snapshot]:
        with self.lock:
            if compatible_with is None:
                compatible_with = self.get_current_snapshot()

            for snap in self.data:
                if snap == compatible_with or not snap.phony:
                    continue
                if not compatible_with.matches_display_config(snap.displays):
                    continue
                yield snap

    def get_rules(self, compatible_with: Optional[Snapshot | Literal[True]] = None, exclusive=False):
        with self.lock:
            current = self.get_current_snapshot()
            if not compatible_with:
                return current.rules

            if compatible_with is True:
                compatible_with: Snapshot = current

            rules = [] if exclusive else compatible_with.rules.copy()
            for snap in self.get_compatible_snapshots(compatible_with):
                rules.extend(r for r in snap.rules if r.fits_display_config(compatible_with.displays))
            return rules

    def prune_history(self):
        settings = load_json('settings')
        with self.lock:
            for snapshot in self.data:
                if snapshot.phony:
                    continue
                snapshot.cleanup(
                    prune=settings.get('prune_history', True),
                    ttl=settings.get('window_history_ttl', 0),
                    maximum=settings.get('max_snapshots', 10),
                )

    def update(self):
        """Captures a new snapshot, updates and prunes the history then saves to disk"""
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

            self.save()


class SnapshotService(Service):
    def _runner(self, snapshot: SnapshotFile):
        count = 0
        settings = load_json('settings')
        while not self._kill_signal.is_set():
            if not settings.get('pause_snapshots', False):
                snapshot.update()
                count += 1

            if count >= settings.get('save_freq', 1):
                snapshot.save()
                count = 0

            sleep_start = time.time()
            while time.time() - sleep_start < settings.get('snapshot_freq', 30):
                time.sleep(0.5)
                if self._kill_signal.is_set():
                    return
