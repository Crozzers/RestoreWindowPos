from typing import Callable

import wx

from common import format_unit, local_path, tuple_convert

from .wx_app import WxApp


class TaskbarIcon(wx.adv.TaskBarIcon):
    def __init__(self, menu_options: list[list], on_click: Callable = None, on_exit: Callable = None):
        wx.adv.TaskBarIcon.__init__(self)
        self.SetIcon(
            wx.Icon(local_path('assets/icon32.ico', asset=True)), 'RestoreWindowPos')
        self.menu_options = menu_options
        self._on_click = on_click
        self._on_exit = on_exit

    def create_menu_item(self, text: str, callback: Callable, menu: wx.Menu = None):
        menu = menu or self.menu
        item = wx.MenuItem(menu, -1, text)
        menu.Bind(wx.EVT_MENU, lambda *_: callback(), id=item.GetId())
        menu.Append(item)
        return item

    def create_sub_menu(self, text, items: tuple[str, Callable]):
        submenu = wx.Menu()
        for item in items:
            self.create_menu_item(item[0], item[2], submenu)
        self.menu.Append(wx.ID_ANY, text, submenu)

    def populate_from_list(self, menu_items):
        for item in menu_items:
            text, _, callback = item
            if callable(callback):
                self.create_menu_item(text, callback)
            else:
                self.create_sub_menu(text, callback)

    def set_menu_options(self, menu_options):
        self.menu_options = menu_options

    def CreatePopupMenu(self):
        if callable(self._on_click):
            self._on_click()
        if self.menu_options is None:
            return False
        menu = wx.Menu()
        self.menu = menu
        self.populate_from_list(self.menu_options)
        self.create_menu_item('Quit', lambda *_: self.exit())
        return menu

    def exit(self):
        if callable(self._on_exit):
            self._on_exit()
        self.RemoveIcon()
        WxApp().schedule_exit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.exit()


def list_to_tuple(item):
    return tuple_convert(item, to=tuple, from_=list)


def submenu_from_settings(settings, key, default, label_unit, allowed_values):
    def cb(options, index, value):
        settings.set(key, value)
        for i, opt in enumerate(options):
            if i == index and '[current]' not in opt[0]:
                opt[0] += ' [current]'
            elif i != index and '[current]' in opt[0]:
                opt[0] = opt[0].replace(' [current]', '')

    opts = []
    for index, val in enumerate(allowed_values):
        label = format_unit(label_unit, val)
        if val == settings.get(key, default):
            label += ' [current]'
        opts.append([label, None, lambda *_, i=index, v=val: cb(opts, i, v)])
    return opts
