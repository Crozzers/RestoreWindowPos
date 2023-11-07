import logging
import os

import wx

from common import load_json, local_path, reverse_dict_lookup
from gui.widgets import EVT_TIME_SPAN_SELECT, TimeSpanSelector, simple_box_sizer


class SettingsPanel(wx.Panel):
    def __init__(self, parent: wx.Frame):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.settings = load_json('settings')

        def header(text: str):
            txt = wx.StaticText(panel, label=text)
            txt.SetFont(wx.Font(14, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            div = wx.StaticLine(panel, size=wx.DefaultSize)
            return (txt, div)

        # widgets
        panel = wx.Panel(self)
        header1 = header('Snapshot settings')
        pause_snap_opt = wx.CheckBox(panel, id=1, label='Pause snapshots')
        snap_freq_txt = wx.StaticText(panel, label='Snapshot frequency')
        self.__snap_freq_choices = {
            '5 seconds': 5,
            '10 seconds': 10,
            '30 seconds': 30,
            '1 minute': 60,
            '5 minutes': 300,
            '10 minutes': 600,
            '30 minutes': 1800,
            '1 hour': 3600,
        }
        snap_freq_opt = wx.Choice(panel, id=2, choices=list(self.__snap_freq_choices.keys()))
        save_freq_txt = wx.StaticText(panel, label='Save frequency')
        save_freq_opt = wx.SpinCtrl(panel, id=3, min=1, max=10)

        prune_history_opt = wx.CheckBox(panel, id=4, label='Prune window history')
        prune_history_opt.SetToolTip(
            'Remove windows from the history if they no longer exist.'
            '\nIt\'s recommended disable this when "Enable reacting to new windows being created" is enabled.'
        )

        history_ttl_txt = wx.StaticText(panel, label='Window history retention')
        history_ttl_txt.SetToolTip('How long window positioning information should be remembered by the program')
        history_ttl_opt = TimeSpanSelector(panel, id=5)

        history_count_txt = wx.StaticText(panel, label='Max number of snapshots to keep')
        history_count_opt = wx.SpinCtrl(panel, id=6, min=1, max=50)

        header2 = header('Misc')

        log_level_txt = wx.StaticText(panel, label='Logging level')
        log_level_opt = wx.Choice(panel, id=7, choices=['Debug', 'Info', 'Warning', 'Error', 'Critical'])

        open_install_btn = wx.Button(panel, label='Open install directory')
        open_github_btn = wx.Button(panel, label='Open GitHub page')
        # place
        simple_box_sizer(
            panel,
            (
                *header1,
                pause_snap_opt,
                (snap_freq_txt, snap_freq_opt),
                (save_freq_txt, save_freq_opt),
                prune_history_opt,
                (history_ttl_txt, history_ttl_opt),
                (history_count_txt, history_count_opt),
                *header2,
                (log_level_txt, log_level_opt),
                open_install_btn,
                open_github_btn,
            ),
        )

        # set widget states
        pause_snap_opt.SetValue(wx.CHK_CHECKED if self.settings.get('pause_snapshots', False) else wx.CHK_UNCHECKED)
        snap_freq_opt.SetStringSelection(
            reverse_dict_lookup(self.__snap_freq_choices, self.settings.get('snapshot_freq', 60))
        )
        save_freq_opt.SetValue(self.settings.get('save_freq', 1))
        prune_history_opt.SetValue(self.settings.get('prune_history', True))
        history_ttl_opt.SetTime(self.settings.get('window_history_ttl', 0))
        history_count_opt.SetValue(self.settings.get('max_snapshots', 10))
        log_level_opt.SetStringSelection(self.settings.get('log_level', 'Info'))

        # bind events
        pause_snap_opt.Bind(wx.EVT_CHECKBOX, self.on_setting)
        snap_freq_opt.Bind(wx.EVT_CHOICE, self.on_setting)
        save_freq_opt.Bind(wx.EVT_SPINCTRL, self.on_setting)
        prune_history_opt.Bind(wx.EVT_CHECKBOX, self.on_setting)
        history_ttl_opt.Bind(EVT_TIME_SPAN_SELECT, self.on_setting)
        history_count_opt.Bind(wx.EVT_SPINCTRL, self.on_setting)
        log_level_opt.Bind(wx.EVT_CHOICE, self.on_setting)

        open_install_btn.Bind(wx.EVT_BUTTON, lambda *_: os.startfile(local_path('.')))
        open_github_btn.Bind(wx.EVT_BUTTON, lambda *_: os.startfile('https://github.com/Crozzers/RestoreWindowPos'))

        # place
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(panel, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizerAndFit(sizer)

    def on_setting(self, event: wx.Event):
        widget = event.GetEventObject()
        if isinstance(widget, wx.CheckBox):
            if event.Id == 1:
                self.settings.set('pause_snapshots', widget.GetValue())
            elif event.Id == 4:
                self.settings.set('prune_history', widget.GetValue())
        elif isinstance(widget, wx.Choice):
            if event.Id == 2:
                self.settings.set('snapshot_freq', self.__snap_freq_choices[widget.GetStringSelection()])
            elif event.Id == 7:
                level: str = widget.GetStringSelection().upper()
                self.settings.set('log_level', level)
                logging.getLogger().setLevel(logging.getLevelName(level))
        elif isinstance(widget, wx.SpinCtrl):
            if event.Id == 3:
                self.settings.set('save_freq', widget.GetValue())
            elif event.Id == 6:
                self.settings.set('max_snapshots', widget.GetValue())
        elif isinstance(widget, TimeSpanSelector):
            if event.Id == 5:
                self.settings.set('window_history_ttl', widget.GetTime())
