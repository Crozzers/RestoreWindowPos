# Sources:
# https://stackoverflow.com/questions/69712306/list-all-windows-with-win32gui
# http://timgolden.me.uk/pywin32-docs/win32gui__GetWindowRect_meth.html
# http://timgolden.me.uk/pywin32-docs/win32gui__MoveWindow_meth.html
# Todo:
# https://learn.microsoft.com/en-us/windows/win32/winmsg/wm-settingchange
# https://stackoverflow.com/questions/5981520/detect-external-display-being-connected-or-removed-under-windows-7
import win32api
import re
import json
import threading
import time
import pywintypes

import win32con
import win32gui
import win32gui_struct

GUID_DEVINTERFACE_DISPLAY_DEVICE = "{E6F07B5F-EE97-4a90-B076-33F57BF4EAA7}"
RESTORE_IN_PROGRESS = False


def size_from_rect(rect) -> tuple[int]:
    return [
        rect[2] - rect[0],
        rect[3] - rect[1]
    ]


def capture_window_snapshot():
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


def restore_window_snapshot(snap: dict):
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
                print('err moving window', win32gui.GetWindowText(hwnd), ':', e)

    win32gui.EnumWindows(callback, None)


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


def OnDeviceChange(hwnd, msg, wp, lp):
    # print(hwnd, msg, wp, lp)
    # print("Device change notification:", wp)
    if msg == win32con.WM_DISPLAYCHANGE:
        global RESTORE_IN_PROGRESS
        RESTORE_IN_PROGRESS = True
        restore_snapshot()
        RESTORE_IN_PROGRESS = False
    return True


def TestDeviceNotifications(flags):
    wc = win32gui.WNDCLASS()
    wc.lpszClassName = 'test_devicenotify'
    wc.style = win32con.CS_GLOBALCLASS | win32con.CS_VREDRAW | win32con.CS_HREDRAW
    wc.hbrBackground = win32con.COLOR_WINDOW+1
    wc.lpfnWndProc = {
        win32con.WM_DISPLAYCHANGE: OnDeviceChange,
        win32con.WM_WINDOWPOSCHANGING: OnDeviceChange
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

    while flags['alive']:
        win32gui.PumpWaitingMessages()
        time.sleep(0.01)
    print('MT exit')

    win32gui.DestroyWindow(hwnd)
    win32gui.UnregisterClass(wc.lpszClassName, None)


def restore_snapshot():
    snap = load_snapshot()
    displays = enum_display_devices()

    for ss in snap:
        if ss['displays'] == displays:
            restore_window_snapshot(ss['windows'])


def load_snapshot():
    try:
        with open('history.json', 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        return []


def capture_snapshot():
    return {
        'displays': enum_display_devices(),
        'windows': capture_window_snapshot()
    }


def save_snapshot(snap):
    with open('history.json', 'w') as f:
        json.dump(snap, f)


def update_snapshot(history, snapshot):
    for item in history:
        if item['displays'] == snapshot['displays']:
            item['windows'] = snapshot['windows']
            break
    else:
        history.append(snapshot)


if __name__ == '__main__':
    flags = {'alive': True}
    monitor_thread = threading.Thread(
        target=TestDeviceNotifications, args=(flags,), daemon=True)
    monitor_thread.start()
    snap = load_snapshot()
    try:
        while True:
            if RESTORE_IN_PROGRESS:
                print('Save snapshot')
                update_snapshot(snap, capture_snapshot())
                save_snapshot(snap)

            time.sleep(5)
    except KeyboardInterrupt:
        flags['alive'] = False

    print('wait for monitor thread to exit')
    while monitor_thread.is_alive():
        time.sleep(1)

    print('exit')
