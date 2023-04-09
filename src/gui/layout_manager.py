from copy import deepcopy
from typing import Callable
import wx
from common import Display, Snapshot
from gui.widgets import Frame, ListCtrl
import wx.lib.scrolledpanel

from snapshot import SnapshotFile, enum_display_devices


class EditDisplay(Frame):
    def __init__(self, parent, display: Display, on_save: Callable):
        self.display = display
        self.on_save = on_save

        super().__init__(
            parent, title=f'Edit Display - {display.uid}/{display.name}')

        # create widgets
        self.panel = wx.Panel(self)
        self.display_uid_label = wx.StaticText(
            self.panel, label='Display UID (regex) (leave empty to ignore)')
        self.display_uid = wx.TextCtrl(self.panel)
        self.display_name_label = wx.StaticText(
            self.panel, label='Display Name (regex) (leave empty to ignore)')
        self.display_name = wx.TextCtrl(self.panel)
        self.display_res_x_label = wx.StaticText(
            self.panel, label='X Resolution (regex) (leave empty to ignore)')
        self.display_res_x = wx.TextCtrl(self.panel)
        self.display_res_y_label = wx.StaticText(
            self.panel, label='Y Resolution (regex) (leave empty to ignore)')
        self.display_res_y = wx.TextCtrl(self.panel)
        self.save_btn = wx.Button(self.panel, label='Save')

        # bind events
        self.save_btn.Bind(wx.EVT_BUTTON, self.save)

        # place widgets
        def next_pos():
            nonlocal pos
            if pos[1] == 1:
                pos = [pos[0] + 1, 0]
            else:
                pos[1] += 1
            return tuple(pos)

        pos = [-1, 1]
        self.sizer = wx.GridBagSizer(5, 5)
        for widget in (
            self.display_uid_label, self.display_uid, self.display_name_label,
            self.display_name, self.display_res_x_label, self.display_res_x,
            self.display_res_y_label, self.display_res_y, self.save_btn
        ):
            self.sizer.Add(widget, pos=next_pos(), flag=wx.EXPAND)
        self.panel.SetSizer(self.sizer)

        # insert data
        self.display_uid.Value = display.uid
        self.display_name.Value = display.name
        self.display_res_x.Value = str(display.resolution[0])
        self.display_res_y.Value = str(display.resolution[1])

    def save(self, *_):
        self.display.uid = self.display_uid.Value
        self.display.name = self.display_name.Value
        try:
            self.display.resolution = (
                int(self.display_res_x.Value) or 0,
                int(self.display_res_y.Value) or 0
            )
        except ValueError:
            wx.MessageDialog(
                self,
                'Invalid value for display resolution. Please enter a number',
                'Error',
                style=wx.OK
            ).ShowModal()
        else:
            self.on_save()


