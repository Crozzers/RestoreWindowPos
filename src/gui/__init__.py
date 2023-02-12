import wx

from _version import __build__, __version__
from common import local_path

from .rule_manager import spawn_rule_manager  # noqa: F401
from .systray import TaskbarIcon, submenu_from_settings  # noqa:F401
from .wx_app import WxApp  # noqa:F401


def about_dialog():
    about = wx.adv.AboutDialogInfo()
    about.SetIcon(wx.Icon(local_path('assets/icon32.ico', asset=True)))
    about.SetName('RestoreWindowPos')
    about.SetVersion(f'v{__version__}')
    about.SetDescription('\n'.join((
        f'Build: {__build__}',
        'Install DIr: %s' % local_path('.')
    )))
    with open(local_path('./LICENSE', asset=True), encoding='utf8') as f:
        about.SetLicence(f.read())
    about.SetCopyright('© 2023')
    about.SetWebSite(
        'https://github.com/Crozzers/RestoreWindowPos', 'Open GitHub Page')
    wx.adv.AboutBox(about)


def exit_root():
    wx.Exit()
