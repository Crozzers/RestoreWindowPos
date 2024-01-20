import logging
import os
import signal
import time

import psutil
import win32con
import win32gui

from common import Window, XandY, load_json, local_path, single_call
from device import DeviceChangeCallback, DeviceChangeService
from gui import TaskbarIcon, WxApp, about_dialog, radio_menu
from gui.wx_app import spawn_gui
from services import ServiceCallback
from snapshot import SnapshotFile, SnapshotService
from window import WindowSpawnService, apply_rules, is_window_valid, restore_snapshot


class LoggingFilter(logging.Filter):
    def filter(self, record):
        try:
            return not (
                # sometimes the record has msg, sometimes its message. Just try to catch all of them
                'Release ' in getattr(record, 'message', getattr(record, 'msg', '')) and record.name == 'comtypes'
            )
        except Exception:
            # sometimes (rarely) record doesn't have a `message` attr
            return True


def update_systray_options():
    global menu_options

    if SETTINGS.get('pause_snapshots', False):
        menu_options[1][0] = 'Resume snapshots'
    else:
        menu_options[1][0] = 'Pause snapshots'

    history_menu = []
    for config in snap.get_current_snapshot().history:
        timestamp = config.time
        label = time.strftime('%b %d %H:%M:%S', time.localtime(timestamp))
        history_menu.append([label, lambda *_, t=timestamp: snap.restore(t)])

    if history_menu:
        history_menu.insert(0, TaskbarIcon.SEPARATOR)
        history_menu.insert(0, ['Clear history', lambda *_: clear_restore_options()])

    menu_options[2][1][:-2] = history_menu

    current_snapshot = snap.get_current_snapshot()
    layout_menu = []
    for snapshot in snap.data:
        if not snapshot.phony:
            continue
        layout_menu.append([snapshot.phony, lambda *_, s=snapshot: restore_snapshot([], s.rules)])
    menu_options[7][1][1:] = layout_menu

    rule_menu = []
    for header, ruleset in (
        ('Current Snapshot', current_snapshot.rules),
        ('All Compatible', snap.get_rules(compatible_with=True, exclusive=True)),
    ):
        if not ruleset:
            continue
        rule_menu.extend([TaskbarIcon.SEPARATOR, [header]])
        for rule in ruleset:
            rule_menu.append([rule.rule_name or 'Unnamed Rule', lambda *_, r=rule: restore_snapshot([], [r])])
    menu_options[8][1][:-2] = rule_menu


def clear_restore_options():
    result = win32gui.MessageBox(
        None,
        'Are you sure you want to clear the snapshot history for this display configuration?',
        'Clear snapshot history?',
        win32con.MB_YESNO | win32con.MB_ICONWARNING,
    )
    if result == win32con.IDYES:
        snap.get_current_snapshot().history.clear()


def rescue_windows(snap: SnapshotFile):
    def callback(hwnd, _):
        if not is_window_valid(hwnd):
            return
        window = Window.from_hwnd(hwnd)
        if not window.fits_display_config(displays):
            rect = [0, 0, *window.size]
            logging.info(f'rescue window {window.name!r} {window.rect} -> {rect}')
            window.move((0, 0))

    displays = snap.get_current_snapshot().displays
    win32gui.EnumWindows(callback, None)


def on_window_spawn(windows: list[Window]):
    on_spawn_settings = SETTINGS.get('on_window_spawn', {})
    if not on_spawn_settings or not on_spawn_settings.get('enabled', False):
        return
    # sleep to make sure window is fully initialised with resizability info
    time.sleep(0.05)
    current_snap = snap.get_current_snapshot()
    rules = snap.get_rules(compatible_with=True, exclusive=True)
    ignore_children = on_spawn_settings.get('ignore_children', True)
    match_resizability = on_spawn_settings.get('match_resizability', True)
    fuzzy_mtm = on_spawn_settings.get('fuzzy_mtm', True)

    # get all the operations and the order we run them
    operations = {
        k: on_spawn_settings.get(k, True)
        for k in on_spawn_settings.get('operation_order', ['apply_lkp', 'apply_rules', 'move_to_mouse'])
    }

    def lkp(window: Window) -> bool:
        last_instance = current_snap.last_known_process_instance(
            window, match_title=True, match_resizability=match_resizability
        )
        if not last_instance:
            return False
        log.info(f'apply LKP: {window} -> {last_instance}')

        # if the last known process instance was minimised then we need to override the placement here
        rect = last_instance.rect
        placement = last_instance.placement
        if placement[1] == win32con.SW_SHOWMINIMIZED:
            show_cmd = win32con.SW_SHOWNORMAL
            if placement[0] == win32con.WPF_RESTORETOMAXIMIZED:
                show_cmd = win32con.SW_SHOWMAXIMIZED
            rect = placement[4]
            placement = (placement[0], show_cmd, (-1, -1), (-1, -1), placement[4])

        window.set_pos(rect, placement)
        return True

    def mtm(window: Window) -> bool:
        cursor_pos: XandY = win32gui.GetCursorPos()
        if fuzzy_mtm:
            # if cursor X between window X and X1, and cursor Y between window Y and Y1
            if window.rect[0] <= cursor_pos[0] <= window.rect[2] and window.rect[1] <= cursor_pos[1] <= window.rect[3]:
                return True
        window.center_on(cursor_pos)
        return True

    for window in windows:
        if window.parent is not None and ignore_children:
            continue
        for op_name, state in operations.items():
            if not state:
                continue
            if op_name == 'apply_lkp' and lkp(window):
                break
            elif op_name == 'move_to_mouse' and mtm(window):
                break
            elif op_name == 'apply_rules' and apply_rules(rules, window):
                break

    capture_snapshot = on_spawn_settings.get('capture_snapshot', 2)
    if capture_snapshot == 2:
        # these are all newly spawned windows so we don't have to worry about merging them into the history
        current_snap.history[-1].windows.extend(windows)
    elif capture_snapshot == 1:
        snap.update()


