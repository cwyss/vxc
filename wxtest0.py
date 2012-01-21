#!/usr/bin/env python

import wx

class TestFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="test")

        panel = wx.Panel(self)

        txt1 = wx.StaticText(panel, label='bla|')
        txt2 = wx.StaticText(panel, label='blablub', size=(100,-1),
                             style=wx.ALIGN_RIGHT)
        txt3 = wx.StaticText(panel, label='|bla')

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(txt1)
        sizer.Add(txt2)
        sizer.Add(txt3)

        panel.SetSizer(sizer)


def run():
    app = wx.PySimpleApp()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()

if __name__=='__main__':
    run()
