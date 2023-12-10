from typing import Literal, TypedDict

import wx

from common import load_json
from gui.widgets import EVT_REARRANGE_LIST_SELECT, RearrangeListCtrl, simple_box_sizer

OnSpawnOperations = Literal['apply_lkp', 'apply_rules', 'move_to_mouse']


class OnSpawnSettings(TypedDict):
    enabled: bool
    move_to_mouse: bool
    apply_lkp: bool
    apply_rules: bool
    operation_order: list[OnSpawnOperations]
    ignore_children: bool
    capture_snapshot: bool | int  # 0/False: disable, 1/True: capture, 2: update
    skip_non_resizable: bool
    match_resizability: bool
    fuzzy_mtm: bool


class OnSpawnPage(wx.Panel):
    def __init__(self, parent: wx.Frame):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.settings_file = load_json('settings')
        self.settings = OnSpawnSettings(
            enabled=False,
            move_to_mouse=False,
            apply_lkp=True,
            apply_rules=True,
            operation_order=['apply_lkp', 'apply_rules', 'move_to_mouse'],
            ignore_children=True,
            capture_snapshot=2,
            skip_non_resizable=False,
            match_resizability=True,
            fuzzy_mtm=True,
        )
        self.settings.update(OnSpawnSettings(**self.settings_file.get('on_window_spawn', default={})))

        def header(text: str):
            txt = wx.StaticText(self.panel, label=text)
            txt.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL))
            return txt

        # create widgets
        enable_opt = wx.CheckBox(self, id=1, label='React to new windows being created')
        enable_opt.SetToolTip('It\'s recommended to disable "Prune window history" when this is enabled')
        self.panel = wx.Panel(self)
        header1 = header('When a new window spawns:')

        # reused later on in Misc settings.
        mtm_opt_name = 'Center on current mouse position'

        option_mapping: dict[str, OnSpawnOperations] = {
            'Apply last known size and/or position': 'apply_lkp',
            'Apply compatible rules': 'apply_rules',
            mtm_opt_name: 'move_to_mouse',
        }
        self.rc_opt = RearrangeListCtrl(
            self.panel,
            options={k: self.settings[k] for k in ('apply_lkp', 'apply_rules', 'move_to_mouse')},
            order=self.settings['operation_order'],
            label_mapping=option_mapping,
        )

        header2 = header('After a new window spawns:')

        update_snapshot_opt = wx.RadioButton(self.panel, id=6, label='Update the current snapshot', style=wx.RB_GROUP)
        capture_snapshot_opt = wx.RadioButton(self.panel, id=7, label='Capture a new snapshot')
        do_nothing_opt = wx.RadioButton(self.panel, id=8, label='Do nothing')

        header3 = header('Window filtering controls:')

        ignore_children_opt = wx.CheckBox(self.panel, id=5, label='Ignore child windows')
        ignore_children_opt.SetToolTip(
            'Child windows are typically small popup windows that spawn near the cursor.'
            # '\nDisabling this means such windows will be moved to the top left corner of the parent window.'
            # ^ this may not be accurate. TODO: remove or implement this
        )
        skip_non_resizable_opt = wx.CheckBox(self.panel, id=9, label='Ignore non-resizable windows')
        skip_non_resizable_opt.SetToolTip(
            'Non resizable windows often include splash screens, alerts and notifications. Enable this to'
            ' prevent those windows from being moved, resized or added to the snapshot when they spawn.'
        )

        match_resizability_opt = wx.CheckBox(
            self.panel, id=10, label='Filter last known window instances by resizability'
        )
        match_resizability_opt.SetToolTip(
            'When looking for the last known size/position of a window, filter out instances where'
            ' the current window is resizable but the last known instance was not, or vice versa.'
            '\nThis prevents splash screens from dictating the final window size.'
        )

        header4 = header('Misc')

        fuzzy_mtm_opt = wx.CheckBox(
            self.panel, id=11, label=f'Disable "{mtm_opt_name}" when mouse is already within the window'
        )

        # set state
        enable_opt.SetValue(self.settings['enabled'])
        if not self.settings['enabled']:
            self.panel.Disable()
        ignore_children_opt.SetValue(self.settings['ignore_children'])

        update_snapshot_opt.SetValue(False)
        capture_snapshot_opt.SetValue(False)
        do_nothing_opt.SetValue(False)
        # set the relevant radio button based on user settings
        [do_nothing_opt, capture_snapshot_opt, update_snapshot_opt][int(self.settings['capture_snapshot'])].SetValue(
            True
        )
        fuzzy_mtm_opt.SetValue(self.settings['fuzzy_mtm'])

        skip_non_resizable_opt.SetValue(self.settings['skip_non_resizable'])
        match_resizability_opt.SetValue(self.settings['match_resizability'])

        # bind events
        for widget in (
            enable_opt,
            ignore_children_opt,
            update_snapshot_opt,
            capture_snapshot_opt,
            do_nothing_opt,
            skip_non_resizable_opt,
            match_resizability_opt,
            fuzzy_mtm_opt,
        ):
            widget.Bind(wx.EVT_CHECKBOX if isinstance(widget, wx.CheckBox) else wx.EVT_RADIOBUTTON, self.on_setting)
        self.rc_opt.Bind(EVT_REARRANGE_LIST_SELECT, self.on_setting)

        # place
        simple_box_sizer(
            self.panel,
            (
                header1,
                self.rc_opt,
                header2,
                update_snapshot_opt,
                capture_snapshot_opt,
                do_nothing_opt,
                header3,
                ignore_children_opt,
                skip_non_resizable_opt,
                match_resizability_opt,
                header4,
                fuzzy_mtm_opt,
            ),
            group_mode=wx.HORIZONTAL,
        )

        sizer = wx.BoxSizer(wx.VERTICAL)
        for widget in (enable_opt, self.panel):
            # panel does its own padding
            sizer.Add(widget, 0, wx.ALL, 5 if widget != self.panel else 0)
        self.SetSizerAndFit(sizer)

    def on_setting(self, event: wx.Event):
        widget = event.GetEventObject()
        if isinstance(widget, wx.CheckBox):
            key = {
                1: 'enabled',
                2: 'move_to_mouse',
                3: 'apply_lkp',
                4: 'apply_rules',
                5: 'ignore_children',
                9: 'skip_non_resizable',
                10: 'match_resizability',
                11: 'fuzzy_mtm',
            }[event.Id]
            self.settings[key] = widget.GetValue()
            if event.Id == 1:  # enable/disable feature
                if widget.GetValue():
                    self.panel.Enable()
                else:
                    self.panel.Disable()
        elif isinstance(widget, wx.RadioButton):
            ids = [8, 7, 6]  # do nothing, capture, update
            self.settings['capture_snapshot'] = ids.index(widget.Id)
        elif isinstance(widget, RearrangeListCtrl):
            operations = self.rc_opt.get_selection()
            self.settings['operation_order'] = list(operations.keys())  # type: ignore
            self.settings.update(operations)  # type: ignore

        self.settings_file.set('on_window_spawn', self.settings)
