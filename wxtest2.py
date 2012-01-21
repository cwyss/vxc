#!/usr/bin/env python


import wx


vcEVT_CUSTOM = wx.NewEventType()
EVT_CUSTOM = wx.PyEventBinder(vcEVT_CUSTOM)

class CustomEvent(wx.PyCommandEvent):
    def __init__(self, evtType, wid):
        wx.PyCommandEvent.__init__(self, evtType, wid)



class CustomPanel(wx.Panel):
    def __init__(self, parent, label=''):
        wx.Panel.__init__(self, parent)

        self.text = wx.StaticText(parent=self, label=label)
        self.button = wx.Button(parent=self, label='press')

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.text, flag=wx.EXPAND)
        self.sizer.Add(self.button, flag=wx.EXPAND)
        self.SetSizer(self.sizer)
        self.Fit()

        self.Bind(wx.EVT_BUTTON, self.onButton)
#        self.Bind(EVT_CUSTOM, self.onCustom)

    def onButton(self, ev):
        print 'custom button'
        customevt = CustomEvent(vcEVT_CUSTOM, self.GetId())
        self.ProcessEvent(customevt)

    def onCustom(self, ev):
        print 'custom event'

class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="wx test")

        panel = wx.Panel(parent=self)
        self.panel = panel
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.text0 = wx.StaticText(parent=panel, label="text 0")
        self.text1 = wx.StaticText(parent=panel, label="text 1")
        self.text2 = wx.StaticText(parent=panel, label="2 mehr text")
        self.text2.Show(False)
        self.button = wx.Button(parent=panel, label="more text")
        self.custom = CustomPanel(panel, 'custom')
        
        self.sizer.Add(self.text0, flag=wx.EXPAND)
#        self.sizer.Add(self.text2, flag=wx.EXPAND)
        self.sizer.Add(self.text1, flag=wx.EXPAND)
        self.sizer.Add(self.button, flag=wx.EXPAND)
        self.sizer.Add(self.custom, flag=wx.EXPAND)
        panel.SetSizer(self.sizer)
        panel.Fit()
        self.Fit()

        self.Bind(wx.EVT_BUTTON, self.onButton)
#        self.Bind(wx.EVT_BUTTON, self.onCustom, self.custom)
        self.Bind(EVT_CUSTOM, self.onCustom)

        self.Show(True)

    def onButton(self, ev):
        self.sizer.Insert(2,self.text2, flag=wx.EXPAND)
        self.text2.Show()
        self.panel.Fit()
        self.Fit()

    def onCustom(self, ev):
        print 'custom panel'


def runmain():
    app = wx.PySimpleApp()
    frame = MainFrame()

    app.MainLoop()


if __name__=='__main__':
    runmain()
