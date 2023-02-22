import wx
import wx.adv


class WxApp(wx.App):
    __instance: 'WxApp' = None

    def __call__(cls, *args, **kwargs):
        if not isinstance(cls.__instance, cls):
            cls.__instance = cls(*args, **kwargs)
        return cls.__instance

    def OnInit(self):
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
