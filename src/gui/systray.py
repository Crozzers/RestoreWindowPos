import logging
from typing import Any, Callable, Optional

import wx
import wx.adv

from common import local_path

log = logging.getLogger(__name__)

MenuItem = tuple[str, Callable | 'MenuList', Optional[bool]]
MenuList = list[MenuItem]


class TaskbarIcon(wx.adv.TaskBarIcon):
    SEPARATOR = wx.ITEM_SEPARATOR
    RADIO = wx.ITEM_RADIO
    NORMAL = wx.ITEM_NORMAL

    def __init__(
        self, menu_options: MenuList, on_click: Optional[Callable] = None, on_exit: Optional[Callable] = None
    ):
        wx.adv.TaskBarIcon.__init__(self)
        self.SetIcon(wx.Icon(local_path('assets/icon32.ico', asset=True)), 'RestoreWindowPos')
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
        menu_from_list(menu, self.menu_options + [self.SEPARATOR, ['Quit', lambda *_: self.exit()]])
        return menu

    def exit(self):
        self.RemoveIcon()
        if callable(self._on_exit):
            self._on_exit()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.exit()


def execute_menu_item(callback, *args):
    try:
        callback(*args)
    except Exception as e:
        log.exception(f'failed to execute menu item {callback}, args: {args}')
        wx.MessageBox(
            f'Failed to execute system tray menu command\n{type(e).__name__}: {e}',
            'RestoreWindowPos',
            wx.OK | wx.ICON_ERROR,
        )
        raise


def menu_from_list(menu: wx.Menu, menu_items: MenuList):
    """Modifies menu inplace"""
    item_kind = TaskbarIcon.NORMAL

    for index, item in enumerate(menu_items):
        if item == TaskbarIcon.RADIO:
            item_kind = TaskbarIcon.RADIO
            continue
        elif item == TaskbarIcon.NORMAL:
            item_kind = TaskbarIcon.NORMAL
            continue

        if item == TaskbarIcon.SEPARATOR:
            if index > 0 and menu_items[index - 1] != TaskbarIcon.SEPARATOR:
                menu.AppendSeparator()
        elif len(item) == 1:
            item = wx.MenuItem(menu, id=wx.ID_ANY, text=item[0], kind=TaskbarIcon.NORMAL)
            item.Enable(False)
            menu.Append(item)
        elif not callable(item[1]):
            sub_menu = wx.Menu()
            menu_from_list(sub_menu, item[1])
            menu.Append(wx.ID_ANY, item[0], sub_menu)
        else:
            menu_item = wx.MenuItem(menu, id=wx.ID_ANY, text=item[0], kind=item_kind)
            menu.Bind(wx.EVT_MENU, lambda *_, cb=item[1]: execute_menu_item(cb, *_), id=menu_item.GetId())
            menu.Append(menu_item)

            if item_kind == TaskbarIcon.RADIO:
                if item[2]:
                    menu_item.Check()


def radio_menu(allowed_values: dict[str, Any], get_value: Callable, set_value: Callable) -> MenuList:
    def cb(k):
        set_value(allowed_values[k])
        for opt in opts:
            opt[2] = opt[0] == k

    opts = []
    current_value = get_value()
    for key, value in allowed_values.items():
        opts.append([key, lambda *_, k=key: cb(k), value == current_value])
    return [TaskbarIcon.RADIO] + opts
