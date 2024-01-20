from collections.abc import Callable, Iterable, Mapping, Sequence
from typing import Optional

import wx
from wx.lib.mixins.listctrl import TextEditMixin
from wx.lib.newevent import NewEvent

from common import local_path


class Frame(wx.Frame):
    def __init__(self, parent=None, title=None, **kwargs):
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY, **kwargs)
        self.SetTitle(title)
        self.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENU))
        self.SetIcon(wx.Icon(local_path('assets/icon32.ico', asset=True)))

    def GetIdealSize(self):
        x = 480
        y = 360
        for child in self.GetChildren():
            if hasattr(child, 'GetBestVirtualSize'):
                vsize = child.GetBestVirtualSize()
                x = max(x, vsize.x)
                y = max(y, vsize.y)
        return wx.Size(x + 10, y + 10)

    def SetIdealSize(self):
        self.SetSize(self.GetIdealSize())

    def SetTitle(self, title):
        if title is None:
            title = 'RestoreWindowPos'
        else:
            title = f'{title} - RestoreWindowPos'
        return super().SetTitle(title)


class ListCtrl(wx.ListCtrl):
    def __init__(self, parent, *args, **kwargs):
        kwargs.setdefault('style', wx.LC_REPORT)
        wx.ListCtrl.__init__(self, parent, *args, **kwargs)

    def GetAllSelected(self):
        pos = self.GetFirstSelected()
        if pos == -1:
            return
        yield pos
        while (item := self.GetNextSelected(pos)) != -1:
            yield item
            pos = item

    def Insert(self, index: int, entry):
        pos = self.InsertItem(index, entry[0])
        for i in range(1, len(entry)):
            self.SetItem(pos, i, entry[i])

    def ScrollList(self, dx, dy):
        return super().ScrollList(int(dx), int(dy))


class EditableListCtrl(ListCtrl, TextEditMixin):
    def __init__(
        self,
        parent,
        *args,
        edit_cols: Optional[list[int]] = None,
        on_edit: Optional[Callable[[int, int], bool]] = None,
        post_edit: Optional[Callable[[int, int], None]] = None,
        **kwargs,
    ):
        """
        Args:
            parent: parent widget
            *args: passed to `ListCtrl.__init__`
            edit_cols: columns to allow editing in, zero based
            on_edit: callback for when editing starts. Takes column and row
                being edited as params. Boolean return determines whether to
                allow that cell to be edited
            post_edit: callback for once editing has been completed. Takes
                column and row as params.
            **kwargs: passed to `ListCtrl.__init__`
        """
        kwargs.setdefault('style', wx.LC_REPORT | wx.LC_EDIT_LABELS)
        ListCtrl.__init__(self, parent, *args, **kwargs)
        TextEditMixin.__init__(self)
        self.Bind(wx.EVT_LEFT_DCLICK, self._on_double_click)
        self.edit_cols = edit_cols
        self.on_edit = on_edit
        self.post_edit = post_edit

    def _on_double_click(self, evt: wx.Event):
        handler: wx.EvtHandler = self.GetEventHandler()
        handler.ProcessEvent(wx.PyCommandEvent(wx.EVT_LIST_ITEM_ACTIVATED.typeId, self.GetId()))
        evt.Skip()

    def CloseEditor(self, evt=None):
        if not self.editor.IsShown():
            return
        super().CloseEditor(evt)

        if callable(self.post_edit):
            self.post_edit(self.curCol, self.curRow)

    def OnChar(self, event: wx.KeyEvent):
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_ESCAPE:
            self.editor.Hide()
        else:
            super().OnChar(event)

    def OpenEditor(self, col, row):
        if self.on_edit is not None:
            if not self.on_edit(col, row):
                self.Select(row)
                return

        if self.edit_cols is not None:
            if col not in self.edit_cols:
                self.Select(row)
                return

        super().OpenEditor(col, row)
        if not self.editor.IsShown():
            # editor is activated using `CallAfter` but after closing
            # and re-opening the window, this event is never fired.
            # This hack copies internal code of the TextEditMixin to
            # force the editor to open
            x0 = self.col_locs[col]
            x1 = self.col_locs[col + 1] - x0
            y0 = self.GetItemRect(row)[1]

            scrolloffset = self.GetScrollPos(wx.HORIZONTAL)
            self.editor.SetSize(x0 - scrolloffset, y0, x1, -1, wx.SIZE_USE_EXISTING)
            self.editor.SetValue(self.GetItem(row, col).GetText())
            self.editor.Show()
            self.editor.Raise()
            self.editor.SetSelection(-1, -1)
            self.editor.SetFocus()


