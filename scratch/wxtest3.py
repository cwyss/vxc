#!/usr/bin/env python

import wx

class TestFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "sizer test")
        panel = wx.Panel(self)

        nameLbl = wx.StaticText(panel, -1, "name:")
        name = wx.TextCtrl(panel, -1, "")
        addrLbl = wx.StaticText(panel, -1, "address:")
        addr = wx.TextCtrl(panel, -1, "")
        sliderLbl = wx.StaticText(panel, -1, "slider:")
        slider = wx.Slider(panel, -1)

        sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        sizer.AddGrowableCol(1)
        sizer.Add(nameLbl, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(name, 0, wx.EXPAND)
        sizer.Add(addrLbl, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(addr, 0, wx.EXPAND)
        sizer.Add(sliderLbl, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(slider, 0, wx.EXPAND)

        panel.SetSizer(sizer)
        sizer.Fit(self)
        sizer.SetSizeHints(self)

class TestFrame1(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, None, -1, "sizer test")
        panel = wx.Panel(self)

#        nameLbl = wx.StaticText(panel, -1, "name:")
        name = wx.TextCtrl(panel, -1, "")
#        addrLbl = wx.StaticText(panel, -1, "address:")
        addr = wx.TextCtrl(panel, -1, "")
        sliderLbl = wx.StaticText(panel, -1, "slider:")
        slider = wx.Slider(panel, -1, size=(100,-1))

        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(name, 0, wx.EXPAND)
        sizer.Add(addr, 0, wx.EXPAND)
        slsizer = wx.BoxSizer(wx.HORIZONTAL)
        slsizer.Add(sliderLbl, 0, 0)
        slsizer.Add(slider, 1, 0)
        sizer.Add(slsizer, 0, wx.EXPAND)

        panel.SetSizer(sizer)
        sizer.Fit(self)
        sizer.SetSizeHints(self)


def run():
    app = wx.PySimpleApp()
    frame = TestFrame1()
    frame.Show()
    app.MainLoop()


if __name__=='__main__':
    run()
