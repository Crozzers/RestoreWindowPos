import wx
from wx.lib.mixins.listctrl import TextEditMixin

from common import local_path


class Frame(wx.Frame):
    def __init__(self, parent=None, title=None, **kwargs):
        if title is None:
            title = 'RestoreWindowPos'
        else:
            title = f'{title} - RestoreWindowPos'
        wx.Frame.__init__(self, parent=parent, id=wx.ID_ANY,
                          title=title, **kwargs)
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
    def __init__(self, parent, *args, edit_cols: list[int] = None, **kwargs):
        kwargs.setdefault('style', wx.LC_REPORT | wx.LC_EDIT_LABELS)
        ListCtrl.__init__(self, parent, *args, **kwargs)
        TextEditMixin.__init__(self)
        self.edit_cols = edit_cols

    def OpenEditor(self, col, row):
        if self.edit_cols is not None:
            if col - 1 not in self.edit_cols:
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
            self.editor.SetSize(x0 - scrolloffset, y0,
                                x1, -1, wx.SIZE_USE_EXISTING)
            self.editor.SetValue(self.GetItem(row, col).GetText())
            self.editor.Show()
            self.editor.Raise()
            self.editor.SetSelection(-1, -1)
            self.editor.SetFocus()