@single_call
def shutdown(*_):
    log.info('begin shutdown process')
    app.ExitMainLoop()
    monitor_thread.stop()
    snapshot_service.stop()
    log.debug('destroy WxApp')
    app.Destroy()
    log.info('save snapshot before shutting down')
    snap.save()
    log.info('end shutdown process')


if __name__ == '__main__':
    logging.basicConfig(
        filename=local_path('log.txt'), filemode='w', format='%(asctime)s:%(levelname)s:%(name)s:%(message)s'
    )
    # filter the excessive comtypes logs
    logging.getLogger('comtypes').addFilter(LoggingFilter())
    log = logging.getLogger(__name__)
    log.info('start')

    SETTINGS = load_json('settings')
    SETTINGS.set('pause_snapshots', False)  # reset this key

    logging.getLogger().setLevel(logging.getLevelName(SETTINGS.get('log_level', 'INFO').upper()))

    snap = SnapshotFile()
    app = WxApp()

    menu_options = [
        ['Capture now', lambda *_: snap.update()],
        ['Pause snapshots', lambda *_: SETTINGS.set('pause_snapshots', not SETTINGS.get('pause_snapshots', False))],
        ['Restore snapshot', [TaskbarIcon.SEPARATOR, ['Most recent', lambda *_: snap.restore(-1)]]],
        ['Rescue windows', lambda *_: rescue_windows(snap)],
        TaskbarIcon.SEPARATOR,
        [
            'Snapshot frequency',
            radio_menu(
                {
                    '5 seconds': 5,
                    '10 seconds': 10,
                    '30 seconds': 30,
                    '1 minute': 60,
                    '5 minutes': 300,
                    '10 minutes': 600,
                    '30 minutes': 1800,
                    '1 hour': 3600,
                },
                lambda: SETTINGS.get('snapshot_freq', 60),
                lambda v: SETTINGS.set('snapshot_freq', v),
            ),
        ],
        TaskbarIcon.SEPARATOR,
        ['Apply layout', [['Current Snapshot', lambda *_: restore_snapshot([], snap.get_rules())]]],
        [
            'Apply rules',
            [
                TaskbarIcon.SEPARATOR,
                ['Apply all', lambda *_: restore_snapshot([], snap.get_rules(compatible_with=True))],
            ],
        ],
        ['Configure rules', lambda *_: spawn_gui(snap, 'rules')],
        TaskbarIcon.SEPARATOR,
        ['Settings', lambda *_: spawn_gui(snap, 'settings')],
        ['About', lambda *_: about_dialog()],
    ]

    # register termination signals so we can do graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT, signal.SIGABRT):
        signal.signal(sig, shutdown)

    # detect if we are running as a single exe file (pyinstaller --onefile mode)
    current_process = psutil.Process(os.getpid())
    log.debug(f'PID: {current_process.pid}')
    parent_process = current_process.parent()
    if (
        parent_process is not None
        and current_process.exe() == parent_process.exe()
        and current_process.name() == parent_process.name()
    ):
        log.debug(f'parent detected. PPID: {parent_process.pid}')
        app.enable_sigterm(parent_process)

    with TaskbarIcon(menu_options, on_click=update_systray_options, on_exit=shutdown):
        monitor_thread = DeviceChangeService(DeviceChangeCallback(snap.restore, shutdown, snap.update), snap.lock)
        monitor_thread.start()
        window_spawn_thread = WindowSpawnService(ServiceCallback(on_window_spawn))
        window_spawn_thread.start()
        snapshot_service = SnapshotService(None)
        snapshot_service.start(args=(snap,))

        try:
            app.MainLoop()
        except KeyboardInterrupt:
            pass
        finally:
            log.info('app mainloop closed')
            shutdown()
    log.debug('fin')
