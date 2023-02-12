import threading
from copy import deepcopy

import win32gui
import wx
import wx.adv
import wx.lib.scrolledpanel

from common import Rule, local_path, size_from_rect
from snapshot import SnapshotFile

RULE_MANAGER_THREAD: threading.Thread = None
ROOT: wx.App = None


class RuleWindow(wx.Frame):
    _instances = []
    _count = 0

    def __init__(self, rule: Rule, snapshot: SnapshotFile):
        self.__class__._instances.append(self)
        self.__class__._count += 1
        self.rule = rule
        self.snapshot = snapshot

        # create widgets and such
        super().__init__(parent=None, title=f'Rule {self._count} (Beta)')
        self.SetIcon(wx.Icon(local_path('assets/icon32.ico', asset=True)))
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
        self.delete_rule_btn = wx.Button(self.panel, label='Delete rule')
        self.new_rule_btn = wx.Button(self.panel, label='New rule')
        self.cancel_btn = wx.Button(
            self.panel, label='Discard all unsaved changes')
        self.save_all_btn = wx.Button(self.panel, label='Save all')
        self.explanation_box = wx.StaticText(self.panel, label=(
            'Resize and reposition this window and then click save.'
            ' Any window that is not currently part of a snapshot will be moved'
            ' to the same size and position as this window'
        ))

        # bind events
        self.reset_btn.Bind(wx.EVT_BUTTON, self.set_pos)
        self.save_btn.Bind(wx.EVT_BUTTON, self.save)
        self.delete_rule_btn.Bind(wx.EVT_BUTTON, self.delete)
        self.new_rule_btn.Bind(wx.EVT_BUTTON, self.new_rule)
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.destroy)
        self.save_all_btn.Bind(wx.EVT_BUTTON, self.save_all)

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
        self.sizer.Add(self.delete_rule_btn, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.new_rule_btn, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.cancel_btn, next_pos(), flag=wx.EXPAND)
        self.sizer.Add(self.save_all_btn, next_pos(), flag=wx.EXPAND)
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
        self.Show()

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
        if self.rule not in self.snapshot.get_rules():
            self.snapshot.get_rules().append(self.rule)
        self.snapshot.save()

    def save_all(self, *_):
        for instance in self._instances:
            instance.save()

    def new_rule(self, *_):
        rule = deepcopy(self.rule)
        self.snapshot.get_rules().append(rule)
        RuleWindow(self.root, rule, self.snapshot)

    def delete(self, *_):
        try:
            self.snapshot.get_rules().remove(self.rule)
        except ValueError:
            pass
        self.destroy()

    def destroy(self, *_):
        try:
            self.Close()
            self.Destroy()
        except RuntimeError:
            pass

        try:
            self._instances.remove(self)
        except ValueError:
            pass


def _new_rule():
    # should probably build some kind of rule manager tbh
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
    for rule in rules:
        RuleWindow(rule, snap)

    RuleWindow._count = 0
