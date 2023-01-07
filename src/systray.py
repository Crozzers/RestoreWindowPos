import ctypes

from infi.systray import SysTrayIcon


class SysTray(SysTrayIcon):
    def update(self, *a, menu_options=None, **kw):
        super().update(*a, **kw)

        if menu_options is not None:
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


def update_tuple(tup, index_path: list[int], new_item):
    # TODO: make menu options just a list and only convert it to give to systray
    tup = list_to_tuple(tup, to=list)

    cur = tup
    for index in index_path[:-1]:
        cur = cur[index]
    cur[index_path[-1]] = new_item

    return list_to_tuple(tup, to=tuple)
