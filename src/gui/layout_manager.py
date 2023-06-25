from copy import deepcopy
from typing import Callable

import wx
import wx.lib.scrolledpanel

from common import Display, Snapshot
from gui.rule_manager import RuleSubsetManager
from gui.widgets import EditableListCtrl, Frame, ListCtrl, SelectionWindow
from snapshot import SnapshotFile, enum_display_devices
from window import restore_snapshot


class EditResolutionWindow(Frame):
    def __init__(self, parent, display: Display, callback: Callable, **kw):
        super().__init__(parent, title='Edit Resolution', **kw)
        self.display = display
        self.callback = callback

        display.comparison_params.setdefault('resolution', ['eq', 'eq'])
        self.selected_ops = display.comparison_params['resolution'].copy()

        sizer = wx.GridBagSizer(5, 5)

        sizer.Add(wx.StaticText(self, label='X Resolution'), (0, 1))
        sizer.Add(wx.StaticText(self, label='Y Resolution'), (0, 2))
        sizer.Add(wx.StaticText(
            self, label='Value (set to 0 to ignore):'), (1, 0))

        max_res = 10 ** 4
        self.x_res_ctrl = wx.SpinCtrlDouble(
            self, value=str(display.resolution[0]), min=-max_res, max=max_res)
        sizer.Add(self.x_res_ctrl, (1, 1))
        self.y_res_ctrl = wx.SpinCtrlDouble(
            self, value=str(display.resolution[1]), min=-max_res, max=max_res)
        sizer.Add(self.y_res_ctrl, (1, 2))

        self.operations = {
            'gt': 'Greater than (>)',
            'ge': 'Greater than or equal (>=)',
            'eq': 'Equal to (==)',
            'le': 'Less than or equal to (<=)',
            'lt': 'Less than'
        }
        sizer.Add(wx.StaticText(self, label='Match when:'),
                  (round(len(self.operations) / 2) + 2, 0))

        count = 1
        for index in range(len(display.resolution)):
            row = 2
            kw = {'style': wx.RB_GROUP}
            for op_name, op_desc in self.operations.items():
                w = wx.RadioButton(self, label=op_desc, id=count, **kw)
                sizer.Add(w, (row, index + 1))
                w.Bind(wx.EVT_RADIOBUTTON, self.select_op)
                if display.comparison_params['resolution'][index] == op_name:
                    w.SetValue(True)

                count += 1
                row += 1
                kw = {}

        save = wx.Button(self, label='Save')
        sizer.Add(save, (row, 0))
        save.Bind(wx.EVT_BUTTON, self.save)

        self.SetSizerAndFit(sizer)

    def save(self, *_):
        self.display.resolution = (
            int(self.x_res_ctrl.Value), int(self.y_res_ctrl.Value))
        self.display.comparison_params['resolution'] = self.selected_ops

        self.callback()
        self.Close()

    def select_op(self, evt: wx.Event):
        plane = evt.Id // len(self.operations)
        index = evt.Id - 1
        if plane:
            index -= len(self.operations)
        self.selected_ops[plane] = tuple(self.operations.keys())[index]


