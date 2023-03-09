import wx

from common import JSONFile, reverse_dict_lookup


class SettingsPanel(wx.Panel):
    def __init__(self, parent: wx.Frame, settings: JSONFile):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.settings = settings

        def header(text: str):
            txt = wx.StaticText(snapshot_panel, label=text)
            txt.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT,
                                wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            div = wx.StaticLine(snapshot_panel, size=wx.DefaultSize)
            return (txt, div)

        # widgets
        snapshot_panel = wx.Panel(self)
        header1 = header('Snapshot settings')
        pause_snap_opt = wx.CheckBox(
            snapshot_panel, id=1, label='Pause snapshots')
        snap_freq_txt = wx.StaticText(
            snapshot_panel, label='Snapshot frequency:')
        self.__snap_freq_choices = {'5 seconds': 5, '10 seconds': 10, '30 seconds': 30, '1 minute': 60,
                                    '5 minutes': 300, '10 minutes': 600, '30 minutes': 1800, '1 hour': 3600}
        snap_freq_opt = wx.Choice(snapshot_panel, id=2, choices=list(
            self.__snap_freq_choices.keys()))
        save_freq_txt = wx.StaticText(snapshot_panel, label='Save frequency:')
        save_freq_opt = wx.SpinCtrl(snapshot_panel, id=3, min=1, max=10)
        # place
        snapshot_sizer = wx.BoxSizer(wx.VERTICAL)
        for widget in (*header1, pause_snap_opt, (snap_freq_txt, snap_freq_opt), (save_freq_txt, save_freq_opt)):
            flag = wx.ALL
            if isinstance(widget, wx.StaticLine):
                flag |= wx.EXPAND
            elif isinstance(widget, tuple):
                sz = wx.BoxSizer(wx.HORIZONTAL)
                for w in widget:
                    sz.Add(w, 0, wx.ALL, 5)
                widget = sz

            snapshot_sizer.Add(widget, 0, flag, 5)
        snapshot_panel.SetSizerAndFit(snapshot_sizer)
        snapshot_panel.Layout()

        # set widget states
        pause_snap_opt.SetValue(wx.CHK_CHECKED if settings.get(
            'pause_snapshots', False) else wx.CHK_UNCHECKED)
        snap_freq_opt.SetStringSelection(reverse_dict_lookup(
            self.__snap_freq_choices, settings.get('snapshot_freq', 60)))
        save_freq_opt.SetValue(settings.get('save_freq', 1))

        # bind events
        pause_snap_opt.Bind(wx.EVT_CHECKBOX, self.on_setting)
        snap_freq_opt.Bind(wx.EVT_CHOICE, self.on_setting)
        save_freq_opt.Bind(wx.EVT_SPINCTRL, self.on_setting)

        # place
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(snapshot_panel, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizerAndFit(sizer)

    def on_setting(self, event: wx.Event):
        widget = event.GetEventObject()
        if isinstance(widget, wx.CheckBox):
            if event.Id == 1:
                self.settings.set('pause_snapshots', widget.GetValue())
        elif isinstance(widget, wx.Choice):
            if event.Id == 2:
                self.settings.set(
                    'snapshot_freq', self.__snap_freq_choices[widget.GetStringSelection()])
        elif isinstance(widget, wx.SpinCtrl):
            if event.Id == 3:
                self.settings.set('save_freq', widget.GetValue())
