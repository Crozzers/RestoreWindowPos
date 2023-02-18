from typing import Callable

import wx

from common import format_unit, local_path

from .wx_app import WxApp


class TaskbarIcon(wx.adv.TaskBarIcon):
    SEPARATOR = wx.ITEM_SEPARATOR

    def __init__(self, menu_options: list[list], on_click: Callable = None, on_exit: Callable = None):
        wx.adv.TaskBarIcon.__init__(self)
        self.SetIcon(
            wx.Icon(local_path('assets/icon32.ico', asset=True)), 'RestoreWindowPos')
        self.menu_options = menu_options
        self._on_click = on_click
        self._on_exit = on_exit

    def set_menu_options(self, menu_options):
        self.menu_options = menu_options

    def CreatePopupMenu(self):
        if callable(self._on_click):
            self._on_click()
        if self.menu_options is None:
            return False
        menu = wx.Menu()
        menu_from_list(menu, self.menu_options +
                       [self.SEPARATOR, ['Quit', lambda *_: self.exit()]])
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


def menu_from_list(menu: wx.Menu, menu_items: list) -> wx.Menu:
    for index, item in enumerate(menu_items):
        if item == wx.ITEM_SEPARATOR:
            if index > 0 and menu_items[index - 1] != wx.ITEM_SEPARATOR:
                menu.AppendSeparator()
        elif not callable(item[1]):
            sub_menu = wx.Menu()
            menu_from_list(sub_menu, item[1])
            menu.Append(wx.ID_ANY, item[0], sub_menu)
        else:
            menu_item = wx.MenuItem(menu, id=wx.ID_ANY, text=item[0])
            menu.Bind(wx.EVT_MENU, item[1], id=menu_item.GetId())
            menu.Append(menu_item)


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
        opts.append([label, lambda *_, i=index, v=val: cb(opts, i, v)])
    return opts