RearrangeListSelect, EVT_REARRANGE_LIST_SELECT = NewEvent()


class RearrangeListCtrl(wx.Panel):
    def __init__(self, parent, options: Mapping[str, bool], order: Sequence[str], label_mapping: Mapping[str, str]):
        """
        Args:
            parent: parent widget
            options: mapping of programmatic name -> enabled/disabled
            order: ordered list of the programmatic option names
            label_mapping: mapping of friendly name -> programmatic name
        """
        wx.Panel.__init__(self, parent)

        self.__labels = label_mapping
        self.rearrange_list = wx.RearrangeList(
            self, items=list(label_mapping.keys()), order=[list(label_mapping.values()).index(i) for i in order]
        )
        self.up_btn = wx.Button(self, label='Up')
        self.down_btn = wx.Button(self, label='Down')

        # set state
        self.rearrange_list.SetCheckedItems([order.index(opt) for opt, state in options.items() if state])

        self.rearrange_list.Bind(wx.EVT_CHECKLISTBOX, lambda *_: self.OnSelectionChange())
        self.up_btn.Bind(wx.EVT_BUTTON, self.move_selection)
        self.down_btn.Bind(wx.EVT_BUTTON, self.move_selection)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.button_sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.rearrange_list)
        self.button_sizer.Add(self.up_btn)
        self.button_sizer.Add(self.down_btn)
        self.sizer.Add(self.button_sizer)
        self.SetSizerAndFit(self.sizer)

    def get_selection(self):
        """
        Returns:
            mapping of option -> checked status. Dict items are inserted in the correct order
        """
        items_in_order = self.rearrange_list.GetItems()
        checked = self.rearrange_list.GetCheckedStrings()
        return {self.__labels[item]: item in checked for item in items_in_order}

    def move_selection(self, evt: wx.Event):
        if evt.Id == self.up_btn.Id:
            self.rearrange_list.MoveCurrentUp()
        elif evt.Id == self.down_btn.Id:
            self.rearrange_list.MoveCurrentDown()
        self.OnSelectionChange()

    def OnSelectionChange(self):
        """Posts a `EVT_REARRANGE_LIST_SELECT` event"""
        evt = RearrangeListSelect()
        evt.SetEventObject(self)
        evt.SetId(self.Id)
        wx.PostEvent(self.GetEventHandler(), evt)


