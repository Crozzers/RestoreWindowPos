import logging
import time

import win32con
import win32gui
import win32gui_struct

GUID_DEVINTERFACE_DISPLAY_DEVICE = "{E6F07B5F-EE97-4a90-B076-33F57BF4EAA7}"


class Display:
    _log = logging.getLogger(__name__).getChild('Display')
    THREAD_ALIVE = False

    @staticmethod
    def wndproc(hwnd, msg, wp, lp):
        if msg == win32con.WM_POWERBROADCAST:
            if wp == win32con.PBT_APMRESUMEAUTOMATIC:
                time.sleep(1)

        return True

    @classmethod
    def on_device_change(cls, callback, lock):
        def wrapped(*args):
            with lock:
                ret = cls.wndproc(*args)
                callback()
                return ret

        return wrapped

    @classmethod
    def monitor_device_changes(cls, callback, lock):
        cls.THREAD_ALIVE = True

        wc = win32gui.WNDCLASS()
        wc.lpszClassName = 'test_devicenotify'
        wc.style = win32con.CS_GLOBALCLASS | win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hbrBackground = win32con.COLOR_WINDOW + 1

        cb = cls.on_device_change(callback, lock)
        wc.lpfnWndProc = {
            win32con.WM_DISPLAYCHANGE: cb,
            win32con.WM_WINDOWPOSCHANGING: cb,
            win32con.WM_POWERBROADCAST: cb
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
        cls._log.debug('monitor thread exit')

        win32gui.DestroyWindow(hwnd)
        win32gui.UnregisterClass(wc.lpszClassName, None)