from typing import TypedDict

import wx

from common import load_json
from gui.widgets import simple_box_sizer


class OnSpawnSettings(TypedDict):
    enabled: bool
    move_to_mouse: bool
    apply_lkp: bool
    apply_rules: bool
    ignore_children: bool
    capture_snapshot: bool | int  # 0/False: disable, 1/True: capture, 2: update


class OnSpawnPage(wx.Panel):
    def __init__(self, parent: wx.Frame):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.settings_file = load_json('settings')
        self.settings = OnSpawnSettings(
            enabled=False, move_to_mouse=False, apply_lkp=True, apply_rules=True,
            ignore_children=True, capture_snapshot=2)
        self.settings.update(self.settings_file.get(
            'on_window_spawn', default={}))

        # create widgets
        enable_opt = wx.CheckBox(
            self, id=1, label='React to new windows being created')
        enable_opt.SetToolTip(
            'It\'s recommended to disable "Prune window history" when this is enabled')
        self.panel = wx.Panel(self)
        header1 = wx.StaticText(
            self.panel, label='When a new window is created:')
        move_to_mouse_opt = wx.CheckBox(
            self.panel, id=2, label='Center on current mouse position')
        # store as instance attr to modify text later
        apply_lkp_opt = wx.CheckBox(
            self.panel, id=3, label='Apply last known size and/or position')
        apply_rules_opt = wx.CheckBox(
            self.panel, id=4, label='Apply compatible rules')
        ignore_children_opt = wx.CheckBox(
            self.panel, id=5, label='Ignore child windows')
        ignore_children_opt.SetToolTip(
            'Child windows are typically small popup windows and spawn near where the cursor is.'
            '\nDisabling this means such windows will be moved to the top left corner of the parent window.'
        )
        update_snapshot_opt = wx.RadioButton(
            self.panel, id=6, label='Update the current snapshot', style=wx.RB_GROUP)
        capture_snapshot_opt = wx.RadioButton(
            self.panel, id=7, label='Capture a new snapshot')
        do_nothing_opt = wx.RadioButton(
            self.panel, id=8, label='Do nothing')

        # set state
        enable_opt.SetValue(self.settings['enabled'])
        if not self.settings['enabled']:
            self.panel.Disable()
        move_to_mouse_opt.SetValue(self.settings['move_to_mouse'])
        if move_to_mouse_opt.GetValue():
            apply_lkp_opt.SetLabelText(
                apply_lkp_opt.LabelText.removesuffix('and position'))
        apply_lkp_opt.SetValue(self.settings['apply_lkp'])
        apply_rules_opt.SetValue(self.settings['apply_rules'])
        ignore_children_opt.SetValue(self.settings['ignore_children'])

        update_snapshot_opt.SetValue(False)
        capture_snapshot_opt.SetValue(False)
        do_nothing_opt.SetValue(False)
        # set the relevant radio button based on user settings
        [do_nothing_opt, capture_snapshot_opt, update_snapshot_opt][int(
            self.settings['capture_snapshot'])].SetValue(True)

        # bind events
        for widget in (
            enable_opt, move_to_mouse_opt, apply_lkp_opt, apply_rules_opt,
            ignore_children_opt, update_snapshot_opt, capture_snapshot_opt, do_nothing_opt
        ):
            widget.Bind(
                wx.EVT_CHECKBOX if isinstance(widget, wx.CheckBox) else wx.EVT_RADIOBUTTON,
                self.on_setting
            )

        # place
        simple_box_sizer(
            self.panel,
            (header1, move_to_mouse_opt, apply_lkp_opt, apply_rules_opt,
             ignore_children_opt, update_snapshot_opt, capture_snapshot_opt, do_nothing_opt),
            group_mode=wx.HORIZONTAL
        )

        sizer = wx.BoxSizer(wx.VERTICAL)
        for widget in (enable_opt, self.panel):
            # panel does its own padding
            sizer.Add(widget, 0, wx.ALL, 5 if widget != self.panel else 0)
        self.SetSizerAndFit(sizer)

    def on_setting(self, event: wx.Event):
        widget = event.GetEventObject()
        if isinstance(widget, wx.CheckBox):
            key = {1: 'enabled', 2: 'move_to_mouse', 3: 'apply_lkp', 4: 'apply_rules',
                   5: 'ignore_children'}[event.Id]
            self.settings[key] = widget.GetValue()
            if event.Id == 1:  # enable/disable feature
                if widget.GetValue():
                    self.panel.Enable()
                else:
                    self.panel.Disable()
        elif isinstance(widget, wx.RadioButton):
            ids = [8, 7, 6]  # do nothing, capture, update
            self.settings['capture_snapshot'] = ids.index(widget.Id)

        self.settings_file.set('on_window_spawn', self.settings)
