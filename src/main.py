# Sources:
# https://stackoverflow.com/questions/69712306/list-all-windows-with-win32gui
# http://timgolden.me.uk/pywin32-docs/win32gui__GetWindowRect_meth.html
# http://timgolden.me.uk/pywin32-docs/win32gui__MoveWindow_meth.html
# Todo:
# https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settingchange
# https://stackoverflow.com/questions/5981520/detect-external-display-being-connected-or-removed-under-windows-7
import json
import os
import re
import sys
import threading
import time

import pywintypes
import win32api
import win32con
import win32gui
import win32gui_struct
from infi.systray import SysTrayIcon

GUID_DEVINTERFACE_DISPLAY_DEVICE = "{E6F07B5F-EE97-4a90-B076-33F57BF4EAA7}"


def local_path(path, asset=False):
    if getattr(sys, 'frozen', False):
        if asset:
            base = sys._MEIPASS
        else:
            base = os.path.dirname(sys.executable)
    else:
        base = os.path.abspath(os.path.join(
            os.path.dirname(__file__), os.pardir))

    return os.path.abspath(os.path.join(base, path))


def size_from_rect(rect) -> tuple[int]:
    return [
        rect[2] - rect[0],
        rect[3] - rect[1]
    ]


class Window:
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

    def restore_snapshot(snap: dict):
        def callback(hwnd, extra):
            for item in snap:
                if hwnd != item['id']:
                    continue

                rect = item['rect']
                if win32gui.GetWindowRect(hwnd) == rect:
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
                except pywintypes.error as e:
                    print('err moving window',
                          win32gui.GetWindowText(hwnd), ':', e)

        win32gui.EnumWindows(callback, None)


class Display:
    THREAD_ALIVE = False

    def enum_display_devices():
        result = []
        for monitor in win32api.EnumDisplayMonitors():
            info = win32api.GetMonitorInfo(monitor[0])
            dev_rect = info['Monitor']
            for adaptor_index in range(5):
                try:
                    device = win32api.EnumDisplayDevices(
                        info['Device'], adaptor_index, 1)
                    dev_uid = re.findall(r'UID[0-9]+', device.DeviceID)[0]
                    dev_name = device.DeviceID.split('#')[1]
                except Exception:
                    # print('err enum_display_devices:', e)
                    pass
                else:
                    result.append({
                        'uid': dev_uid,
                        'name': dev_name,
                        'resolution': size_from_rect(dev_rect),
                        'rect': list(dev_rect)
                    })
        return result

    def on_device_change(hwnd, msg, wp, lp):
        if msg == win32con.WM_DISPLAYCHANGE:
            Snapshot.restore()
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
            win32con.WM_WINDOWPOSCHANGING: cls.on_device_change
        }
        win32gui.RegisterClass(wc)
        hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            'WinSnapper',
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
        print('MT exit')

        win32gui.DestroyWindow(hwnd)
        win32gui.UnregisterClass(wc.lpszClassName, None)


class Snapshot:
    RESTORE_IN_PROGRESS = False

    @classmethod
    def restore(cls):
        cls.RESTORE_IN_PROGRESS = True
        snap = cls.load()
        displays = Display.enum_display_devices()

        for ss in snap:
            if ss['displays'] == displays:
                Window.restore_snapshot(ss['windows'])

        cls.RESTORE_IN_PROGRESS = False

    def load():
        try:
            with open(local_path('history.json'), 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.decoder.JSONDecodeError):
            return []

    def capture():
        return {
            'displays': Display.enum_display_devices(),
            'windows': Window.capture_snapshot()
        }

    def save(snap):
        with open(local_path('history.json'), 'w') as f:
            json.dump(snap, f)

    def update(history, snapshot):
        for item in history:
            if item['displays'] == snapshot['displays']:
                item['windows'] = snapshot['windows']
                break
        else:
            history.append(snapshot)


if __name__ == '__main__':
    EXIT = False

    def notify(*_):
        global EXIT
        EXIT = True

    # menu_options = (("Test", None, lambda *_: print('test')),)
    menu_options = ()

    with SysTrayIcon(local_path('assets/icon32.ico', asset=True), 'RestoreWindowPos', menu_options, on_quit=notify) as systray:
        monitor_thread = threading.Thread(
            target=Display.monitor_device_changes, daemon=True)
        monitor_thread.start()
        snap = Snapshot.load()

        try:
            while not EXIT:
                if not Snapshot.RESTORE_IN_PROGRESS:
                    print('Save snapshot')
                    Snapshot.update(snap, Snapshot.capture())
                    Snapshot.save(snap)

                time.sleep(5)
        except KeyboardInterrupt:
            pass

    Display.THREAD_ALIVE = False
    print('wait for monitor thread to exit')
    while monitor_thread.is_alive():
        time.sleep(0.5)

    print('exit')
