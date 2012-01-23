#!/usr/bin/env python


import wx


class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="wx test")

        panel = wx.Panel(parent=self)
        self.panel = panel
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.grid = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        self.grid.AddGrowableCol(1)

        self.text0 = wx.StaticText(parent=panel, label="text 0")
        self.text1 = wx.Button(parent=panel, label="0 rechts")
        self.grid.Add(self.text0, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.grid.Add(self.text1, 0, wx.EXPAND)

        self.text2 = wx.StaticText(parent=panel, label="mehr text")
        self.text3 = wx.Button(parent=panel, label="mehr")
        self.text2.Hide()
        self.text3.Hide()

        self.button1 = wx.Button(parent=panel, label="add")
        self.button2 = wx.Button(parent=panel, label="remove")
        
        self.sizer.Add(self.button1, flag=wx.EXPAND)
        self.sizer.Add(self.button2, flag=wx.EXPAND)
        self.sizer.Add(self.grid, flag=wx.EXPAND)
        panel.SetSizer(self.sizer)
        panel.Fit()
        self.Fit()

        self.Bind(wx.EVT_BUTTON, self.onButton1, self.button1)
        self.Bind(wx.EVT_BUTTON, self.onButton2, self.button2)

        self.Show(True)

    def onButton1(self, ev):
        print 'add'
        if not self.text2.IsShown():
            self.grid.Add(self.text2, 0, wx.ALIGN_RIGHT)
            self.grid.Add(self.text3, 0, wx.EXPAND)
            self.text2.Show()
            self.text3.Show()
            self.panel.Fit()
            self.Fit()

    def onButton2(self, ev):
        print 'rem'
        if self.text2.IsShown():
            self.grid.Detach(self.text2)
            self.grid.Detach(self.text3)
            self.text2.Show(False)
            self.text3.Show(False)
            self.panel.Fit()
            self.Fit()
        else:
            self.grid.Clear()
            self.grid.Add(self.text0, 0, wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
            self.grid.Add(self.text1, 0, wx.EXPAND)
#            self.panel.Fit()
#            self.Fit()

def runmain():
    app = wx.PySimpleApp()
    frame = MainFrame()

    app.MainLoop()


if __name__=='__main__':
    runmain()
