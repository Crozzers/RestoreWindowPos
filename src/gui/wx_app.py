import wx
import wx.adv


class WxApp(wx.App):
    __instance = None

    def __call__(cls, *args, **kwargs):
        if not isinstance(cls.__instance, cls):
            cls.__instance = cls(*args, **kwargs)
        return cls.__instance

    def OnInit(self):
        self._top_frame = wx.Frame(None, -1)
        self.SetTopWindow(self._top_frame)
        return True

    def OnExit(self):
        return super().OnExit()

    def schedule_exit(self):
        self._top_frame.DestroyChildren()
        self._top_frame.Destroy()
        wx.CallAfter(self.Destroy)
