import wx

from _version import __build__, __version__
from common import local_path

from .systray import TaskbarIcon, radio_menu  # noqa:F401
from .wx_app import WxApp  # noqa:F401


def about_dialog():
    about = wx.adv.AboutDialogInfo()
    about.SetIcon(wx.Icon(local_path('assets/icon32.ico', asset=True)))
    about.SetName('RestoreWindowPos')
    about.SetVersion(f'v{__version__}')
    about.SetDescription('\n'.join((f'Build: {__build__}', 'Install Dir: %s' % local_path('.'))))
    with open(local_path('./LICENSE', asset=True), encoding='utf8') as f:
        about.SetLicence(f.read())
    about.SetCopyright('© 2024')
    about.SetWebSite('https://github.com/Crozzers/RestoreWindowPos', 'Open GitHub Page')
    wx.adv.AboutBox(about)