class DisplayManager(wx.StaticBox):
    def __init__(self, parent: wx.Frame, layout: Snapshot, **kwargs):
        wx.StaticBox.__init__(self, parent, **kwargs)
        self.layout = layout
        self.displays = layout.displays

        # create action buttons
        action_panel = wx.Panel(self)
        add_display_btn = wx.Button(action_panel, label='Add')
        clone_display_btn = wx.Button(action_panel, label='Clone')
        dup_display_btn = wx.Button(action_panel, label='Duplicate')
        del_display_btn = wx.Button(action_panel, label='Delete')
        mode_txt = wx.StaticText(action_panel, label='Match:')
        mode_opt = wx.Choice(action_panel, choices=('All', 'Any'))

        # bind events
        add_display_btn.Bind(wx.EVT_BUTTON, self.add_display)
        clone_display_btn.Bind(wx.EVT_BUTTON, self.clone_display)
        dup_display_btn.Bind(wx.EVT_BUTTON, self.duplicate_display)
        del_display_btn.Bind(wx.EVT_BUTTON, self.delete_display)
        mode_opt.Bind(wx.EVT_CHOICE, self.select_mode)

        # position widgets
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for widget in (
            add_display_btn, clone_display_btn, dup_display_btn,
            del_display_btn, mode_txt, mode_opt
        ):
            action_sizer.Add(widget, 0, wx.ALL | wx.CENTER, 5)
        action_panel.SetSizer(action_sizer)

        # set widget states
        mode_opt.SetSelection(0 if layout.comparison_params.get('displays') == 'all' else 1)

        # create list control
        self.list_control = EditableListCtrl(
            self, edit_cols=list(range(0, 4)), on_edit=self.on_edit)
        self.list_control.Bind(wx.EVT_TEXT_ENTER, self.edit_display)
        for index, col in enumerate(
            ('Display UID (regex)', 'Display Name (regex)',
             'X Resolution', 'Y Resolution', 'Rect')
        ):
            self.list_control.AppendColumn(col)
            self.list_control.SetColumnWidth(index, 250 if index < 2 else 125)

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
            ),
            str(display.rect)
        ))
        if not new:
            return
        self.displays.append(display)

    def clone_display(self, *_):
        displays = enum_display_devices()
        d_names = [i.name for i in displays]
        options = {'Clone UIDs': True, 'Clone Names': True}

        def on_select(selection, options):
            for index in selection:
                display: Display = deepcopy(displays[index])
                if not options['Clone UIDs']:
                    display.uid = None
                if not options['Clone Names']:
                    display.name = None
                self.displays.append(display)
            self.refresh_list()

        SelectionWindow(self, d_names, on_select, options,
                        title='Clone Displays').Show()

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
        update()

    def on_edit(self, col, row) -> bool:
        if col < 2:
            return True
        if col > 4:
            return False

        display: Display = self.displays[row]
        w_name = f'editdisplay-{id(display)}'
        for child in self.GetChildren():
            if not isinstance(child, Frame):
                continue
            if child.GetName() == w_name:
                return child.Raise()
        EditResolutionWindow(self, display, callback=self.refresh_list, name=w_name).Show()

    def refresh_list(self):
        self.list_control.DeleteAllItems()
        for display in self.displays:
            self.append_display(display, new=False)

    def select_mode(self, evt: wx.CommandEvent):
        choice = 'any' if evt.GetSelection() == 1 else 'all'
        self.layout.comparison_params['display'] = choice


