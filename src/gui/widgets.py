import wx

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
