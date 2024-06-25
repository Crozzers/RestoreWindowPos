'''
Module for wrangling additional functions out of Windows that the `win32api` family of packages doesn't expose.
'''
import ctypes
from ctypes.wintypes import HWND, DWORD, RECT


dwmapi = ctypes.WinDLL('dwmapi')

def DwmGetWindowAttribute(hwnd: int, attr: int):
    '''
    Exposes the `dwmapi.DwmGetWindowAttribute` function but takes care of the ctypes noise.

    See: https://learn.microsoft.com/en-us/windows/win32/api/dwmapi/nf-dwmapi-dwmgetwindowattribute
    '''
    rect = RECT()
    dwmapi.DwmGetWindowAttribute(HWND(hwnd), DWORD(attr), ctypes.byref(rect), ctypes.sizeof(rect))
    return rect


shcore = ctypes.WinDLL('shcore')


def GetDpiForMonitor(monitor: int):
    '''
    Exposes the `shcore.GetDpiForMonitor` function but takes care of the ctypes noise.

    See: https://learn.microsoft.com/en-gb/windows/win32/api/shellscalingapi/nf-shellscalingapi-getdpiformonitor
    '''
    dpi_x = ctypes.c_uint()
    dpi_y = ctypes.c_uint()
    shcore.GetDpiForMonitor(monitor, 0, ctypes.byref(dpi_x), ctypes.byref(dpi_y))  # MDT_EFFECTIVE_DPI
    return dpi_x.value, dpi_y.value

__all__ = ['DwmGetWindowAttribute', 'GetDpiForMonitor']
