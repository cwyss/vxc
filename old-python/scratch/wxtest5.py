#!/usr/bin/env python

import wx


class ColorStateButton(wx.BitmapButton):
    def __init__(self, parent, color):
        self.size = parent.ConvertDialogSizeToPixels((12,8))
        wx.BitmapButton.__init__(self, parent, -1, self.makeBMC(color))

    def makeBMC(self, color):
        bmp = wx.EmptyBitmap(*self.size)
        dc = wx.MemoryDC()
        dc.SelectObject(bmp)
        dc.SetBackground(wx.Brush(color))
        dc.Clear()
        dc.SelectObject(wx.NullBitmap)
        return bmp

    def setColor(self, color):
        self.SetBitmapLabel(self.makeBMC(color))


class TestFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="test")

        panel = wx.Panel(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)

        b = wx.Button(self, -1, 'test')
        sizer.Add(b)
        self.Bind(wx.EVT_BUTTON, self.onbut, b)

        self.but = ColorStateButton(self, 'green')
        self.Bind(wx.EVT_BUTTON, self.oncolorbut, self.but)
        sizer.Add(self.but)

        panel.SetSizer(sizer)

    def onbut(self, evt):
        print "change to blue"
        self.but.setColor('blue')
    def oncolorbut(self, evt):
        print "change to red"
        self.but.setColor('red')

def run():
    app = wx.PySimpleApp()
    frame = TestFrame()
    frame.Show()
    app.MainLoop()

if __name__=='__main__':
    run()
