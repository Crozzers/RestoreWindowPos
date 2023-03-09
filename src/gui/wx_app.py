from typing import Literal

import wx
import wx.adv

from common import JSONFile
from gui.rule_manager import RuleManager
from gui.settings import SettingsPanel
from gui.widgets import Frame
from snapshot import SnapshotFile


class WxApp(wx.App):
    __instance: 'WxApp' = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls.__instance, cls):
            cls.__instance = wx.App.__new__(cls, *args, **kwargs)
        return cls.__instance

    def OnInit(self):
        if isinstance(getattr(self, '_top_frame', None), wx.Frame):
            return True
        self._top_frame = wx.Frame(None, -1)
        self.SetTopWindow(self._top_frame)
        self.enable_sigterm()
        return True

    def enable_sigterm(self):
        self.timer = wx.Timer(self._top_frame)
        self._top_frame.Bind(wx.EVT_TIMER, self.OnTimer, self.timer)
        self.timer.Start(1000)

    def OnTimer(self, *_):
        return

    def schedule_exit(self):
        self._top_frame.DestroyChildren()
        self._top_frame.Destroy()
        wx.CallAfter(self.Destroy)


def spawn_gui(snapshot: SnapshotFile, settings: JSONFile, start_page: Literal['rules', 'settings'] = 'rules'):
    f = Frame(title='Manage Rules', size=wx.Size(600, 500))
    nb = wx.Notebook(f, id=wx.ID_ANY, style=wx.BK_DEFAULT)
    rule_panel = RuleManager(nb, snapshot)
    settings_panel = SettingsPanel(nb, settings)
    nb.AddPage(rule_panel, 'Rules')
    nb.AddPage(settings_panel, 'Settings')
    nb.SetPadding(wx.Size(5, 2))
    if start_page == 'settings':
        nb.ChangeSelection(1)
    f.SetIdealSize()
    f.Show()
