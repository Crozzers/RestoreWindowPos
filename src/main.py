import logging
import signal
import time

import win32con
import win32gui

from common import JSONFile, Window, local_path, single_call
from device import DeviceChangeCallback, DeviceChangeService
from gui import TaskbarIcon, WxApp, about_dialog, radio_menu
from gui.wx_app import spawn_gui
from services import ServiceCallback
from snapshot import SnapshotFile, SnapshotService
from window import (WindowSpawnService, apply_positioning, apply_rules,
                    from_hwnd, is_window_valid, restore_snapshot)


def update_systray_options():
    global menu_options

    if SETTINGS.get('pause_snapshots', False):
        menu_options[1][0] = 'Resume snapshots'
    else:
        menu_options[1][0] = 'Pause snapshots'

    history_menu = []
    for config in snap.get_history():
        timestamp = config.time
        label = time.strftime('%b %d %H:%M:%S', time.localtime(timestamp))
        history_menu.append(
            [label, lambda *_, t=timestamp: snap.restore(t)])

    if history_menu:
        history_menu.insert(0, TaskbarIcon.SEPARATOR)
        history_menu.insert(
            0, ['Clear history', lambda *_: clear_restore_options()])

    menu_options[2][1][:-2] = history_menu

    current_snapshot = snap.get_current_snapshot()
    layout_menu = []
    for snapshot in snap.data:
        if not snapshot.phony:
            continue
        layout_menu.append([snapshot.phony, lambda *_, s=snapshot: restore_snapshot([], s.rules)])
    menu_options[7][1][1:] = layout_menu

    rule_menu = []
    for header, ruleset in (
        ('Current Snapshot', current_snapshot.rules),
        ('All Compatible', snap.get_rules(
            compatible_with=True, exclusive=True))
    ):
        if not ruleset:
            continue
        rule_menu.extend([TaskbarIcon.SEPARATOR, [header]])
        for rule in ruleset:
            rule_menu.append([rule.rule_name or 'Unnamed Rule',
                              lambda *_, r=rule: restore_snapshot([], [r])])
    menu_options[8][1][:-2] = rule_menu


def clear_restore_options():
    result = win32gui.MessageBox(
        None,
        'Are you sure you want to clear the snapshot history for this display configuration?',
        'Clear snapshot history?',
        win32con.MB_YESNO | win32con.MB_ICONWARNING
    )
    if result == win32con.IDYES:
        snap.clear_history()


def rescue_windows(snap: SnapshotFile):
    def callback(hwnd, _):
        if not is_window_valid(hwnd):
            return
        window = from_hwnd(hwnd)
        if not window.fits_display_config(displays):
            rect = [0, 0, *window.size]
            logging.info(f'rescue window {window.name!r} {window.rect} -> {rect}')
            apply_positioning(hwnd, rect)

    displays = snap.get_current_snapshot().displays
    win32gui.EnumWindows(callback, None)


def on_window_spawn(windows: list[Window]):
    if not SETTINGS.get('apply_snapshot_on_window_spawn', True):
        return
    current_snap = snap.get_current_snapshot()
    rules = snap.get_rules(compatible_with=True, exclusive=True)
    for window in windows:
        if (last_instance := current_snap.last_known_process_instance(window.executable)):
            apply_positioning(window.id, last_instance.rect, last_instance.placement)
        else:
            apply_rules(rules, window)


if __name__ == '__main__':
    logging.basicConfig(filename=local_path('log.txt'),
                        filemode='w',
                        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    log = logging.getLogger(__name__)
    log.info('start')

    SETTINGS = JSONFile('settings.json')
    SETTINGS.load()
    SETTINGS.set('pause_snapshots', False)  # reset this key

    logging.getLogger().setLevel(logging.getLevelName(SETTINGS.get('log_level', 'INFO').upper()))

    snap = SnapshotFile()
    app = WxApp()

    menu_options = [
        ['Capture now', lambda *_: snap.update()],
        ['Pause snapshots', lambda *_: SETTINGS.set(
            'pause_snapshots', not SETTINGS.get('pause_snapshots', False))],
        ['Restore snapshot', [
            TaskbarIcon.SEPARATOR,
            ['Most recent', lambda *_: snap.restore(-1)]
        ]],
        ['Rescue windows', lambda *_: rescue_windows(snap)],
        TaskbarIcon.SEPARATOR,
        [
            'Snapshot frequency', radio_menu(
                {'5 seconds': 5, '10 seconds': 10, '30 seconds': 30, '1 minute': 60,
                 '5 minutes': 300, '10 minutes': 600, '30 minutes': 1800, '1 hour': 3600},
                lambda: SETTINGS.get('snapshot_freq', 60),
                lambda v: SETTINGS.set('snapshot_freq', v)
            )
        ],
        TaskbarIcon.SEPARATOR,
        ['Apply layout', [
            ['Current Snapshot', lambda *_: restore_snapshot([], snap.get_rules())]
        ]],
        ['Apply rules', [
            TaskbarIcon.SEPARATOR,
            ['Apply all', lambda *_: restore_snapshot([], snap.get_rules(compatible_with=True))]
        ]],
        ['Configure rules', lambda *_: spawn_gui(snap, SETTINGS, 'rules')],
        TaskbarIcon.SEPARATOR,
        ['Settings', lambda *_: spawn_gui(snap, SETTINGS, 'settings')],
        ['About', lambda *_: about_dialog()]
    ]

    @single_call
    def shutdown(*_):
        log.info('begin shutdown process')
        app.ExitMainLoop()
        monitor_thread.stop()
        snapshot_service.stop()
        log.info('save snapshot before shutting down')
        snap.save()
        log.info('exit')

    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGABRT):
        signal.signal(sig, shutdown)

    with TaskbarIcon(menu_options, on_click=update_systray_options, on_exit=shutdown):
        monitor_thread = DeviceChangeService(
            DeviceChangeCallback(snap.restore, shutdown, snap.update),
            snap.lock
        )
        monitor_thread.start()
        window_spawn_thread = WindowSpawnService(ServiceCallback(on_window_spawn))
        window_spawn_thread.start()
        snapshot_service = SnapshotService(None)
        snapshot_service.start(args=(snap, SETTINGS))

        try:
            app.MainLoop()
        except KeyboardInterrupt:
            pass
        finally:
            shutdown()