class DisplayManager(wx.StaticBox):
    def __init__(self, parent: wx.Frame, layout: Snapshot):
        wx.StaticBox.__init__(self, parent, label=f'Displays for {layout.phony}')
        self.layout = layout
        self.displays = layout.displays

        # create action buttons
        action_panel = wx.Panel(self)
        add_display_btn = wx.Button(action_panel, label='Add')
        clone_display_btn = wx.Button(action_panel, label='Clone')
        edit_display_btn = wx.Button(action_panel, label='Edit')
        dup_display_btn = wx.Button(action_panel, label='Duplicate')
        del_display_btn = wx.Button(action_panel, label='Delete')

        # bind events
        add_display_btn.Bind(wx.EVT_BUTTON, self.add_display)
        clone_display_btn.Bind(wx.EVT_BUTTON, self.clone_display)
        edit_display_btn.Bind(wx.EVT_BUTTON, self.edit_display)
        dup_display_btn.Bind(wx.EVT_BUTTON, self.duplicate_display)
        del_display_btn.Bind(wx.EVT_BUTTON, self.delete_display)

        # position buttons
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (
            add_display_btn, clone_display_btn, edit_display_btn,
            dup_display_btn, del_display_btn
        ):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create list control
        self.list_control = ListCtrl(self, style=wx.LC_REPORT)
        # see https://stackoverflow.com/a/2413105/21226016
        self.list_control.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edit_display)
        for index, col in enumerate(('Display UID', 'Display Name', 'X Resolution', 'Y Resolution')):
            self.list_control.AppendColumn(col)
            self.list_control.SetColumnWidth(index, 300 if index < 2 else 150)

        # add rules
        for display in self.displays:
            self.append_display(display, False)

        # position list control
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(15)
        sizer.Add(action_panel, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.list_control, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

    def add_display(self, *_):
        self.append_display(Display('', '', [1920, 1080], [0, 0, 1920, 1080]))

    def append_display(self, display: Display, new=True):
        self.list_control.Append((
            display.uid or '',
            display.name or '',
            *(
                display.resolution or (1920, 1080)
            )
        ))
        if not new:
            return
        self.displays.append(display)

    def clone_display(self, *_):
        pass

    def delete_display(self, *_):
        while (item := self.list_control.GetFirstSelected()) != -1:
            self.displays.pop(item)
            self.list_control.DeleteItem(item)

    def duplicate_display(self, *_):
        for item in self.list_control.GetAllSelected():
            self.append_display(deepcopy(self.displays[item]))

    def edit_display(self, *_):
        for item in self.list_control.GetAllSelected():
            EditDisplay(self, self.displays[item],
                        on_save=self.refresh_list).Show()

    def refresh_list(self):
        self.list_control.DeleteAllItems()
        for display in self.displays:
            self.append_display(display, new=False)


class LayoutManager(wx.StaticBox):
    def __init__(self, parent: 'LayoutPage', snapshot_file: SnapshotFile):
        wx.StaticBox.__init__(self, parent, label='Layouts')
        self.snapshot_file = snapshot_file
        self.layouts = [i for i in self.snapshot_file.data if i.phony]

        # create action buttons
        action_panel = wx.Panel(self)
        add_layout_btn = wx.Button(action_panel, label='New')
        clone_layout_btn = wx.Button(action_panel, label='Clone Current')
        edit_layout_btn = wx.Button(action_panel, label='Edit')
        dup_layout_btn = wx.Button(action_panel, label='Duplicate')
        del_layout_btn = wx.Button(action_panel, label='Delete')
        mov_up_btn = wx.Button(action_panel, id=1, label='Move Up')
        mov_dn_btn = wx.Button(action_panel, id=2, label='Move Down')

        def btn_evt(func):
            return lambda *_: [func(*_), self.update_snapshot_file()]

        # bind events
        add_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.add_layout))
        clone_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.clone_layout))
        edit_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.edit_layout))
        dup_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.duplicate_layout))
        del_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.delete_layout))
        mov_up_btn.Bind(wx.EVT_BUTTON, btn_evt(self.move_layout))
        mov_dn_btn.Bind(wx.EVT_BUTTON, btn_evt(self.move_layout))

        # position buttons
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (
            add_layout_btn, clone_layout_btn, edit_layout_btn, dup_layout_btn,
            del_layout_btn, mov_up_btn, mov_dn_btn
        ):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create list control
        self.list_control = ListCtrl(self, style=wx.LC_REPORT | wx.LC_EDIT_LABELS)
        self.list_control.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edit_layout)
        for index, col in enumerate(('Layout Name',)):
            self.list_control.AppendColumn(col)
            self.list_control.SetColumnWidth(index, 600 if index < 3 else 150)

        # add rules
        for layout in self.layouts:
            self.append_layout(layout, False)

        # position list control
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.AddSpacer(15)
        sizer.Add(action_panel, 0, wx.ALL | wx.EXPAND, 0)
        sizer.Add(self.list_control, 1, wx.ALL | wx.EXPAND, 5)
        self.SetSizer(sizer)

    def add_layout(self, *_):
        self.append_layout(
            Snapshot(displays=enum_display_devices(), phony='Unnamed Layout'))

    def append_layout(self, layout: Snapshot, new=True):
        self.list_control.Append((layout.phony or 'Unnamed Layout',))
        if not new:
            return
        self.layouts.append(layout)
        self.update_snapshot_file()

    def clone_layout(self, *_):
        layout = deepcopy(self.snapshot_file.get_current_snapshot())
        layout.history = []
        layout.phony = 'Unnamed Layout'
        layout.mru = None
        self.append_layout(layout)

    def delete_layout(self, *_):
        while (item := self.list_control.GetFirstSelected()) != -1:
            self.layouts.pop(item)
            self.list_control.DeleteItem(item)

    def duplicate_layout(self, *_):
        for item in self.list_control.GetAllSelected():
            self.append_layout(deepcopy(self.layouts[item]))

    def edit_layout(self, *_):
        item = self.list_control.GetFirstSelected()
        self.Parent.swap_layout(self.layouts[item])

    def insert_layout(self, index: int, layout: Snapshot):
        self.list_control.Insert(index, (layout.phony or 'Unnamed Layout',))

    def move_layout(self, btn_evt: wx.Event):
        direction = -1 if btn_evt.Id == 1 else 1
        selected = list(self.list_control.GetAllSelected())
        items: list[tuple[int, Snapshot]] = []

        # get all items and their new positions
        for index in reversed(selected):
            self.list_control.DeleteItem(index)
            items.insert(0, (max(0, index + direction),
                         self.layouts.pop(index)))

        # re-insert into list
        for new_index, rule in items:
            self.layouts.insert(new_index, rule)
            self.insert_layout(new_index, rule)
            self.list_control.Select(new_index)

    def update_snapshot_file(self):
        with self.snapshot_file.lock:
            to_remove = []

            for layout in self.snapshot_file.data:
                if not layout.phony:
                    continue
                if layout not in self.layouts:
                    to_remove.append(layout)

            for layout in to_remove:
                while layout in self.snapshot_file.data:
                    self.snapshot_file.data.remove(layout)

            for layout in self.layouts:
                if layout not in self.snapshot_file.data:
                    self.snapshot_file.data.append(layout)

            self.snapshot_file.save()


class LayoutPage(wx.Panel):
    def __init__(self, parent: wx.Frame, snapshot_file: SnapshotFile):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.snapshot = snapshot_file

        self.layout_manager = LayoutManager(self, snapshot_file)
        self.display_manager = DisplayManager(
            self, next(i for i in snapshot_file.data if i.phony))

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.layout_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.sizer.Add(self.display_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(self.sizer)

    def swap_layout(self, layout: Snapshot):
        self.sizer.Remove(1)
        self.display_manager.Destroy()
        self.display_manager = DisplayManager(self, layout)
        self.sizer.Add(self.display_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.sizer.Layout()
