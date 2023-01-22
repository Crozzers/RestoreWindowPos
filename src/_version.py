import sys

import win32api

__version__ = '0.6.2'
__build__ = None

if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
    __build__ = win32api.LOWORD(win32api.GetFileVersionInfo(sys.executable, '\\')['FileVersionLS'])
