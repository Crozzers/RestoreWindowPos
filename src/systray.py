import ctypes

from infi.systray import SysTrayIcon

from common import format_unit


class SysTray(SysTrayIcon):
    def __init__(self, *a, menu_options=None, **kw):
        self.menu_options_orig = menu_options
        super().__init__(*a, menu_options=list_to_tuple(menu_options), **kw)

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


def list_to_tuple(item, to=tuple):
    if isinstance(item, (tuple, list)):
        item = to(list_to_tuple(sub, to=to) for sub in item)
    return item


def submenu_from_settings(settings, key, label_unit, allowed_values):
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
        if val == settings.get(key):
            label += ' [current]'
        opts.append([label, None, lambda s, i=index, v=val: cb(s, opts, i, v)])
    return opts
