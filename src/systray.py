import ctypes
import logging

import win32con
from infi.systray import SysTrayIcon

from common import format_unit, tuple_convert


class SysTray(SysTrayIcon):
    def __init__(self, *a, menu_options=None, on_click=None, **kw):
        self.log = logging.getLogger(__name__).getChild(
            self.__class__.__name__).getChild(str(id(self)))
        self.on_click = on_click
        self.menu_options_orig = menu_options
        super().__init__(*a, menu_options=list_to_tuple(menu_options), **kw)

    def _show_menu(self):
        if callable(self.on_click):
            self.on_click(self)
        return super()._show_menu()

    def update(self, *a, menu_options=None, **kw):
        super().update(*a, **kw)

        if menu_options is not None:
            if menu_options is True:
                menu_options = self.menu_options_orig

            menu_options = list_to_tuple(menu_options)
            menu_options += (('Quit', None, SysTrayIcon.QUIT),)
            self._next_action_id = SysTrayIcon.FIRST_ID
            self._menu_actions_by_id = set()
            self._menu_options = self._add_ids_to_menu_options(
                list(menu_options))
            self._menu_actions_by_id = dict(self._menu_actions_by_id)
            ctypes.windll.user32.DestroyMenu(self._menu)
            self._menu = None

    def _execute_menu_option(self, id):
        try:
            return super()._execute_menu_option(id)
        except Exception as e:
            self.log.exception(f'failed to execute menu command {id}')
            caption = f'Failed to execute system tray menu command\n{type(e).__name__}: {e}'
            ctypes.windll.user32.MessageBoxW(
                0, caption, 'RestoreWindowPos', win32con.MB_ICONERROR)
            raise


def list_to_tuple(item):
    return tuple_convert(item, to=tuple, from_=list)


def submenu_from_settings(settings, key, default, label_unit, allowed_values):
    def cb(systray, options, index, value):
        settings.set(key, value)
        for i, opt in enumerate(options):
            if i == index and '[current]' not in opt[0]:
                opt[0] += ' [current]'
            elif i != index and '[current]' in opt[0]:
                opt[0] = opt[0].replace(' [current]', '')
        systray.update(menu_options=True)

    opts = []
    for index, val in enumerate(allowed_values):
        label = format_unit(label_unit, val)
        if val == settings.get(key, default):
            label += ' [current]'
        opts.append([label, None, lambda s, i=index, v=val: cb(s, opts, i, v)])
    return opts
