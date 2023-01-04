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

from infi.systray import SysTrayIcon

from common import JSONFile, local_path
from device import Display
from snapshot import Snapshot


if __name__ == '__main__':
    logging.basicConfig(filename=local_path('log.txt'),
                        filemode='w',
                        format='%(asctime)s:%(levelname)s:%(name)s:%(message)s',
                        level=logging.DEBUG)
    log = logging.getLogger(__name__)
    log.info('start')

    SETTINGS = JSONFile('settings.json')
    SETTINGS.load()
    EXIT = threading.Event()

    menu_options = (
        (
            "Snapshot frequency", None, (
                ('2 seconds', None, lambda *_: SETTINGS.set('snapshot_freq', 2)),
                ('5 seconds', None, lambda *_: SETTINGS.set('snapshot_freq', 5)),
                ('30 seconds', None, lambda *_: SETTINGS.set('snapshot_freq', 30)),
                ('1 minute', None, lambda *_: SETTINGS.set('snapshot_freq', 60)),
                ('5 minutes', None, lambda *_: SETTINGS.set('snapshot_freq', 300)),
            )
        ), (
            "Save frequency", None, (
                ('Every snapshot', None, lambda *_: SETTINGS.set('save_freq', 1)),
                ('Every 2 snapshots', None, lambda *_: SETTINGS.set('save_freq', 2)),
                ('Every 3 snapshots', None, lambda *_: SETTINGS.set('save_freq', 3)),
                ('Every 4 snapshots', None, lambda *_: SETTINGS.set('save_freq', 4)),
                ('Every 5 snapshots', None, lambda *_: SETTINGS.set('save_freq', 5)),
            )
        )
    )

    with SysTrayIcon(
        local_path('assets/icon32.ico', asset=True),
        'RestoreWindowPos',
        menu_options,
        on_quit=lambda *_: EXIT.set()
    ) as systray:
        snap = Snapshot()
        monitor_thread = threading.Thread(
            target=Display.monitor_device_changes, args=(snap.restore, snap.lock,), daemon=True)
        monitor_thread.start()

        try:
            count = 0
            while not EXIT.is_set():
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
