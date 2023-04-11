import os.path
from copy import deepcopy
from typing import Callable, TYPE_CHECKING

import win32gui
import wx
import wx.adv
import wx.lib.scrolledpanel

from common import Rule, Window, size_from_rect
from gui.widgets import Frame, ListCtrl
from snapshot import SnapshotFile
from window import capture_snapshot, restore_snapshot

if TYPE_CHECKING:
    from gui.layout_manager import LayoutManager


class RuleWindow(Frame):
    def __init__(self, parent, rule: Rule, on_save: Callable):
        self.rule = rule
        self.on_save = on_save

        # create widgets and such
        super().__init__(parent, title=self.rule.rule_name)
        self.panel = wx.lib.scrolledpanel.ScrolledPanel(self)
        self.rule_name_label = wx.StaticText(self.panel, label='Rule name')
        self.rule_name = wx.TextCtrl(self.panel)
        self.window_name_label = wx.StaticText(
            self.panel, label='Window name (regex) (leave empty to ignore)')
        self.window_name = wx.TextCtrl(self.panel)
        self.window_exe_label = wx.StaticText(
            self.panel, label='Executable path (regex) (leave empty to ignore)')
        self.window_exe = wx.TextCtrl(self.panel)
        self.reset_btn = wx.Button(self.panel, label='Reset rule')
        self.save_btn = wx.Button(self.panel, label='Save')
        self.explanation_box = wx.StaticText(self.panel, label=(
            'Resize and reposition this window and then click save.'
            ' Any window that is not currently part of a snapshot will be moved'
            ' to the same size and position as this window'
        ))

        # bind events
        self.reset_btn.Bind(wx.EVT_BUTTON, self.set_pos)
        self.save_btn.Bind(wx.EVT_BUTTON, self.save)

        # place everything
        def next_pos():
            nonlocal pos
            if pos[1] == 1:
                pos = [pos[0] + 1, 0]
            else:
                pos[1] += 1
            return tuple(pos)

        pos = [-1, 1]
        self.sizer = wx.GridBagSizer(5, 5)
        self.sizer.Add(self.rule_name_label, pos=next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.rule_name, pos=next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.window_name_label, pos=next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.window_name, pos=next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.window_exe_label, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.window_exe, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.reset_btn, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.save_btn, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.explanation_box, next_pos(),
                       span=(1, 2), flag=wx.EXPAND)
        self.panel.SetSizerAndFit(self.sizer)
        self.sizer.Fit(self.panel)

        # insert data
        self.rule_name.Value = self.rule.rule_name or ''
        self.window_name.Value = self.rule.name or ''
        self.window_exe.Value = self.rule.executable or ''

        # final steps
        self.panel.SetupScrolling()
        self.set_pos()

    def get_placement(self):
        return win32gui.GetWindowPlacement(self.GetHandle())

    def set_placement(self):
        win32gui.SetWindowPlacement(self.GetHandle(), self.rule.placement)

    def get_rect(self):
        return win32gui.GetWindowRect(self.GetHandle())

    def set_rect(self):
        rect = self.rule.rect
        w, h = size_from_rect(rect)
        win32gui.MoveWindow(self.GetHandle(), *rect[:2], w, h, 0)

    def set_pos(self, *_):
        self.set_placement()
        self.set_rect()

    def save(self, *_):
        self.rule.rule_name = self.rule_name.Value or None
        self.rule.name = self.window_name.Value or None
        self.rule.executable = self.window_exe.Value or None
        self.rule.rect = self.get_rect()
        self.rule.size = size_from_rect(self.rule.rect)
        self.rule.placement = self.get_placement()
        self.on_save()


