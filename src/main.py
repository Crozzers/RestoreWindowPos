# Sources:
# https://stackoverflow.com/questions/69712306/list-all-windows-with-win32gui
# http://timgolden.me.uk/pywin32-docs/win32gui__GetWindowRect_meth.html
# http://timgolden.me.uk/pywin32-docs/win32gui__MoveWindow_meth.html
# Todo:
# https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settingchange
# https://stackoverflow.com/questions/5981520/detect-external-display-being-connected-or-removed-under-windows-7
import logging
import threading
import time

import win32con
import win32gui

from common import JSONFile, local_path
from device import DeviceChangeService
from gui import about_dialog, exit_root, spawn_rule_manager
from snapshot import SnapshotFile, SnapshotService
from systray import SysTray, submenu_from_settings
from window import restore_snapshot


def pause_snapshots(systray):
    if SETTINGS.get('pause_snapshots', False):
        SETTINGS.set('pause_snapshots', False)
        verb = 'Pause'
    else:
        SETTINGS.set('pause_snapshots', True)
        verb = 'Resume'

    global menu_options
    menu_options[0][0] = f'{verb} snapshots'
    systray.update(menu_options=True)


def update_systray_options(systray):
    history_menu = []
    for config in snap.get_history():
        timestamp = config.time
        label = time.strftime('%b %d %H:%M:%S', time.localtime(timestamp))
        history_menu.append(
            [label, None, lambda s, t=timestamp: snap.restore(t)])

    if history_menu:
        history_menu.insert(0, ['Clear history', None,
                                lambda s: clear_restore_options()])

    global menu_options
    menu_options[2][2][:-1] = history_menu

    rule_menu = []
    for rule in snap.get_rules():
        rule_menu.append([
            rule.rule_name or 'Unnamed Rule', None,
            lambda s, r=rule: restore_snapshot([], [r])]
        )
    menu_options[3][2][:-1] = rule_menu

    systray.update(menu_options=menu_options)


def clear_restore_options():
    result = win32gui.MessageBox(
        None,
        'Are you sure you want to clear the snapshot history for this display configuration?',
        'Clear snapshot history?',
        win32con.MB_YESNO | win32con.MB_ICONWARNING
    )
    if result == win32con.IDYES:
        snap.clear_history()


if __name__ == '__main__':
    logging.basicConfig(filename=local_path('log.txt'),
                        filemode='w',
                        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                        level=logging.DEBUG)
    log = logging.getLogger(__name__)
    log.info('start')

    SETTINGS = JSONFile('settings.json')
    SETTINGS.load()
    SETTINGS.set('pause_snapshots', False)  # reset this key
    EXIT = threading.Event()

    snap = SnapshotFile()

    menu_options = [
        ['Capture Now', None, lambda s: snap.update()],
        ['Pause Snapshots', None, pause_snapshots],
        ['Restore Snapshot', None, [
            ['Most recent', None, lambda s: snap.restore(-1)]
        ]],
        ['Apply rules', None, [
            ['Apply all', None, lambda s: restore_snapshot(
                [], snap.get_rules())]
        ]],
        [
            "Snapshot frequency", None, submenu_from_settings(
                SETTINGS, 'snapshot_freq', 60, 'second', [5, 10, 30, 60, 300, 600, 1800, 3600])
        ], [
            "Save frequency", None,
            submenu_from_settings(
                SETTINGS, 'save_freq', 1, 'snapshot', [1, 2, 3, 4, 5])
        ],
        ['Configure Rules', None, lambda s: spawn_rule_manager(
            snap)],
        ['About', None, lambda s: about_dialog()]
    ]

    with SysTray(
        local_path('assets/icon32.ico', asset=True),
        'RestoreWindowPos',
        menu_options=menu_options,
        on_click=update_systray_options,
        on_quit=lambda *_: EXIT.set()
    ) as systray:
        monitor_thread = DeviceChangeService(snap.restore, snap.lock)
        monitor_thread.start()
        snapshot_service = SnapshotService(None)
        snapshot_service.start(args=(snap, SETTINGS))

        try:
            while not EXIT.is_set():
                time.sleep(1)
        except KeyboardInterrupt:
            pass

    monitor_thread.stop()
    snapshot_service.stop()
    exit_root()

    log.info('save snapshot before shutting down')
    snap.save()

    log.info('exit')