class LayoutManager(wx.StaticBox):
    def __init__(self, parent: 'LayoutPage', snapshot_file: SnapshotFile):
        wx.StaticBox.__init__(self, parent, label='Layouts')
        self.snapshot_file = snapshot_file
        self.layouts = [snapshot_file.get_current_snapshot()]
        for layout in self.snapshot_file.data:
            if not layout.phony:
                continue
            if layout.phony == 'Global' and layout.displays == []:
                self.layouts.insert(1, layout)
            else:
                self.layouts.append(layout)

        # create action buttons
        action_panel = wx.Panel(self)
        add_layout_btn = wx.Button(action_panel, label='Add New')
        apply_layout_btn = wx.Button(action_panel, label='Apply')
        clone_layout_btn = wx.Button(action_panel, label='Clone Current')
        edit_layout_btn = wx.Button(action_panel, label='Edit')
        dup_layout_btn = wx.Button(action_panel, label='Duplicate')
        del_layout_btn = wx.Button(action_panel, label='Delete')
        mov_up_btn = wx.Button(action_panel, id=1, label='Move Up')
        mov_dn_btn = wx.Button(action_panel, id=2, label='Move Down')
        rename_btn = wx.Button(action_panel, id=3, label='Rename')

        self._disallow_current = (
            edit_layout_btn, del_layout_btn, mov_up_btn, mov_dn_btn, rename_btn)

        def btn_evt(func, swap=True):
            wrapped = lambda *_: [func(*_), self.update_snapshot_file()]  # noqa: E731
            if swap:
                return lambda *_: [wrapped(*_), self.edit_layout()]
            return wrapped

        # bind events
        add_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.add_layout))
        apply_layout_btn.Bind(wx.EVT_BUTTON, btn_evt(self.apply_layout))
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
            add_layout_btn, apply_layout_btn, clone_layout_btn, edit_layout_btn,
            dup_layout_btn, del_layout_btn, mov_up_btn, mov_dn_btn, rename_btn
        ):
            action_sizer.Add(btn, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create list control
        self.list_control = ListCtrl(
            self, style=wx.LC_REPORT | wx.LC_EDIT_LABELS)
        self.list_control.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.edit_layout)
        self.list_control.Bind(wx.EVT_LIST_END_LABEL_EDIT, self.rename_layout)
        self.list_control.Bind(wx.EVT_LIST_ITEM_SELECTED, self.on_select)
        self.list_control.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.on_select)
        for index, col in enumerate(('Layout Name',)):
            self.list_control.AppendColumn(col)
            self.list_control.SetColumnWidth(index, 600 if index < 3 else 150)

        # add layouts
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
        if layout == self.layouts[0]:
            name = 'Current Snapshot'
        else:
            name = layout.phony
        self.list_control.Append((name,))
        if not new:
            return
        self.layouts.append(layout)
        self.update_snapshot_file()

    def apply_layout(self, *_):
        for item in self.list_control.GetAllSelected():
            layout: Snapshot = self.layouts[item]
            restore_snapshot([], layout.rules)

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
        self.list_control.Insert(index, (layout.phony,))

    def move_layout(self, btn_evt: wx.Event):
        direction = -1 if btn_evt.Id == 1 else 1
        selected = list(self.list_control.GetAllSelected())
        items: list[tuple[int, Snapshot]] = []

        # get all items and their new positions
        for index in reversed(selected):
            self.list_control.DeleteItem(index)
            items.insert(0, (max(2, index + direction),
                         self.layouts.pop(index)))

        # re-insert into list
        for new_index, rule in items:
            self.layouts.insert(new_index, rule)
            self.insert_layout(new_index, rule)
            self.list_control.Select(new_index)

    def on_select(self, evt: wx.Event):
        selected = tuple(self.list_control.GetAllSelected())
        if 0 in selected or 1 in selected:
            func = wx.Button.Disable
        else:
            func = wx.Button.Enable
        for widget in self._disallow_current:
            func(widget)

    def rename_layout(self, evt: wx.Event):
        def update():
            self.list_control.SetItemText(0, 'Current Snapshot')
            self.list_control.SetItemText(1, 'Global')
            for index, layout in enumerate(self.layouts[2:], start=2):
                text = self.list_control.GetItemText(index)
                if text == 'Global':
                    self.list_control.SetItemText(index, layout.phony or 'Unnamed Layout')
                    wx.MessageBox(
                        'Name "Global" is not allowed for user created layouts',
                        'Invalid Value',
                        wx.OK | wx.ICON_WARNING
                    )
                else:
                    layout.phony = text
                if not layout.phony:
                    layout.phony = 'Unnamed Layout'
                    self.list_control.SetItemText(index, 'Unnamed Layout')
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
                to_remove.append(layout)

            for layout in to_remove:
                while layout in self.snapshot_file.data:
                    self.snapshot_file.data.remove(layout)

            self.snapshot_file.data.extend(self.layouts[1:])

            self.snapshot_file.save()


class LayoutPage(wx.Panel):
    def __init__(self, parent: wx.Frame, snapshot_file: SnapshotFile):
        wx.Panel.__init__(self, parent, id=wx.ID_ANY)
        self.snapshot = snapshot_file

        self.layout_manager = LayoutManager(self, snapshot_file)
        self.display_manager = None
        self.rule_manager = None

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.layout_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.SetSizer(self.sizer)

        self.swap_layout()

    def swap_layout(self, layout: Snapshot = None):
        if self.sizer.GetItemCount() > 1:
            self.sizer.Remove(2)
            self.sizer.Remove(1)
            self.display_manager.Destroy()
            self.rule_manager.Destroy()

        if layout is None:
            try:
                with self.snapshot.lock:
                    layout = next(i for i in reversed(
                        self.snapshot.data) if i.phony)
            except StopIteration:
                return

        current = self.snapshot.get_current_snapshot()
        if layout == current:
            name = 'Current Snapshot'
        else:
            name = layout.phony

        self.display_manager = DisplayManager(
            self, layout, label=f'Displays for {name}')

        if layout == current or (layout.phony == 'Global' and layout.displays == []):
            self.display_manager.Disable()

        self.rule_manager = RuleSubsetManager(
            self, self.snapshot, layout.rules, f'Rules for {name}')
        self.sizer.Add(self.display_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.sizer.Add(self.rule_manager, 0, wx.ALL | wx.EXPAND, 0)
        self.sizer.Layout()