class WindowClone(Frame):
    def __init__(self, parent, on_clone: Callable[[list[Window]], None], **kwargs):
        super().__init__(parent, 'Clone a Window', **kwargs)
        self.on_clone = on_clone

        # create action buttons
        action_panel = wx.Panel(self)
        clone_btn = wx.Button(action_panel, label='Clone')
        deselect_all_btn = wx.Button(action_panel, label='Deselect All')
        select_all_btn = wx.Button(action_panel, label='Select All')
        # bind events
        clone_btn.Bind(wx.EVT_BUTTON, self.clone)
        deselect_all_btn.Bind(wx.EVT_BUTTON, self.deselect_all)
        select_all_btn.Bind(wx.EVT_BUTTON, self.select_all)
        # place
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (clone_btn, deselect_all_btn, select_all_btn):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create option checks
        self._clone_opts = {'name': True, 'executable': True}
        option_panel = wx.Panel(self)
        window_name_opt = wx.CheckBox(
            option_panel, id=1, label='Clone window names')
        window_exe_opt = wx.CheckBox(
            option_panel, id=2, label='Clone window executable paths')
        # bind events and set states
        window_name_opt.SetValue(wx.CHK_CHECKED)
        window_name_opt.Bind(wx.EVT_CHECKBOX, self.on_check)
        window_exe_opt.SetValue(wx.CHK_CHECKED)
        window_exe_opt.Bind(wx.EVT_CHECKBOX, self.on_check)
        # place
        option_sizer = wx.GridSizer(cols=2, hgap=5, vgap=5)
        option_sizer.Add(window_name_opt, 0, wx.ALIGN_CENTER)
        option_sizer.Add(window_exe_opt, 0, wx.ALIGN_CENTER)
        option_panel.SetSizer(option_sizer)

        self.check_list = wx.CheckListBox(
            self, id=wx.ID_ANY, style=wx.LB_EXTENDED | wx.LB_NEEDED_SB)

        self.windows = sorted(capture_snapshot(), key=lambda w: w.name)
        self.check_list.AppendItems(tuple(i.name for i in self.windows))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(action_panel, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(option_panel, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.check_list, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizerAndFit(sizer)

    def clone(self, *_):
        to_clone = []
        for index in self.check_list.GetCheckedItems():
            window = deepcopy(self.windows[index])
            for prop, include in self._clone_opts.items():
                if not include:
                    setattr(window, prop, '')
            to_clone.append(window)

        self.on_clone(to_clone)

        try:
            self.Close()
            self.Destroy()
        except RuntimeError:
            pass

    def deselect_all(self, *_):
        self.select_all(check=False)

    def on_check(self, event: wx.Event):
        check: wx.CheckBox = event.GetEventObject()
        if event.Id == 1:
            self._clone_opts['name'] = check.GetValue()
        else:
            self._clone_opts['executable'] = check.GetValue()

    def select_all(self, *_, check=True):
        for i in range(len(self.windows)):
            self.check_list.Check(i, check=check)


class RuleSubsetManager(wx.StaticBox):
    def __init__(self, parent: 'LayoutManager', snapshot: SnapshotFile, rules: list[Rule], label=None):
        wx.StaticBox.__init__(self, parent, label=label or '')
        self.snapshot = snapshot
        self.rules = rules

        # create action buttons
        action_panel = wx.Panel(self)
        apply_btn = wx.Button(action_panel, label='Apply')
        add_rule_btn = wx.Button(action_panel, label='Create')
        clone_window_btn = wx.Button(action_panel, label='Clone Window')
        edit_rule_btn = wx.Button(action_panel, label='Edit')
        dup_rule_btn = wx.Button(action_panel, label='Duplicate')
        del_rule_btn = wx.Button(action_panel, label='Delete')
        mov_up_rule_btn = wx.Button(action_panel, id=1, label='Move Up')
        mov_dn_rule_btn = wx.Button(action_panel, id=2, label='Move Down')
        # move_to_btn = wx.Button(action_panel, id=3, label='Move To')
        # bind events
        apply_btn.Bind(wx.EVT_BUTTON, self.apply_rule)
        add_rule_btn.Bind(wx.EVT_BUTTON, self.add_rule)
        clone_window_btn.Bind(wx.EVT_BUTTON, self.clone_windows)
        edit_rule_btn.Bind(wx.EVT_BUTTON, self.edit_rule)
        dup_rule_btn.Bind(wx.EVT_BUTTON, self.duplicate_rule)
        del_rule_btn.Bind(wx.EVT_BUTTON, self.delete_rule)
        mov_up_rule_btn.Bind(wx.EVT_BUTTON, self.move_rule)
        mov_dn_rule_btn.Bind(wx.EVT_BUTTON, self.move_rule)
        # move_to_btn.Bind(wx.EVT_BUTTON, self.move_to)
        # position buttons
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (
            apply_btn, add_rule_btn, clone_window_btn, edit_rule_btn, dup_rule_btn,
            del_rule_btn, mov_up_rule_btn, mov_dn_rule_btn,
            # move_to_btn
        ):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create list control
        self.list_control = ListCtrl(self)
        self.list_control.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edit_rule)
        for index, col in enumerate(('Rule Name', 'Window Title', 'Window Executable', 'Window Rect')):
            self.list_control.AppendColumn(col)
            self.list_control.SetColumnWidth(index, 200 if index < 3 else 150)

        # add rules
        for rule in self.rules:
            self.append_rule(rule)

        # position list control
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(15)
        sizer.Add(action_panel, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.list_control, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

    def add_rule(self, *_):
        rule = _new_rule()
        rule.rule_name = 'Unnamed rule'
        self.rules.append(rule)
        self.append_rule(rule)
        self.snapshot.save()

    def apply_rule(self, *_):
        rules = []
        for index in self.list_control.GetAllSelected():
            rules.append(self.rules[index])
        restore_snapshot([], rules)

    def append_rule(self, rule: Rule):
        self.list_control.Append(
            (rule.rule_name or 'Unnamed rule', rule.name or '',
             rule.executable or '', str(rule.rect)))

    def edit_rule(self, *_):
        for item in self.list_control.GetAllSelected():
            RuleWindow(self, self.rules[item],
                       on_save=self.refresh_list).Show()

    def clone_windows(self, *_):
        def on_clone(windows: list[Window]):
            for window in windows:
                if window.executable:
                    rule_name = os.path.basename(window.executable) + ' rule'
                else:
                    rule_name = 'Unnamed rule'

                rule = Rule(
                    size=window.size,
                    rect=window.rect,
                    placement=window.placement,
                    name=window.name,
                    executable=window.executable,
                    rule_name=rule_name
                )
                self.rules.append(rule)
                self.append_rule(rule)
            self.snapshot.save()

        WindowClone(self, on_clone).Show()

    def delete_rule(self, *_):
        while (item := self.list_control.GetFirstSelected()) != -1:
            self.rules.pop(item)
            self.list_control.DeleteItem(item)
        self.snapshot.save()

    def duplicate_rule(self, *_):
        for item in self.list_control.GetAllSelected():
            self.rules.append(deepcopy(self.rules[item]))
            self.append_rule(self.rules[-1])
        self.snapshot.save()

    def insert_rule(self, index: int, rule: Rule):
        self.list_control.Insert(
            index,
            (rule.rule_name or 'Unnamed rule', rule.name or '',
             rule.executable or '', str(rule.rect)))

    def move_rule(self, btn_event: wx.Event):
        direction = -1 if btn_event.Id == 1 else 1
        selected = list(self.list_control.GetAllSelected())
        items: list[tuple[int, Rule]] = []

        # get all items and their new positions
        for index in reversed(selected):
            self.list_control.DeleteItem(index)
            items.insert(0, (max(0, index + direction), self.rules.pop(index)))

        # re-insert into list
        for new_index, rule in items:
            self.rules.insert(new_index, rule)
            self.insert_rule(new_index, rule)
            self.list_control.Select(new_index)

        self.snapshot.save()

    def move_to(self, btn_event: wx.Event):
        pass

    def refresh_list(self, selected=None):
        selected = selected or []
        self.list_control.DeleteAllItems()
        for index, rule in enumerate(self.rules):
            self.append_rule(rule)
            self.list_control.Select(index, on=index in selected)
        self.snapshot.save()


def _new_rule():
    rect = (0, 0, 1000, 500)
    return Rule(
        size=size_from_rect(rect),
        rect=rect,
        placement=(0, 1, (-1, -1), (-1, -1), rect)
    )
