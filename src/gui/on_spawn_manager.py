from typing import Callable, List, Literal, Optional, TypedDict

import wx
import wx.lib.scrolledpanel

from common import load_json
from gui.widgets import EVT_REARRANGE_LIST_SELECT, EditableListCtrl, RearrangeListCtrl, simple_box_sizer

OnSpawnOperations = Literal['apply_lkp', 'apply_rules', 'move_to_mouse']


class WindowDictLite(TypedDict):
    '''
    Super light typed dict that can be expanded to use the full `Window` class without much hassle
    '''
    name: str
    executable: str


class OnSpawnSettings(TypedDict):
    name: str
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
    apply_to: Optional[WindowDictLite]


class OverallSpawnSettings(OnSpawnSettings):
    profiles: List[OnSpawnSettings]


def default_spawn_settings():
    return OnSpawnSettings(
            name='Profile',
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
            apply_to=None
        )


class OnSpawnPanel(wx.Panel):
    def __init__(self, parent: wx.Window, profile: OnSpawnSettings, on_save: Callable[[OnSpawnSettings], None]):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.on_save = on_save
        for key, value in default_spawn_settings().items():
            profile.setdefault(key, value)  # type: ignore

        self.profile = profile

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
            options={k: self.profile[k] for k in ('apply_lkp', 'apply_rules', 'move_to_mouse')},
            order=self.profile['operation_order'],
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

        header4 = header('Misc:')

        fuzzy_mtm_opt = wx.CheckBox(
            self.panel, id=11, label=f'Disable "{mtm_opt_name}" when mouse is already within the window'
        )

        if self.profile['name'] == 'Global':
            apply_to_widgets = ()
        else:
            header5 = header('Apply to:')
            window_name_label = wx.StaticText(self.panel, label='Window name (regex) (leave empty to match all windows):')
            window_name = wx.TextCtrl(self.panel, id=12)
            window_exe_label = wx.StaticText(self.panel, label='Window executable (regex) (leave empty to match all windows):')
            window_exe = wx.TextCtrl(self.panel, id=13)
            apply_to = self.profile.get('apply_to', {})
            if apply_to:
                window_name.SetValue(apply_to.get('name', ''))
                window_exe.SetValue(apply_to.get('executable', ''))
            window_name.Bind(wx.EVT_KEY_UP, self.on_setting)
            window_exe.Bind(wx.EVT_KEY_UP, self.on_setting)

            ### TODO: add note here explaining why one must be filled

            apply_to_widgets = (header5, window_name_label, window_name, window_exe_label, window_exe)

        # set state
        enable_opt.SetValue(self.profile['enabled'])
        if not self.profile['enabled']:
            self.panel.Disable()
        ignore_children_opt.SetValue(self.profile['ignore_children'])

        update_snapshot_opt.SetValue(False)
        capture_snapshot_opt.SetValue(False)
        do_nothing_opt.SetValue(False)
        # set the relevant radio button based on user settings
        [do_nothing_opt, capture_snapshot_opt, update_snapshot_opt][int(self.profile['capture_snapshot'])].SetValue(
            True
        )
        fuzzy_mtm_opt.SetValue(self.profile['fuzzy_mtm'])

        skip_non_resizable_opt.SetValue(self.profile['skip_non_resizable'])
        match_resizability_opt.SetValue(self.profile['match_resizability'])

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
                *apply_to_widgets
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
            self.profile[key] = widget.GetValue()
            if event.Id == 1:  # enable/disable feature
                if widget.GetValue():
                    self.panel.Enable()
                else:
                    self.panel.Disable()
        elif isinstance(widget, wx.RadioButton):
            ids = [8, 7, 6]  # do nothing, capture, update
            self.profile['capture_snapshot'] = ids.index(widget.Id)
        elif isinstance(widget, RearrangeListCtrl):
            operations = self.rc_opt.get_selection()
            self.profile['operation_order'] = list(operations.keys())  # type: ignore
            self.profile.update(operations)  # type: ignore
        elif isinstance(widget, wx.TextCtrl) and isinstance(event, wx.KeyEvent):
            # allow text ctrl to sort itself out and insert values
            event.Skip()
            name = self.panel.FindWindowById(12).GetValue()
            exe = self.panel.FindWindowById(13).GetValue()
            apply_to: Optional[WindowDictLite]
            if name or exe:
                apply_to = {
                    'name': self.panel.FindWindowById(12).GetValue(),
                    'executable': self.panel.FindWindowById(13).GetValue()
                }
            else:
                apply_to = None
            self.profile['apply_to'] = apply_to

        self.on_save(self.profile)


