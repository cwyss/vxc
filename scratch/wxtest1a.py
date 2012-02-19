#!/usr/bin/env python

import wx

class TestDialog(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, title="dialog", style=wx.RESIZE_BORDER)

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        # txt1 = wx.StaticText(self, label='bla|long long long')
        # sizer.Add(txt1)

        # lb = wx.ListBox(self, choices=['aaa','bb bb','ccccc'])
        # sizer.Add(lb, 1, flag=wx.EXPAND)

        # lc = wx.ListCtrl(self, style=wx.LC_REPORT)
        lc = wx.TreeCtrl(self)
        sizer.Add(lc, 1, flag=wx.EXPAND)

        sizer.Fit(self)
        sizer.SetSizeHints(self)
#        print "dialog", self.GetMinSize(), self.GetMaxSize()


class TestFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="test")

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.VERTICAL)
        panel.SetSizer(sizer)

        txt1 = wx.StaticText(panel, label='bla|long long long')
        sizer.Add(txt1)

        lb = wx.ListBox(panel, choices=['aaa','bb bb','ccccc'])
        sizer.Add(lb, 1, flag=wx.EXPAND)

        but = wx.Button(panel, -1, "Dialog")
        sizer.Add(but)
        but.Bind(wx.EVT_BUTTON, self.onBut)

        sizer.Fit(self)
        print "frame", self.GetMinSize(), self.GetMaxSize()

    def onBut(self, evt):
        dlg = TestDialog()
        dlg.ShowModal()
        dlg.Destroy()


def run():
    app = wx.PySimpleApp()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()

if __name__=='__main__':
    run()
