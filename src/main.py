# Sources:
# https://stackoverflow.com/questions/69712306/list-all-windows-with-win32gui
# http://timgolden.me.uk/pywin32-docs/win32gui__GetWindowRect_meth.html
# http://timgolden.me.uk/pywin32-docs/win32gui__MoveWindow_meth.html
# Todo:
# https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settingchange
# https://stackoverflow.com/questions/5981520/detect-external-display-being-connected-or-removed-under-windows-7
import ctypes
import logging
import threading
import time

import win32con

from _version import __version__, __build__
from common import JSONFile, local_path
from device import Display
from snapshot import Snapshot
from systray import SysTray, submenu_from_settings


def about(_):
    caption = '\n'.join((
        f"Version: v{__version__}",
        f"Build: {__build__}",
        "URL: https://github.com/Crozzers/RestoreWindowPos",
        "\nCreated by: Crozzers (https://github.com/Crozzers)",
        "License: MIT License",
        "\nInstall Dir: %s" % local_path('.')
    ))
    ctypes.windll.user32.MessageBoxW(
        0, caption, 'RestoreWindowPos', win32con.MB_ICONINFORMATION)


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

    snap = Snapshot()

    menu_options = [
        ['Capture Now', None, lambda s: snap.capture()],
        ['Pause Snapshots', None, pause_snapshots],
        [
            "Snapshot frequency", None, submenu_from_settings(
                SETTINGS, 'snapshot_freq', 30, 'second', [2, 5, 30, 60, 300])
        ], [
            "Save frequency", None,
            submenu_from_settings(
                SETTINGS, 'save_freq', 1, 'snapshot', [1, 2, 3, 4, 5])
        ],
        ['About', None, about]
    ]

    with SysTray(
        local_path('assets/icon32.ico', asset=True),
        'RestoreWindowPos',
        menu_options=menu_options,
        on_quit=lambda *_: EXIT.set()
    ) as systray:
        monitor_thread = threading.Thread(
            target=Display.monitor_device_changes, args=(snap.restore, snap.lock,), daemon=True)
        monitor_thread.start()

        try:
            count = 0
            while not EXIT.is_set():
                if not SETTINGS.get('pause_snapshots', False):
                    snap.update()
                    count += 1

                if count >= SETTINGS.get('save_freq', 1):
                    snap.save()
                    count = 0

                for i in range(SETTINGS.get('snapshot_freq', 30)):
                    time.sleep(1)
                    if EXIT.is_set():
                        break
                else:
                    continue
                break
        except KeyboardInterrupt:
            pass

    Display.THREAD_ALIVE = False
    log.info('wait for monitor thread to exit')
    while monitor_thread.is_alive():
        time.sleep(0.5)

    log.info('save snapshot before shutting down')
    snap.save()

    log.info('exit')