class OnSpawnPage(wx.lib.scrolledpanel.ScrolledPanel):
    def __init__(self, parent: wx.Frame):
        wx.lib.scrolledpanel.ScrolledPanel.__init__(self, parent, id=wx.ID_ANY)
        self.settings_file = load_json('settings')

        self.settings: OverallSpawnSettings = {**default_spawn_settings(), 'name': 'Global', 'profiles': []}
        if (ows := self.settings_file.get('on_window_spawn')) is not None:
            self.settings.update(ows)

        self.profile_box = wx.StaticBox(self, label='Profiles')
        action_panel = wx.Panel(self.profile_box)
        add_profile_btn = wx.Button(action_panel, label='Add profile')
        del_profile_btn = wx.Button(action_panel, label='Delete profile')

        self.profiles_list = EditableListCtrl(
            self.profile_box,
            post_edit=self.rename_profile,
            style=wx.LC_REPORT | wx.LC_EDIT_LABELS | wx.LC_SINGLE_SEL
        )
        self.profiles_list.AppendColumn('Profiles')
        self.profiles_list.SetColumnWidth(0, 300)
        self.populate_profiles()
        self.profiles_list.Unbind(wx.EVT_LEFT_DOWN)
        self.profiles_list.Bind(wx.EVT_LEFT_DOWN, self.select_profile)

        add_profile_btn.Bind(wx.EVT_BUTTON, self.add_profile)
        del_profile_btn.Bind(wx.EVT_BUTTON, self.del_profile)

        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        action_sizer.Add(add_profile_btn)
        action_sizer.Add(del_profile_btn)
        action_panel.SetSizerAndFit(action_sizer)

        profile_sizer = wx.BoxSizer(wx.VERTICAL)
        profile_sizer.Add(action_panel)
        profile_sizer.Add(self.profiles_list)
        self.profile_box.SetSizerAndFit(profile_sizer)

        self.profile_panel = OnSpawnPanel(self, self.settings, self.on_save)

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.profile_box)
        self.sizer.Add(self.profile_panel)
        self.SetSizerAndFit(self.sizer)

        self.SetupScrolling()

    def add_profile(self, event: wx.Event):
        new = default_spawn_settings()
        self.profiles_list.Append((new['name'],))
        self.settings['profiles'].append(new)
        event.Skip()

    def del_profile(self, event: wx.Event):
        for index in reversed(sorted(self.profiles_list.GetAllSelected())):
            if index == 0:
                continue
            self.profiles_list.DeleteItem(index)
            self.settings['profiles'].pop(index - 1)

    def rename_profile(self, col, row):
        for index, profile in enumerate(self.get_all_profiles()):
            if index == 0:
                self.profiles_list.SetItemText(index, 'Global')
            else:
                text = self.profiles_list.GetItemText(index)
                if text == 'Global':
                    self.profiles_list.SetItemText(index, profile['name'])
                else:
                    profile['name'] = self.profiles_list.GetItemText(index)

    def populate_profiles(self):
        for index in range(self.profiles_list.GetItemCount()):
            self.profiles_list.DeleteItem(index)
        for profile in self.get_all_profiles():
            self.profiles_list.Append((profile['name'],))

    def get_all_profiles(self):
        return [self.settings] + self.settings['profiles']

    def select_profile(self, event: wx.MouseEvent):
        x,y = event.GetPosition()
        row, _ = self.profiles_list.HitTest((x, y))
        if row < 0:
            event.Skip()
            return
        self.profiles_list.Select(row)
        self.set_state(row)

    def set_state(self, selected = None):
        self.sizer.Remove(1)
        self.profile_panel.Destroy()
        selected = self.profiles_list.GetFirstSelected() if selected is None else selected
        if selected == 0:
            profile = self.settings
        else:
            profile = self.settings['profiles'][selected - 1]
        self.profile_panel = OnSpawnPanel(self, profile, self.on_save)
        self.sizer.Add(self.profile_panel, 0, wx.ALL | wx.EXPAND, 0)
        self.sizer.Layout()
        self.profile_panel.Update()
        self.SetupScrolling()

    def on_save(self, event = None):
        self.settings_file.set('on_window_spawn', self.settings)
