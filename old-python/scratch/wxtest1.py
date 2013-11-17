#!/usr/bin/env python

import wx

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

        sizer.Fit(self)

def run():
    app = wx.PySimpleApp()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()

if __name__=='__main__':
    run()
