# Sources:
# https://stackoverflow.com/questions/69712306/list-all-windows-with-win32gui
# http://timgolden.me.uk/pywin32-docs/win32gui__GetWindowRect_meth.html
# http://timgolden.me.uk/pywin32-docs/win32gui__MoveWindow_meth.html
# Todo:
# https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settingchange
# https://stackoverflow.com/questions/5981520/detect-external-display-being-connected-or-removed-under-windows-7
import logging
import time

import win32con
import win32gui

from common import JSONFile, local_path
from device import DeviceChangeService
from gui import WxApp, about_dialog, spawn_rule_manager
from gui import TaskbarIcon, submenu_from_settings
from snapshot import SnapshotFile, SnapshotService
from window import restore_snapshot


def pause_snapshots():
    if SETTINGS.get('pause_snapshots', False):
        SETTINGS.set('pause_snapshots', False)
        verb = 'Pause'
    else:
        SETTINGS.set('pause_snapshots', True)
        verb = 'Resume'

    global menu_options
    menu_options[1][0] = f'{verb} snapshots'


def update_systray_options():
    history_menu = []
    for config in snap.get_history():
        timestamp = config.time
        label = time.strftime('%b %d %H:%M:%S', time.localtime(timestamp))
        history_menu.append(
            [label, lambda *_, t=timestamp: snap.restore(t)])

    if history_menu:
        history_menu.insert(0, [TaskbarIcon.SEPERATOR, None])
        history_menu.insert(
            0, ['Clear history', lambda *_: clear_restore_options()])

    global menu_options
    menu_options[2][1][:-2] = history_menu

    rule_menu = []
    for rule in snap.get_rules():
        rule_menu.append([rule.rule_name or 'Unnamed Rule',
                         lambda *_, r=rule: restore_snapshot([], [r])])
    menu_options[7][1][:-2] = rule_menu


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

    snap = SnapshotFile()
    app = WxApp()

    menu_options = [
        ['Capture Now', snap.update],
        ['Pause Snapshots', pause_snapshots],
        ['Restore Snapshot', [
            [TaskbarIcon.SEPERATOR, None],
            ['Most recent', lambda *_: snap.restore(-1)]
        ]],
        [TaskbarIcon.SEPERATOR, None],
        [
            "Snapshot frequency", submenu_from_settings(
                SETTINGS, 'snapshot_freq', 60, 'second', [5, 10, 30, 60, 300, 600, 1800, 3600])
        ], [
            "Save frequency", submenu_from_settings(
                SETTINGS, 'save_freq', 1, 'snapshot', [1, 2, 3, 4, 5])
        ],
        [TaskbarIcon.SEPERATOR, None],
        ['Apply rules', [
            [TaskbarIcon.SEPERATOR, None],
            ['Apply all', lambda *_: restore_snapshot([], snap.get_rules())]
        ]],
        ['Configure Rules', lambda *_: spawn_rule_manager(snap)],
        [TaskbarIcon.SEPERATOR, None],
        ['About', lambda *_: about_dialog()]
    ]

    def shutdown():
        monitor_thread.stop()
        snapshot_service.stop()
        log.info('save snapshot before shutting down')
        snap.save()
        log.info('exit')

    with TaskbarIcon(menu_options, on_click=update_systray_options, on_exit=shutdown):
        monitor_thread = DeviceChangeService(snap.restore, snap.lock)
        monitor_thread.start()
        snapshot_service = SnapshotService(None)
        snapshot_service.start(args=(snap, SETTINGS))

        try:
            app.MainLoop()
        except KeyboardInterrupt:
            pass
