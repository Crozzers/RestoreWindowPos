from common import JSONFile, local_path, size_from_rect
import win32api
import re
import win32gui
import pywintypes


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
                pass
            else:
                result.append({
                    'uid': dev_uid,
                    'name': dev_name,
                    'resolution': size_from_rect(dev_rect),
                    'rect': list(dev_rect)
                })
    return result


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

                rect = tuple(item['rect'])
                current = win32gui.GetWindowRect(hwnd)
                if current == rect:
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
                    # log.debug(
                    #     f'restore window "{win32gui.GetWindowText(hwnd)}" {current} -> {rect}')
                except pywintypes.error as e:
                    # log.error('err moving window %s : %s' %
                    #           (win32gui.GetWindowText(hwnd), e))
                    pass

        win32gui.EnumWindows(callback, None)


class Snapshot(JSONFile):
    RESTORE_IN_PROGRESS = False
    # kind of a hack until I get a proper messaging system between threads
    INSTANCE = None

    def __init__(self):
        super().__init__(local_path('history.json'))
        super().load(default=[])
        # keep a ref so Display.on_device_change can invoke a restore
        self.__class__.INSTANCE = self

    def restore(self):
        self.__class__.RESTORE_IN_PROGRESS = True
        displays = enum_display_devices()

        for ss in self.data:
            if ss['displays'] == displays:
                Window.restore_snapshot(ss['windows'])

        self.__class__.RESTORE_IN_PROGRESS = False

    def capture(self):
        # log.debug('capture snapshot')  # TODO: to be re-enabled
        return {
            'displays': enum_display_devices(),
            'windows': Window.capture_snapshot()
        }

    def update(self, snap=None):
        if snap is None:
            snap = self.capture()

        for item in self.data:
            if item['displays'] == snap['displays']:
                item['windows'] = snap['windows']
                break
        else:
            self.data.append(snap)
