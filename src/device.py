import time
from dataclasses import dataclass
from typing import Callable

import win32con
import win32gui
import win32gui_struct

from services import Service, ServiceCallback

GUID_DEVINTERFACE_DISPLAY_DEVICE = "{E6F07B5F-EE97-4a90-B076-33F57BF4EAA7}"


@dataclass(slots=True)
class DeviceChangeCallback(ServiceCallback):
    capture: Callable = None


class DeviceChangeService(Service):
    def pre_callback(self, hwnd, msg, wp, lp):
        super().pre_callback()
        if msg == win32con.WM_CLOSE:
            self.log.info('invoke shutdown due to WM_CLOSE signal')
            self.shutdown()
            return False

        if msg == win32con.WM_POWERBROADCAST:
            if wp in (win32con.PBT_APMSTANDBY, win32con.PBT_APMSUSPEND):
                self.log.info(
                    'invoke capture due to PBT_APM[STANDBY|SUSPEND] signal')
                return self._run_callback('capture', threaded=True)

            if wp not in (win32con.PBT_APMRESUMEAUTOMATIC,
                          win32con.PBT_APMRESUMECRITICAL,
                          win32con.PBT_APMRESUMESTANDBY,
                          win32con.PBT_APMRESUMESUSPEND
                          ):
                self.log.info(
                    'skip WM_POWERBROADCAST event due to unknown signal')
                return False

            self.log.info(
                'trigger PBT_APMRESUME[AUTOMATIC|CRITICAL|STANDBY|SUSPEND] signal')
            time.sleep(1)
        elif msg == win32con.WM_DISPLAYCHANGE:
            self.log.debug('trigger WM_DISPLAYCHANGE')
        elif msg == win32con.WM_WINDOWPOSCHANGING:
            self.log.debug('trigger WM_WINDOWPOSCHANGING')
        else:
            self.log.debug(f'trigger {msg=:x} {wp=:x} {lp=:x}')

        return True

    def _runner(self):
        wc = win32gui.WNDCLASS()
        wc.lpszClassName = 'RestoreWindowPos'
        wc.style = win32con.CS_GLOBALCLASS | win32con.CS_VREDRAW | win32con.CS_HREDRAW
        wc.hbrBackground = win32con.COLOR_WINDOW + 1

        wc.lpfnWndProc = {
            win32con.WM_DISPLAYCHANGE: self.callback,
            win32con.WM_WINDOWPOSCHANGING: self.callback,
            win32con.WM_POWERBROADCAST: self.callback,
            win32con.WM_CLOSE: self.callback
        }
        win32gui.RegisterClass(wc)
        hwnd = win32gui.CreateWindow(
            wc.lpszClassName,
            'Device Change Monitoring Window - RestoreWindowPos',
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

        while not self._kill_signal.wait(timeout=0.01):
            win32gui.PumpWaitingMessages()

        win32gui.DestroyWindow(hwnd)
        win32gui.UnregisterClass(wc.lpszClassName, None)
