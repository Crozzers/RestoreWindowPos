from typing import TypedDict
import wx
from common import load_json


class OnSpawnSettings(TypedDict):
    enabled: bool
    apply_lkp: bool
    apply_rules: bool


class OnSpawnPage(wx.Panel):
    def __init__(self, parent: wx.Frame):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.settings_file = load_json('settings')
        self.settings = OnSpawnSettings(enabled=False, apply_lkp=True, apply_rules=True)
        self.settings.update(self.settings_file.get('on_window_spawn', default={}))

        # create widgets
        enable_opt = wx.CheckBox(
            self, id=1, label='Enable reacting to new windows being created')
        self.panel = wx.Panel(self)
        header1 = wx.StaticText(self.panel, label='When a new window is created:')
        apply_lkp_opt = wx.CheckBox(
            self.panel, id=2, label='Apply last known position')
        apply_rules_opt = wx.CheckBox(
            self.panel, id=3, label='Apply compatible rules')

        # set state
        enable_opt.SetValue(self.settings['enabled'])
        if not self.settings['enabled']:
            self.panel.Disable()
        apply_lkp_opt.SetValue(self.settings['apply_lkp'])
        apply_rules_opt.SetValue(self.settings['apply_rules'])

        # bind events
        for widget in (enable_opt, apply_lkp_opt, apply_rules_opt):
            widget.Bind(wx.EVT_CHECKBOX, self.on_setting)

        # place
        panel_sizer = wx.BoxSizer(wx.VERTICAL)
        for widget in (header1, apply_lkp_opt, apply_rules_opt):
            panel_sizer.Add(widget, 0, wx.ALL, 5)
        self.panel.SetSizerAndFit(panel_sizer)

        sizer = wx.BoxSizer(wx.VERTICAL)
        for widget in (enable_opt, self.panel):
            # panel does its own padding
            sizer.Add(widget, 0, wx.ALL, 5 if widget != self.panel else 0)
        self.SetSizerAndFit(sizer)

    def on_setting(self, event: wx.Event):
        widget = event.GetEventObject()
        if isinstance(widget, wx.CheckBox):
            if event.Id == 1:
                state = widget.GetValue()
                self.settings['enabled'] = state
                if state:
                    self.panel.Enable()
                else:
                    self.panel.Disable()
            else:
                key = {2: 'apply_lkp', 3: 'apply_rules'}[event.Id]
                self.settings[key] = widget.GetValue()

        self.settings_file.set('on_window_spawn', self.settings)
