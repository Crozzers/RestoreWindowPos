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
import win32gui_struct
from infi.systray import SysTrayIcon

from common import JSONFile, local_path
from snapshot import Snapshot

GUID_DEVINTERFACE_DISPLAY_DEVICE = "{E6F07B5F-EE97-4a90-B076-33F57BF4EAA7}"


class Display:
    THREAD_ALIVE = False

    def on_device_change(hwnd, msg, wp, lp):
        if msg == win32con.WM_POWERBROADCAST:
            if wp == win32con.PBT_APMRESUMEAUTOMATIC:
                Snapshot.RESTORE_IN_PROGRESS = True
                time.sleep(1)
        Snapshot.INSTANCE.restore()
        return True

    @classmethod
    def monitor_device_changes(cls):
        cls.THREAD_ALIVE = True

        wc = win32gui.WNDCLASS()
        wc.lpszClassName = 'test_devicenotify'
        wc.style = win32con.CS_GLOBALCLASS | win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hbrBackground = win32con.COLOR_WINDOW+1
        wc.lpfnWndProc = {
            win32con.WM_DISPLAYCHANGE: cls.on_device_change,
            win32con.WM_WINDOWPOSCHANGING: cls.on_device_change,
            win32con.WM_POWERBROADCAST: cls.on_device_change
        }
        win32gui.RegisterClass(wc)
        hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            'RestoreWindowPos',
            # no need for it to be visible.
            win32con.WS_CAPTION,
            100, 100, 900, 900, 0, 0, 0, None
        )

        filter = win32gui_struct.PackDEV_BROADCAST_DEVICEINTERFACE(
            GUID_DEVINTERFACE_DISPLAY_DEVICE
        )
        win32gui.RegisterDeviceNotification(
            hwnd, filter, win32con.DEVICE_NOTIFY_WINDOW_HANDLE
        )

        while cls.THREAD_ALIVE:
            win32gui.PumpWaitingMessages()
            time.sleep(0.01)
        log.debug('monitor thread exit')

        win32gui.DestroyWindow(hwnd)
        win32gui.UnregisterClass(wc.lpszClassName, None)


if __name__ == '__main__':
    logging.basicConfig(filename=local_path('log.txt'),
                        filemode='w',
                        format='%(asctime)s:%(levelname)s:%(message)s',
                        level=logging.DEBUG)
    log = logging.getLogger(__name__)
    log.info('start')

    SETTINGS = JSONFile('settings.json')
    SETTINGS.load()
    EXIT = False

    def notify(*_):
        global EXIT
        EXIT = True

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
        on_quit=notify
    ) as systray:
        monitor_thread = threading.Thread(
            target=Display.monitor_device_changes, daemon=True)
        monitor_thread.start()
        snap = Snapshot()

        try:
            count = 0
            while not EXIT:
                if not snap.RESTORE_IN_PROGRESS:
                    snap.update()
                    count += 1

                if count >= SETTINGS.get('save_freq', 1):
                    snap.save()
                    count = 0

                for i in range(SETTINGS.get('snapshot_freq', 30)):
                    time.sleep(1)
                    if EXIT:
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
