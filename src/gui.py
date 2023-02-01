import ctypes
import re
import threading
import tkinter as tk

import win32gui

from common import local_path, size_from_rect

RULE_MANAGER_THREAD: threading.Thread = None
ROOT: tk.Tk = None


class RuleWindow():
    _instances = []
    _count = 0

    def __init__(self, root: tk.Tk, rule: dict, snapshot):
        self.__class__._instances.append(self)
        self.__class__._count += 1
        self._snapshot = snapshot

        self.root = root
        self.rule = rule
        self.window = tk.Toplevel(root)
        self.window.title(f'Rule {self._count}')
        self.window.iconbitmap(local_path('assets/icon32.ico', asset=True))
        self.set_rect()
        self.get_rect()
        self.window.protocol('WM_DELETE_WINDOW', self.destroy)

        # now create widgets for user to use
        self.frame = tk.Frame(self.window)
        self.window_name_label = tk.Label(
            self.frame, text='Window Name (regex or exact match) (leave empty to ignore):')
        self.window_name = tk.Entry(self.frame, width=50)
        self.window_exe_label = tk.Label(
            self.frame, text='Window Executable (regex or exact match) (leave empty to ignore):')
        self.window_exe = tk.Entry(self.frame, width=50)
        self.reset_btn = tk.Button(
            self.frame, text='Reset Rule', command=self.set_rect)
        self.save_btn = tk.Button(
            self.frame, text='Save', command=self.save)
        self.delete_rule_btn = tk.Button(
            self.frame, text='Delete Rule', command=self.delete_rule)
        self.new_rule_btn = tk.Button(
            self.frame, text='New Rule', command=self.new_rule)
        self.cancel_btn = tk.Button(
            self.frame, text='Discard All Unsaved Changes', command=self.destroy)
        self.save_all_btn = tk.Button(
            self.frame, text='Save All', command=self.save_all)

        # place everything
        self.frame.pack(fill='both', expand=True)
        self.frame.columnconfigure(0, weight=1)
        self.frame.columnconfigure(1, weight=1)
        self.window_name_label.grid(row=0, column=0)
        self.window_name.grid(row=0, column=1, sticky='nsew')
        self.window_exe_label.grid(row=1, column=0)
        self.window_exe.grid(row=1, column=1, sticky='nsew')
        self.reset_btn.grid(row=2, column=0, sticky='nesw')
        self.save_btn.grid(row=2, column=1, sticky='nesw')
        self.delete_rule_btn.grid(row=3, column=0, sticky='nesw')
        self.new_rule_btn.grid(row=3, column=1, sticky='nesw')
        self.cancel_btn.grid(row=4, column=0, sticky='nesw')
        self.save_all_btn.grid(row=4, column=1, sticky='nesw')

        # insert data
        self.window_name.insert(0, self.rule.get('name') or '')
        self.window_exe.insert(0, self.rule.get('executable') or '')

    def set_rect(self, rect=None, placement=None):
        if rect is None:
            rect = self.rule.get('rect')
        if placement is None:
            placement = self.rule.get('placement')
        w, h = size_from_rect(rect)
        h -= self.window.winfo_rooty() - self.window.winfo_y()
        self.window.geometry('%dx%d+%d+%d' % (w, h, rect[0], rect[1]))
        win32gui.SetWindowPlacement(self.window.winfo_id(), placement)

    def get_rect(self):
        geom = self.window.geometry()
        w, h, x, y = (int(i) for i in re.match(
            r'(-?\d+)x(-?\d+)\+(-?\d+)\+(-?\d+).*', geom).groups())
        h += self.window.winfo_rooty() - self.window.winfo_y()
        return [x, y, x + w, y + h]

    def get_placement(self):
        return win32gui.GetWindowPlacement(
            self.window.winfo_id())

    def save(self):
        self.rule['name'] = self.window_name.get() or None
        self.rule['executable'] = self.window_exe.get() or None
        minimized = self.window.state() not in ('normal', 'zoomed')
        if minimized:
            self.window.deiconify()
        self.rule['rect'] = self.get_rect()
        if minimized:
            self.window.iconify()
        self.rule['placement'] = self.get_placement()

    def save_all(self):
        for window in self.__class__._instances:
            window.window.focus_force()
            window.save()
        self.window.focus_force()
        self._snapshot.save()

    def new_rule(self):
        rect = self.get_rect()
        rule = {
            'name': None,
            'executable': None,
            'size': size_from_rect(rect),
            'rect': rect,
            'placement': self.get_placement()
        }
        self._snapshot.get_current_snapshot()['rules'].append(rule)
        self.__class__(self.root, rule, self._snapshot)

    def delete_rule(self):
        # todo: refactor all rule management into some rule manager class.
        self.destroy(False)
        self._snapshot.get_current_snapshot()['rules'].remove(self.rule)

    def destroy(self, root=True):
        if root:
            self.root.destroy()
            self.__class__._instances = []
        else:
            self.window.destroy()
            self.__class__._instances.remove(self)


def _new_rule():
    # should probably build some kind of rule manager tbh
    rect = [0, 0, 1000, 500]
    return {
        'name': None,
        'executable': None,
        'size': size_from_rect(rect),
        'rect': rect,
        'placement': [0, 1, [-1, -1], [-1, -1], rect]
    }


def spawn_rule_manager(snap):
    root = init_root()

    try:
        if root.winfo_exists() and root.winfo_children():
            return
    except tk.TclError:
        # root has been destroyed
        root = init_root(refresh=True)

    snap.get_current_snapshot().setdefault('rules', [_new_rule()])
    rules = snap.get_current_snapshot().get('rules')
    if not rules:
        rules.append(_new_rule())
    for rule in rules:
        w = RuleWindow(root, rule, snap)
        w.window.focus_force()

    root = init_root()
    root.mainloop()
    root.quit()
    RuleWindow._count = 0


def init_root(refresh=False):
    global ROOT
    if refresh and ROOT is not None:
        ROOT.quit()
        ROOT = None

    if ROOT is None:
        ROOT = tk.Tk()
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
        ROOT.withdraw()
    return ROOT
