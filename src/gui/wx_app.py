import logging
from typing import Literal, Optional
import psutil

import wx
import wx.adv
from common import single_call

from gui.layout_manager import LayoutPage
from gui.on_spawn_manager import OnSpawnPage
from gui.settings import SettingsPanel
from gui.widgets import Frame
from snapshot import SnapshotFile


class WxApp(wx.App):
    __instance: 'WxApp'

    @single_call  # mark as `single_call` so we don't re-call `OnInit` during shutdown
    def __init__(self):
        self._log = logging.getLogger(__name__).getChild(self.__class__.__name__ + '.' + str(id(self)))
        super().__init__()

    def __new__(cls, *args, **kwargs):
        if not isinstance(getattr(cls, '__instance', None), cls):
            cls.__instance = wx.App.__new__(cls, *args, **kwargs)
        return cls.__instance

    def OnInit(self):
        if isinstance(getattr(self, '_top_frame', None), wx.Frame):
            return True
        self._top_frame = wx.Frame(None, -1)
        self.SetTopWindow(self._top_frame)
        self.enable_sigterm()
        return True

    def enable_sigterm(self, parent: Optional[psutil.Process] = None):
        """
        Allow the application to respond to external signals such as SIGTERM or SIGINT.
        This is done by creating a wx timer that regularly returns control of the program
        to the Python runtime, allowing it to process the signals.

        Args:
            parent: optional parent process. If provided, the lifetime of the application will
                be tied to this process. When the parent exits, this app will follow suit
        """
        self._log.debug(f'enable sigterm, {parent=}')

        def check_parent_alive():
            if not parent or parent.is_running():
                return
            self._log.info('parent process no longer running. exiting mainloop...')
            self.ExitMainLoop()

        # enable sigterm by regularly returning control back to python
        self.timer = wx.Timer(self._top_frame)
        self._top_frame.Bind(wx.EVT_TIMER, lambda *_: check_parent_alive(), self.timer)
        self.timer.Start(1000)


def spawn_gui(snapshot: SnapshotFile, start_page: Literal['rules', 'settings'] = 'rules'):
    top = WxApp()._top_frame

    for child in top.GetChildren():
        if isinstance(child, Frame):
            if child.GetName() == 'RWPGUI':
                f = child
                nb = f.nb
                break
    else:
        f = Frame(parent=top, size=wx.Size(600, 500), name='RWPGUI')
        nb = wx.Notebook(f, id=wx.ID_ANY, style=wx.BK_DEFAULT)
        f.nb = nb
        layout_panel = LayoutPage(nb, snapshot)
        on_spawn_panel = OnSpawnPage(nb)
        settings_panel = SettingsPanel(nb)
        nb.AddPage(layout_panel, 'Layouts and Rules')
        nb.AddPage(on_spawn_panel, 'Window Spawn Behaviour')
        nb.AddPage(settings_panel, 'Settings')
        nb.SetPadding(wx.Size(5, 2))

    nb.ChangeSelection(2 if start_page == 'settings' else 0)
    f.SetIdealSize()
    f.Show()
    f.Raise()
    f.Iconize(False)