class SelectionWindow(Frame):
    def __init__(
        self,
        parent,
        select_from: list,
        callback: Callable[[list[int], dict[str, bool]], None],
        options: Optional[dict[str, bool]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self.CenterOnParent()
        self.select_from = select_from
        self.callback = callback
        self.options = options or {}

        # create action buttons
        action_panel = wx.Panel(self)
        done_btn = wx.Button(action_panel, label='Done')
        deselect_all_btn = wx.Button(action_panel, label='Deselect All')
        select_all_btn = wx.Button(action_panel, label='Select All')
        # bind events
        done_btn.Bind(wx.EVT_BUTTON, self.done)
        deselect_all_btn.Bind(wx.EVT_BUTTON, self.deselect_all)
        select_all_btn.Bind(wx.EVT_BUTTON, self.select_all)
        # place
        action_sizer = wx.BoxSizer(wx.HORIZONTAL)
        for check in (done_btn, deselect_all_btn, select_all_btn):
            action_sizer.Add(check, 0, wx.ALL, 5)
        action_panel.SetSizer(action_sizer)

        # create option buttons
        def toggle_option(key):
            self.options[key] = not self.options[key]

        option_panel = wx.Panel(self)
        option_sizer = wx.GridSizer(cols=len(self.options), hgap=5, vgap=5)
        for key, value in self.options.items():
            check = wx.CheckBox(option_panel, label=key)
            if value:
                check.SetValue(wx.CHK_CHECKED)
            check.Bind(wx.EVT_CHECKBOX, lambda *_, k=key: toggle_option(k))
            option_sizer.Add(check, 0, wx.ALIGN_CENTER)
        option_panel.SetSizer(option_sizer)

        self.check_list = wx.CheckListBox(self, style=wx.LB_EXTENDED | wx.LB_NEEDED_SB)
        self.check_list.AppendItems(select_from)

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(action_panel, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(option_panel, 0, wx.ALL | wx.EXPAND, 5)
        sizer.Add(self.check_list, 0, wx.ALL | wx.EXPAND, 5)
        self.SetSizerAndFit(sizer)

    def done(self, *_):
        selected = self.check_list.GetCheckedItems()

        try:
            self.Close()
            self.Destroy()
        except RuntimeError:
            pass

        self.callback(selected, self.options)

    def deselect_all(self, *_):
        self.select_all(check=False)

    def select_all(self, *_, check=True):
        for i in range(len(self.select_from)):
            self.check_list.Check(i, check=check)


TimeSpanSelect, EVT_TIME_SPAN_SELECT = NewEvent()


class TimeSpanSelector(wx.Panel):
    def __init__(self, parent, *a, **kw):
        wx.Panel.__init__(self, parent, *a, **kw)

        # create widgets
        self.spin_ctrl = wx.SpinCtrl(self, min=1)
        self.choices = {'Forever': 0, 'Minutes': 60, 'Hours': 3600, 'Days': 86400, 'Months': 86400 * 30}
        self.multiplier_selector = wx.Choice(self, choices=list(self.choices.keys()))

        # bind events
        self.spin_ctrl.Bind(wx.EVT_SPINCTRL, self.OnSelection)
        self.multiplier_selector.Bind(wx.EVT_CHOICE, self.OnSelection)

        # place widgets
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.spin_ctrl, 0, wx.ALL, 0)
        sizer.Add(self.multiplier_selector, 0, wx.ALL, 0)
        self.SetSizerAndFit(sizer)

    def GetTime(self) -> int:
        multiplier = tuple(self.choices.values())[self.multiplier_selector.GetSelection()]
        return self.spin_ctrl.GetValue() * multiplier

    def OnSelection(self, _):
        if self.multiplier_selector.GetSelection() == 0:
            self.spin_ctrl.Hide()
        elif not self.spin_ctrl.IsShown():
            self.spin_ctrl.Show()
        self.Layout()

        evt = TimeSpanSelect()
        evt.SetEventObject(self)
        evt.SetId(self.Id)
        wx.PostEvent(self.GetEventHandler(), evt)

    def SetTime(self, seconds: int):
        if seconds == 0:
            self.multiplier_selector.SetSelection(0)
            self.spin_ctrl.Hide()
            return
        if not self.spin_ctrl.IsShown():
            self.spin_ctrl.Show()
        self.Layout()

        for name, multiplier in reversed(self.choices.items()):
            if (count := seconds // multiplier) >= 1:
                self.spin_ctrl.SetValue(count)
                self.multiplier_selector.SetSelection(tuple(self.choices).index(name))
                return


def simple_box_sizer(parent: wx.Panel, widgets: Iterable[wx.Window | Iterable[wx.Window]], group_mode=wx.VERTICAL):
    # place
    sizer = wx.BoxSizer(wx.VERTICAL)
    for widget in widgets:
        flag = wx.ALL
        if isinstance(widget, wx.StaticLine):
            flag |= wx.EXPAND
        elif isinstance(widget, tuple):
            sz = wx.BoxSizer(group_mode)
            for w in widget:
                sz.Add(w, 0, wx.ALL, 0)
            widget = sz

        sizer.Add(widget, 0, flag, 5)
    parent.SetSizerAndFit(sizer)
    parent.Layout()
