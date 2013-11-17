#!/usr/bin/env python


import sys, time, wx, pyrawmidi, thread


vcEVT_CTRLCHANGE = wx.NewEventType()
EVT_CTRLCHANGE = wx.PyEventBinder(vcEVT_CTRLCHANGE)

class CtrlChangeEvent(wx.PyEvent):
    def __init__(self, evtType, wid, c, v):
        wx.PyEvent.__init__(self, wid, evtType)

        self.controller = c
        self.value = v



class MainFrame(wx.Frame):
    def __init__(self):
        wx.Frame.__init__(self, parent=None, title="wx test")

        panel = wx.Panel(parent=self)
        self.slider = wx.Slider(parent=panel, minValue=0, maxValue=127,
                           size=(200,-1), pos=(50,50), 
                           style=wx.SL_HORIZONTAL|wx.SL_RIGHT|wx.SL_LABELS)
        self.text = wx.StaticText(parent=panel, pos=(270,50), label="0")

        self.slider.Bind(wx.EVT_SCROLL, self.on_slider)
        self.Bind(EVT_CTRLCHANGE, self.on_ctrlchange)
        self.Show(True)

    def on_slider(self, evt):
        self.text.SetLabel(str(self.slider.GetValue()))
        pyrawmidi.write([0xB0,0x11,self.slider.GetValue()])

    def on_ctrlchange(self, evt):
        self.slider.SetValue(evt.value)

    def postsliderval(self, ctrl, val):
        evt = CtrlChangeEvent(vcEVT_CTRLCHANGE, -1, ctrl, val)
        wx.PostEvent(self, evt)


def printcmd(cmd):
    for b in cmd:
        print "%02X " % b ,
    print

class MidiInThread(object):
    def __init__(self, frame):
        self.frame = frame
        self.run = True
        self.running = False
        thread.start_new_thread(self.threadfunc, ())

    def threadfunc(self):
        self.running = True
        while True:
            cmd = pyrawmidi.read()
            if not self.run:
                break
            if cmd[0]==0xB0 and cmd[1]==0x11:
                self.frame.postsliderval(cmd[1], cmd[2])
            else:
                printcmd(cmd)
        self.running = False

    def stop(self):
        self.run = False

        # next midi msg is echoed back from the virus, causing threadfunc
        # to return from pyrawmidi.read() and terminate
#        pyrawmidi.write([0xf0,0,0x20,0x33,0x01,0x10,0x73,0x40,0x10,0x01,0xf7])

        # request single dump to cause threadfunc to terminate
        pyrawmidi.write([0xf0,0,0x20,0x33,0x01,0x10,0x30,0,0x40,0xf7])

        # wait for thread to terminate
        while self.running:
            time.sleep(.1)


def runmain():
    pyrawmidi.close()
    pyrawmidi.open("hw:1,0,1")
    pyrawmidi.setfilter(0,0)

    app = wx.PySimpleApp()
    frame = MainFrame()
    midiinthread = MidiInThread(frame)

    app.MainLoop()

    sys.stdout.write("terminating midi thread...")
    sys.stdout.flush()
    midiinthread.stop()
    sys.stdout.write("\n")

    pyrawmidi.close()


if __name__=='__main__':
    runmain()
