from copy import deepcopy

import wx
import wx.lib.scrolledpanel

from common import Display, Snapshot
from gui.widgets import EditableListCtrl, ListCtrl
from snapshot import SnapshotFile, enum_display_devices


class DisplayManager(wx.StaticBox):
    def __init__(self, parent: wx.Frame, layout: Snapshot):
        wx.StaticBox.__init__(
            self, parent, label=f'Displays for {layout.phony}')
        self.layout = layout
        self.displays = layout.displays

        # create action buttons
        action_panel = wx.Panel(self)
        add_display_btn = wx.Button(action_panel, label='Add')
        clone_display_btn = wx.Button(action_panel, label='Clone')
        dup_display_btn = wx.Button(action_panel, label='Duplicate')
        del_display_btn = wx.Button(action_panel, label='Delete')

        # bind events
        add_display_btn.Bind(wx.EVT_BUTTON, self.add_display)
        clone_display_btn.Bind(wx.EVT_BUTTON, self.clone_display)
        dup_display_btn.Bind(wx.EVT_BUTTON, self.duplicate_display)
        del_display_btn.Bind(wx.EVT_BUTTON, self.delete_display)

        # position buttons
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (
            add_display_btn, clone_display_btn,
            dup_display_btn, del_display_btn
        ):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create list control
        self.list_control = EditableListCtrl(self)
        self.list_control.Bind(wx.EVT_TEXT_ENTER, self.edit_display)
        for index, col in enumerate(
            ('Display UID (regex)', 'Display Name (regex)', 'X Resolution', 'Y Resolution')
        ):
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

    def edit_display(self, evt: wx.Event):
        def update():
            for index, display in enumerate(self.displays):
                try:
                    display.resolution = (
                        int(self.list_control.GetItemText(index, 2)),
                        int(self.list_control.GetItemText(index, 3))
                    )
                    display.uid = self.list_control.GetItemText(index, 0)
                    display.name = self.list_control.GetItemText(index, 1)
                except ValueError:
                    wx.MessageDialog(
                        self,
                        'Invalid value for display resolution. Please enter a valid integer',
                        'Error',
                        style=wx.OK
                    ).ShowModal()
                else:
                    wx.CallAfter(self.refresh_list)

        evt.Skip()
        wx.CallAfter(update)

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
        rename_btn = wx.Button(action_panel, id=3, label='Rename')

        def btn_evt(func, swap=True):
            wrapped = lambda *_: [func(*_), self.update_snapshot_file()]  # noqa: E731
            if swap:
                return lambda *_: [wrapped(*_), self.edit_layout()]
            return wrapped

        # bind events
        add_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.add_layout))
        clone_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.clone_layout))
        edit_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.edit_layout, False))
        dup_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.duplicate_layout))
        del_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.delete_layout))
        mov_up_btn.Bind(wx.EVT_BUTTON, btn_evt(self.move_layout, False))
        mov_dn_btn.Bind(wx.EVT_BUTTON, btn_evt(self.move_layout, False))
        # not btn_evt since no data changes yet
        rename_btn.Bind(wx.EVT_BUTTON, self.rename_layout)

        # position buttons
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for btn in (
            add_layout_btn, clone_layout_btn, edit_layout_btn, dup_layout_btn,
            del_layout_btn, mov_up_btn, mov_dn_btn, rename_btn
        ):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create list control
        self.list_control = ListCtrl(
            self, style=wx.LC_REPORT | wx.LC_EDIT_LABELS)
        self.list_control.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edit_layout)
        self.list_control.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.rename_layout)
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
        layout = Snapshot(displays=enum_display_devices(),
                          phony='Unnamed Layout')
        self.append_layout(layout)

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
        try:
            layout = self.layouts[item]
        except IndexError:
            layout = None
        self.Parent.swap_layout(layout)

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

    def rename_layout(self, evt: wx.Event):
        def update():
            for index, layout in enumerate(self.layouts):
                layout.phony = self.list_control.GetItemText(index)
            self.update_snapshot_file()
            self.edit_layout()

        if evt.Id == 3:
            self.list_control.EditLabel(self.list_control.GetFirstSelected())
        else:
            # use CallAfter to allow ListCtrl to update the value before we read it
            wx.CallAfter(update)

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
        self.display_manager = None

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.layout_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(self.sizer)

        self.swap_layout()

    def swap_layout(self, layout: Snapshot = None):
        if self.sizer.GetItemCount() > 1:
            self.sizer.Remove(1)
            self.display_manager.Destroy()

        if layout is None:
            try:
                with self.snapshot.lock:
                    layout = next(i for i in reversed(
                        self.snapshot.data) if i.phony)
            except StopIteration:
                return

        self.display_manager = DisplayManager(self, layout)
        self.sizer.Add(self.display_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.sizer.Layout()
