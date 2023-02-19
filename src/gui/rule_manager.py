from copy import deepcopy
from typing import Callable

import win32gui
import wx
import wx.adv
import wx.lib.scrolledpanel

from common import Rule, size_from_rect
from gui.widgets import Frame, ListCtrl
from snapshot import SnapshotFile


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


class RuleManager(wx.Panel):
    def __init__(self, parent: wx.Frame, snapshot: SnapshotFile):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.snapshot = snapshot
        self.rules = snapshot.get_rules()

        # create action buttons
        action_panel = wx.Panel(self)
        add_rule_btn = wx.Button(action_panel, label='Create')
        edit_rule_btn = wx.Button(action_panel, label='Edit')
        dup_rule_btn = wx.Button(action_panel, label='Duplicate')
        del_rule_btn = wx.Button(action_panel, label='Delete')
        mov_up_rule_btn = wx.Button(action_panel, id=1, label='Move Up')
        mov_dn_rule_btn = wx.Button(action_panel, id=2, label='Move Down')
        # bind events
        add_rule_btn.Bind(wx.EVT_BUTTON, self.add_rule)
        edit_rule_btn.Bind(wx.EVT_BUTTON, self.edit_rule)
        dup_rule_btn.Bind(wx.EVT_BUTTON, self.duplicate_rule)
        del_rule_btn.Bind(wx.EVT_BUTTON, self.delete_rule)
        mov_up_rule_btn.Bind(wx.EVT_BUTTON, self.move_rule)
        mov_dn_rule_btn.Bind(wx.EVT_BUTTON, self.move_rule)
        # position buttons
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (add_rule_btn, edit_rule_btn, dup_rule_btn, del_rule_btn, mov_up_rule_btn, mov_dn_rule_btn):
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
        sizer.Add(action_panel, 0, wx.ALL, 5)
        sizer.Add(self.list_control, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

    def add_rule(self, *_):
        rule = _new_rule()
        rule.rule_name = 'Unnamed rule'
        self.rules.append(rule)
        self.append_rule(rule)

    def append_rule(self, rule: Rule):
        self.list_control.Append(
            (rule.rule_name or 'Unnamed rule', rule.name or '',
             rule.executable or '', str(rule.rect)))

    def edit_rule(self, *_):
        for item in self.list_control.GetAllSelected():
            RuleWindow(self, self.rules[item], on_save=self.refresh_list).Show()

    def duplicate_rule(self, *_):
        for item in self.list_control.GetAllSelected():
            self.rules.append(deepcopy(self.rules[item]))
            self.append_rule(self.rules[-1])

    def delete_rule(self, *_):
        while (item := self.list_control.GetFirstSelected()) != -1:
            self.rules.pop(item)
            self.list_control.DeleteItem(item)

    def move_rule(self, btn_event: wx.Event):
        direction = -1 if btn_event.Id == 1 else 1
        selected = list(self.list_control.GetAllSelected())
        new_positions: list[int] = []
        to_insert: list[Rule] = []

        # get all items and their new positions
        for index in reversed(selected):
            new_positions.insert(0, index + direction)
            to_insert.insert(0, self.rules.pop(index))

        # re-insert into list
        for new_index, rule in zip(new_positions, to_insert):
            self.rules.insert(new_index, rule)

        self.refresh_list(selected=new_positions)

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


def spawn_rule_manager(snap: SnapshotFile):
    rules = snap.get_rules()
    if not rules:
        rules.append(_new_rule())

    f = Frame(title='Manage Rules', size=wx.Size(600, 500))
    RuleManager(f, snap)
    f.SetIdealSize()
    f.Show()
