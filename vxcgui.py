#!/usr/bin/env python


import wx, vxcmidi, vxcctrl, csv, os


vcEVT_MIDI = wx.NewEventType()
EVT_MIDI = wx.PyEventBinder(vcEVT_MIDI)

class MidiEvent(wx.PyEvent):
    def __init__(self, evtType, wid, msg):
        wx.PyEvent.__init__(self, wid, evtType)
        self.msg = msg


class StoreDialog(wx.Dialog):
    def __init__(self, oldname):
        wx.Dialog.__init__(self, None, title='Store Program')
        self.overwrite = False

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)
        
        namesizer = wx.BoxSizer(wx.HORIZONTAL)
        lbl = wx.StaticText(self, -1, 'Name')
        namesizer.Add(lbl, 0, wx.ALIGN_CENTER|wx.LEFT|wx.RIGHT, 5)
        self.name = wx.TextCtrl(self, -1, oldname.rstrip())
        namesizer.Add(self.name, 1, wx.RIGHT, 5)
        sizer.Add(namesizer, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)

        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        but = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        butsizer.Add(but, 0)
        but = wx.Button(self, -1, 'Overwrite')
        but.Bind(wx.EVT_BUTTON, self.onOverwrite)
        butsizer.Add(but, 0)
        but = wx.Button(self, wx.ID_OK, 'Append')
        butsizer.Add(but, 0)
        sizer.Add(butsizer, 0, flag=wx.EXPAND)

        self.Fit()

    def onOverwrite(self, evt):
        self.overwrite = True
        self.EndModal(wx.ID_OK)


class LimitDialog(wx.Dialog):
    def __init__(self, proglib):
        wx.Dialog.__init__(self, None, title='Limit Program List',
                           style=wx.RESIZE_BORDER)
        self.proglib = proglib
        self.ctrlcond = []

        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        linesizer = wx.BoxSizer(wx.HORIZONTAL)
        label = wx.StaticText(self, -1, 'Name')
        self.name = wx.TextCtrl(self, -1)
        linesizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.LEFT|wx.RIGHT, 5)
        linesizer.Add(self.name, 1, wx.RIGHT, 5)
        sizer.Add(linesizer, 0, wx.EXPAND|wx.TOP|wx.BOTTOM, 5)

        self.condlist = wx.ListBox(self, -1)
        sizer.Add(self.condlist, 1, wx.EXPAND|wx.LEFT|wx.RIGHT|wx.BOTTOM, 5)
        self.condlist.Bind(wx.EVT_LISTBOX, self.onSelCond)

        linesizer = wx.BoxSizer(wx.HORIZONTAL)
        self.boolop = wx.Choice(self, -1, 
                                choices=vxcmidi.LIMITBOOL_NAMES.values())
        linesizer.Add(self.boolop, 0, wx.LEFT|wx.RIGHT, 5)
        self.boolop.Bind(wx.EVT_CHOICE, self.onBoolOp)
        self.ctrlpage = wx.Choice(self, -1,
                                  choices=vxcmidi.CTRL_NAMES)
        linesizer.Add(self.ctrlpage, 0, wx.RIGHT, 5)
        self.ctrlpage.Bind(wx.EVT_CHOICE, self.onCtrlPageNr)
        self.ctrlnr = wx.SpinCtrl(self, max=127)
        linesizer.Add(self.ctrlnr, 0, wx.RIGHT, 5)
        self.ctrlnr.Bind(wx.EVT_SPINCTRL, self.onCtrlPageNr)
        self.relatop = wx.Choice(self, -1, 
                                 choices=vxcmidi.LIMITREL_NAMES.values())
        linesizer.Add(self.relatop, 0, wx.RIGHT, 5)
        self.relatop.Bind(wx.EVT_CHOICE, self.onRelatOp)
        self.val = wx.SpinCtrl(self, max=127)
        linesizer.Add(self.val, 0, wx.RIGHT, 5)
        self.val.Bind(wx.EVT_SPINCTRL, self.onVal)
        sizer.Add(linesizer, 0, wx.EXPAND|wx.BOTTOM, 5)

        linesizer = wx.BoxSizer(wx.HORIZONTAL)
        but = wx.Button(self, -1, 'Add Cond')
        but.Bind(wx.EVT_BUTTON, self.onAddCond)
        linesizer.Add(but, 0, wx.LEFT, 5)
        but = wx.Button(self, -1, 'Rem Cond')
        but.Bind(wx.EVT_BUTTON, self.onRemCond)
        linesizer.Add(but, 0)
        but = wx.Button(self, -1, 'Clear All')
        but.Bind(wx.EVT_BUTTON, self.onClearAll)
        linesizer.Add(but, 0)
        but = wx.Button(self, -1, 'Update')
        but.Bind(wx.EVT_BUTTON, self.onUpdate)
        linesizer.Add(but, 0)
        but = wx.Button(self, wx.ID_OK, 'Close')
        but.Bind(wx.EVT_BUTTON, self.onClose)
        linesizer.Add(but, 0, wx.RIGHT, 5)
        sizer.Add(linesizer, 0, wx.EXPAND|wx.BOTTOM, 5)

        self.Fit()
        sizer.SetSizeHints(self)
        self.updateCondList()

    def enableCondBut(self, val=True):
        self.boolop.Enable(val)
        self.ctrlpage.Enable(val)
        self.ctrlnr.Enable(val)
        self.relatop.Enable(val)
        self.val.Enable(val)

    def makeCondStr(self, cond):
        return "%3s %s %3d %2s %d" % (vxcmidi.LIMITBOOL_NAMES[cond[0]],
                                      vxcmidi.CTRL_NAMES[cond[1][0]],
                                      cond[1][1],
                                      vxcmidi.LIMITREL_NAMES[cond[2]],
                                      cond[3])

    def updateCond(self, ind):
        str = self.makeCondStr(self.ctrlcond[ind])
        self.condlist.SetString(ind, str)

    def updateCondList(self, selind=0):
        condlen = len(self.ctrlcond)
        if condlen>0:
            strlst = [self.makeCondStr(cond) for cond in self.ctrlcond]
            self.condlist.Set(strlst)
            if selind>=condlen:
                selind = condlen-1
            self.condlist.SetSelection(selind)
            self.enableCondBut(True)
            self.showCond(selind)
        else:
            self.condlist.Clear()
            self.enableCondBut(False)

    def showCond(self, ind):
        cond = self.ctrlcond[ind]
        self.boolop.SetSelection(cond[0])
        self.ctrlpage.SetSelection(cond[1][0])
        self.ctrlnr.SetValue(cond[1][1])
        self.relatop.SetSelection(cond[2])
        self.val.SetValue(cond[3])

    def onSelCond(self, evt):
        selind = self.condlist.GetSelection()
        if selind>=0:
            self.showCond(selind)

    def setCond(self, cind, value):
        selind = self.condlist.GetSelection()
        self.ctrlcond[selind][cind] = value
        self.updateCond(selind)
    def onBoolOp(self, evt):
        self.setCond(0, self.boolop.GetSelection())
    def onCtrlPageNr(self, evt):
        self.setCond(1, (self.ctrlpage.GetSelection(), 
                         self.ctrlnr.GetValue()))
    def onRelatOp(self, evt):
        self.setCond(2, self.relatop.GetSelection())
    def onVal(self, evt):
        self.setCond(3, self.val.GetValue())

    def onAddCond(self, evt):
        self.ctrlcond.append([vxcmidi.LIMIT_AND, (vxcmidi.CTRL_A,0),
                              vxcmidi.LIMIT_EQ, 0])
        self.updateCondList(len(self.ctrlcond)-1)

    def onRemCond(self, evt):
        rmind = self.condlist.GetSelection()
        if rmind>=0:
            del self.ctrlcond[rmind]
            self.updateCondList(rmind)

    def onClearAll(self, evt):
        self.name.SetValue("")
        self.ctrlcond = []
        self.updateCondList()
        self.onUpdate()

    def onClose(self, evt):
        self.onUpdate()
        self.Close()

    def onUpdate(self, evt=None):
        self.proglib.setLimitCrit(self.name.GetValue(), self.ctrlcond)


class ProgLibGUI(wx.Panel):
    def __init__(self, parent, interface):
        wx.Panel.__init__(self, parent)
        self.interface = interface
        interface.addLibChngListener(self.onLibChange)
        interface.addPrgChngListener(self.onProgChange)

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)
        leftsizer = wx.BoxSizer(wx.VERTICAL)
        self.banklist = wx.ListBox(self, style=wx.LB_SINGLE)
        leftsizer.Add(self.banklist, 1, flag=wx.EXPAND)
        
        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.storebut = wx.ToggleButton(self, -1, 'Store')
        butsizer.Add(self.storebut, 0)
        self.movebut = wx.ToggleButton(self, -1, 'Move')
        butsizer.Add(self.movebut, 0)
        leftsizer.Add(butsizer, 0, flag=wx.EXPAND)

        self.sizer.Add(leftsizer, 0, flag=wx.EXPAND)
        self.proglist = wx.ListCtrl(self, style=wx.LC_LIST)
        self.sizer.Add(self.proglist, 3, flag=wx.EXPAND)

        self.banklist.Bind(wx.EVT_LISTBOX, self.onBankSel)
        self.proglist.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onProgSel)
        self.storebut.Bind(wx.EVT_TOGGLEBUTTON, self.onStore)

        self.onLibChange()

    def onLibChange(self, newpart=vxcmidi.PL_LIBCHNG, appendName=None):
        pl  = self.interface.proglib
        if newpart==vxcmidi.PL_LIBCHNG:
            self.banklist.Set(pl.getBankNames())
            bankind = self.interface.proglib.getSelBank()
            self.banklist.SetSelection(bankind)
            self.updateProgList()
        elif newpart==vxcmidi.PL_NEWBANK:
            self.banklist.Append(appendName)
        else:
            self.updateProgList(appendName=appendName)

    def updateProgList(self, appendName=None):
        bankind = self.banklist.GetSelection()
        if appendName==None:
            self.proglist.ClearAll()
            if bankind>=0:
                content = self.interface.proglib.getBankContents(bankind)
                for i in range(len(content)):
                    string = "%3d %s" % (content[i][1], content[i][0])
                    self.proglist.InsertStringItem(i, string)
                pi = self.interface.proglib.getCurrentProg()
                self.proglist.Select(pi, True)
        elif bankind==self.banklist.GetCount()-1:
            self.proglist.Append((appendName,))

    def onBankSel(self, evt):
        bi = self.banklist.GetSelection()
        if bi>=0:
            self.interface.proglib.setBank(bi)
            self.updateProgList()

    def onProgSel(self, evt):
        pi = evt.GetIndex()
        if self.storebut.GetValue()==True:
            self.storebut.SetValue(False)
            self.interface.storeProg(self.storeName, pi)
        elif self.movebut.GetValue()==True:
            self.movebut.SetValue(False)
            self.interface.proglib.moveProg(pi)
        else:
            self.interface.proglib.setProg(pi)

    def onProgChange(self):
        bi = self.interface.proglib.getSelBank()
        if bi!=self.banklist.GetSelection():
            self.banklist.SetSelection(bi)
            self.updateProgList()
        newpi = self.interface.proglib.getCurrentProg()
        pi = self.proglist.GetFirstSelected()
        if pi!=newpi:
            self.proglist.Select(pi, False)
            self.proglist.Select(newpi, True)

    def onStore(self, evt):
        if self.storebut.GetValue()==True:
            name = self.interface.current.name
            name = wx.GetTextFromUser("Enter program name", 
                                      "Store program to...",
                                      default_value=name)
            if name!='':
                self.storeName = name
            else:
                self.storebut.SetValue(False)


class ReadBankDialog(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, title="Read Bank from Virus")
        self.readall = False

        sizer = wx.BoxSizer(wx.VERTICAL)

        self.banklist = wx.ListBox(self, choices=self.makeBankList(),
                                   style=wx.LB_EXTENDED)
        sizer.Add(self.banklist, flag=wx.EXPAND)

        namesizer = wx.BoxSizer(wx.HORIZONTAL)
        namelbl = wx.StaticText(self, label="Prefix")
        namesizer.Add(namelbl, flag=wx.ALIGN_CENTER_VERTICAL)
        self.nameCtrl = wx.TextCtrl(self, value="")
        namesizer.Add(self.nameCtrl, 1)
        sizer.Add(namesizer, flag=wx.EXPAND)

        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        cancelbut = wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer.Add(cancelbut)
        allbut = wx.Button(self, -1, "Read All")
        butsizer.Add(allbut)
        allbut.Bind(wx.EVT_BUTTON, self.onReadAll)
        okbut = wx.Button(self, wx.ID_OK, "Read Selected")
        butsizer.Add(okbut)
        sizer.Add(butsizer, flag=wx.EXPAND)

        self.SetSizer(sizer)
        self.Fit()

    def onReadAll(self, evt):
        self.readall = True
        self.EndModal(wx.ID_OK)

    def makeBankName(self, i):
        if i<4:
            return "Ram %c" % (65+i)
        else:
            return "Rom %c" % (65+i-4)

    def makeBankList(self):
        return [self.makeBankName(i) for i in range(4+26)]

    def getReqList(self):
        if self.readall:
            sel = range(4+26)
        else:
            sel = self.banklist.GetSelections()
        lst = []
        prefix = self.nameCtrl.GetValue()
        if prefix!='':
            prefix += ' '
        for i in sel:
            lst.append((i+1,prefix+self.makeBankName(i)))
        return lst


class Prefs(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, title="Preferences")

        self.port = 'hw:1,0,1'
        self.proglib = ''
        self.ctrldef = ''
        self.midifilter = 0
        self.connect = 1
        self.allwaysRecv = 1
        self.allwaysSend = 0
        self.winsize = [800,500]

        self.load(tryit=True)
        self.setupDialog()

    def setupDialog(self):
        self.sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        self.sizer.AddGrowableCol(1)
        self.SetSizer(self.sizer)

        label = wx.StaticText(self, label='Midi Port')
        portsizer = wx.BoxSizer(wx.VERTICAL)
        self.portCtrl = wx.TextCtrl(self)
        portsizer.Add(self.portCtrl, 0, wx.EXPAND)
        self.connectCtrl = wx.CheckBox(self, -1, 'Connect at Startup')
        portsizer.Add(self.connectCtrl, 0, wx.EXPAND)
        self.recvCtrl = wx.CheckBox(self, -1, 'Always Recieve')
        portsizer.Add(self.recvCtrl, 0, wx.EXPAND)
        self.sendCtrl = wx.CheckBox(self, -1, 'Allways Send')
        portsizer.Add(self.sendCtrl, 0, wx.EXPAND)
        self.sizer.Add(label, 0, 
                       wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(portsizer, 0, wx.EXPAND)

        label = wx.StaticText(self, label='Program Library')
        self.proglibCtrl = wx.TextCtrl(self)
        self.sizer.Add(label, 0, 
                       wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(self.proglibCtrl, 0, wx.EXPAND)

        label = wx.StaticText(self, label='Controller Definitions')
        self.ctrldefCtrl = wx.TextCtrl(self)
        self.sizer.Add(label, 0, 
                       wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(self.ctrldefCtrl, 0, wx.EXPAND)

        label = wx.StaticText(self, label='Midi Filter')
        fltsizer = wx.BoxSizer(wx.VERTICAL)
        self.fltnote = wx.CheckBox(self, -1, 'Note On/Off')
        fltsizer.Add(self.fltnote, 0)
        self.fltpress = wx.CheckBox(self, -1, 'Channel Pressure')
        fltsizer.Add(self.fltpress, 0)
        self.fltpitch = wx.CheckBox(self, -1, 'Pitch')
        fltsizer.Add(self.fltpitch, 0)
        self.fltmod = wx.CheckBox(self, -1, 'Mod Wheel')
        fltsizer.Add(self.fltmod, 0)
        self.sizer.Add(label, 0, 
                       wx.ALIGN_RIGHT|wx.ALIGN_TOP)
        self.sizer.Add(fltsizer, 0, wx.EXPAND)

        label = wx.StaticText(self, label='Window Size')
        wssizer = wx.BoxSizer(wx.HORIZONTAL)
        self.winwidth = wx.SpinCtrl(self, max=9999)
        wssizer.Add(self.winwidth, 0)
        self.winheight = wx.SpinCtrl(self, max=9999)
        wssizer.Add(self.winheight, 0)
        self.sizer.Add(label, 0, 
                       wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(wssizer, 0, wx.EXPAND)

        but = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        self.sizer.Add(but, 0)
        but = wx.Button(self, wx.ID_OK, 'Ok')
        self.sizer.Add(but, 0)

    def load(self, filename='.vxcrc', tryit=False):
        try:
            rdr = csv.reader(open(filename, 'r'))
            self.port, self.proglib, self.ctrldef = rdr.next()
            self.midifilter = int(rdr.next()[0])
            self.connect,self.allwaysRecv,self.allwaysSend = \
                map(int, rdr.next())
            self.winsize = map(int, rdr.next())
        except IOError as error:
            if error.errno!=os.errno.ENOENT or not tryit:
                showError(str(error))
        except ValueError:
            showError("rc file %s: wrong type" % filename)
        except StopIteration:
            pass

    def save(self, filename='.vxcrc'):
        try:
            wrt = csv.writer(open(filename, 'w'))
            wrt.writerow((self.port, self.proglib, self.ctrldef))
            wrt.writerow((self.midifilter,))
            wrt.writerow((self.connect,self.allwaysRecv,self.allwaysSend))
            wrt.writerow(self.winsize)
        except IOError as error:
            showError(str(error))

    def setFltValue(self, filter):
        self.fltnote.SetValue(filter & vxcmidi.FILTER_NOTE)
        self.fltpress.SetValue(filter & vxcmidi.FILTER_CHNPRESS)
        self.fltpitch.SetValue(filter & vxcmidi.FILTER_PITCH)
        self.fltmod.SetValue(filter & vxcmidi.FILTER_MOD)

    def getFltValue(self):
        filter = 0
        if self.fltnote.GetValue():
            filter += vxcmidi.FILTER_NOTE
        if self.fltpress.GetValue():
            filter += vxcmidi.FILTER_CHNPRESS
        if self.fltpitch.GetValue():
            filter += vxcmidi.FILTER_PITCH
        if self.fltmod.GetValue():
            filter += vxcmidi.FILTER_MOD
        return filter

    def doDialog(self):
        self.portCtrl.SetValue(self.port)
        self.proglibCtrl.SetValue(self.proglib)
        self.ctrldefCtrl.SetValue(self.ctrldef)
        self.setFltValue(self.midifilter)
        self.connectCtrl.SetValue(self.connect)
        self.recvCtrl.SetValue(self.allwaysRecv)
        self.sendCtrl.SetValue(self.allwaysSend)
        self.winwidth.SetValue(self.winsize[0])
        self.winheight.SetValue(self.winsize[1])
        if self.ShowModal()==wx.ID_OK:
            self.port = self.portCtrl.GetValue()
            self.proglib = self.proglibCtrl.GetValue()
            self.ctrldef = self.ctrldefCtrl.GetValue()
            self.midifilter = self.getFltValue()
            self.connect = int(self.connectCtrl.GetValue())
            self.allwaysRecv = int(self.recvCtrl.GetValue())
            self.allwaysSend = int(self.sendCtrl.GetValue())
            self.winsize[0] = self.winwidth.GetValue()
            self.winsize[1] = self.winheight.GetValue()
            self.save()


class vxcFrame(wx.Frame):
    def __init__(self, interface):
        wx.Frame.__init__(self, parent=None, title='VirusXControl')

        self.prefs = Prefs()
        self.SetSize(self.prefs.winsize)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.interface = interface
        interface.addPrgChngListener(self.onProgChange)
        interface.addLibChngListener(self.onLibChange)

        self.limitdialog = LimitDialog(interface.proglib)

        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.setMidiMsg('disconnected')
        self.createMenu()

        self.notebook = wx.Notebook(self)
        print "build ProgLib page"
        self.proglib = ProgLibGUI(self.notebook, interface)
        self.initCtrlPages()
        self.controllers = vxcctrl.ControllersGUI(self.notebook, interface)
        self.setupNotebook()

        if len(self.prefs.proglib):
            print "load proglib"
            self.loadProgLib(self.prefs.proglib)
        else:
            self.onProgChange()

    def onClose(self, evt):
        self.limitdialog.Destroy()
        self.prefs.Destroy()
        self.Destroy()

    def onProgChange(self):
        if self.interface.isProgModified()==True:
            line = '** '
        else:
            line = '-- '
        line += "[%s] %s" % (self.interface.current_location,
                             self.interface.current.name)
        self.statusbar.SetStatusText(line, 0)

    def onLibChange(self, newpart, appendName):
        numprogs, numbanks, nolimit = self.interface.proglib.getVisibleInfo()
        line = "%d programs in %d banks (%s)" % \
            (numprogs, numbanks, "all" if nolimit else "limit")
        self.statusbar.SetStatusText(line, 1)

    def setMidiMsg(self, midimsg):
        self.statusbar.SetStatusText(midimsg, 1)


    def createMenu(self):
        menubar = wx.MenuBar()

        menu = wx.Menu()
        item = menu.AppendCheckItem(-1, '&Connect to Virus\tctrl-c')
        self.Bind(wx.EVT_MENU, self.onConnect, item)
        menu.AppendSeparator()
        item = menu.Append(-1, 'Preferences...')
        self.Bind(wx.EVT_MENU, self.onPrefs, item)
        item = menu.Append(-1, 'Controller Setup...')
        self.Bind(wx.EVT_MENU, self.onCtrlSetup, item)
        menu.AppendSeparator()
        item = menu.Append(-1, '&Quit\tctrl-q')
        self.Bind(wx.EVT_MENU, self.onQuit, item)
        menubar.Append(menu, '&Main')

        menu = wx.Menu()
        item = menu.Append(-1, 'Next\tctrl-n')
        self.Bind(wx.EVT_MENU, self.onNextProg, item)
        item = menu.Append(-1, 'Prev\tctrl-p')
        self.Bind(wx.EVT_MENU, self.onPrevProg, item)
        item = menu.Append(-1, 'Revert\tctrl-v')
        self.Bind(wx.EVT_MENU, self.onRevert, item)
        menu.AppendSeparator()
        item = menu.Append(-1, 'Store\tctrl-s')
        self.Bind(wx.EVT_MENU, self.onStore, item)
        item = menu.Append(-1, 'Append\tctrl-a')
        self.Bind(wx.EVT_MENU, self.onAppend, item)
        item = menu.Append(-1, 'Delete\tctrl-d')
        self.Bind(wx.EVT_MENU, self.onDelete, item)
        menu.AppendSeparator()
        item = menu.Append(-1, 'Limit...\tctrl-l')
        self.Bind(wx.EVT_MENU, self.onLimit, item)
        menu.AppendSeparator()
        item = menu.Append(-1, 'Receive\tctrl-r')
        self.Bind(wx.EVT_MENU, self.onRecvProg, item)
        item = menu.AppendCheckItem(-1, 'Always Receive')
        self.Bind(wx.EVT_MENU, self.onAlwaysRecv, item)
        menubar.Append(menu, '&Single')

        menu = wx.Menu()
        item = menu.Append(-1, 'Load ProgLib...')
        self.Bind(wx.EVT_MENU, self.onLoadProgLib, item)
        item = menu.Append(-1, 'Save ProgLib...')
        self.Bind(wx.EVT_MENU, self.onSaveProgLib, item)
        menu.AppendSeparator()
        item = menu.Append(-1, 'New Bank')
        self.Bind(wx.EVT_MENU, self.onNewBank, item)
        item = menu.Append(-1, 'Delete Bank')
        self.Bind(wx.EVT_MENU, self.onDeleteBank, item)
        menu.AppendSeparator()
        item = menu.Append(-1, 'Read Bank from Virus...')
        self.Bind(wx.EVT_MENU, self.onReadBank, item)
        item = menu.Append(-1, 'Stop Bank Read')
        self.Bind(wx.EVT_MENU, self.onStopRead, item)
        item = menu.Append(-1, 'Resume Bank Read')
        self.Bind(wx.EVT_MENU, self.onResumeRead, item)
        menubar.Append(menu, '&Library')

        self.SetMenuBar(menubar)

    def setupNavigateMenu(self):
        menu = wx.Menu()
        self.navgotoDict = {}
        for i in range(self.notebook.GetPageCount()):
            name = self.notebook.GetPageText(i) + '\tF%d' % (i+1)
            item = menu.Append(-1, name)
            self.Bind(wx.EVT_MENU, self.onNotebookGoto, item)
            self.navgotoDict[item.GetId()] = i

        menubar = self.GetMenuBar()
        oldpos = menubar.FindMenu("Navigate")
        if oldpos!=wx.NOT_FOUND:
            menubar.Replace(oldpos, menu, '&Navigate')
        else:
            menubar.Append(menu, '&Navigate')

    def initCtrlPages(self):
        self.ctrlpages = vxcctrl.CtrlPages()
        if len(self.prefs.ctrldef)>0:
            print "load controller defs"
            try:
                self.ctrlpages.loadFromFile(self.prefs.ctrldef)
            except IOError as error:
                showError('Error reading controller definitions.\n' +
                          "%s: '%s'" % (error.strerror, error.filename))
        else:
            self.ctrlpages.init2()

    def setupNotebook(self):
        while self.notebook.GetPageCount()>0:
            self.notebook.RemovePage(0)
        self.notebook.AddPage(self.proglib, 'Library')
        self.controllers.setup(self.ctrlpages)
        self.setupNavigateMenu()

    def loadProgLib(self, libname):
        try:
            self.interface.proglib.loadFromFile(libname)
        except vxcmidi.ProgLibError as error:
            showError(str(error))
        except IOError as error:
            showError('Error reading program library.\n' +
                      error.strerror+': '+error.filename)


    def onConnect(self, evt):
        if self.GetMenuBar().IsChecked(evt.GetId()):
            try:
                self.setMidiMsg('connected')
                self.interface.connect(self.prefs.port, self.prefs.midifilter)
            except StandardError as error:
                showError(str(error))
                self.GetMenuBar().Check(evt.GetId(), False)
                self.setMidiMsg('disconnected')
        else:
            self.interface.disconnect()
            self.setMidiMsg('disconnected')

    def onPrefs(self, evt):
        self.prefs.doDialog()

    def onCtrlSetup(self, evt):
        dialog = vxcctrl.CtrlDefDialog(self.ctrlpages)
        if dialog.ShowModal()==wx.ID_OK:
            self.ctrlpages = dialog.getPages()
            if dialog.save:
                if len(self.prefs.ctrldef)>0:
                    try:
                        self.ctrlpages.saveToFile(self.prefs.ctrldef)
                    except IOError as error:
                        showError('Error writing controller definitions.\n' +
                                  "%s: '%s'" % (error.strerror, error.filename))
                else:
                    showError("No CtrlDef filename specified")
            self.setupNotebook()
        dialog.Destroy()

    def onQuit(self, evt):
        self.Close()

    def onRecvProg(self, evt):
        try:
            self.interface.readSingleVirus()
        except StandardError as error:
            showError(str(error))
        
    def onAlwaysRecv(self, evt):
        recv = self.GetMenuBar().IsChecked(evt.GetId())
        self.interface.setAlwaysReceive(recv)

    def onReadBank(self, evt):
        dialog = ReadBankDialog()
        ret = dialog.ShowModal()
        if ret==wx.ID_OK:
            try:
                banklst = dialog.getReqList()
                self.interface.readBankListVirus(banklst)
            except StandardError as error:
                showError(str(error))
        dialog.Destroy()

    def onStopRead(self, evt):
        try:
            self.interface.stopBankRead()
        except StandardError as error:
            showError(str(error))

    def onResumeRead(self, evt):
        try:
            self.interface.resumeBankRead()
        except StandardError as error:
            showError(str(error))

    def onNewBank(self, evt):
        name = wx.GetTextFromUser("Enter new bank name", "New Bank")
        if name!='':
            self.interface.proglib.newBank(name)

    def onDeleteBank(self, evt):
        self.interface.proglib.deleteBank()

    def onNextProg(self, evt):
        self.interface.proglib.nextProg()
    def onPrevProg(self, evt):
        self.interface.proglib.prevProg()

    def onLoadProgLib(self, evt):
        wildcard="Program Library (*.vlb)|*.vlb|All Files|*"
        dialog = wx.FileDialog(None, "Load Program Library", style=wx.OPEN,
                               wildcard=wildcard)
        if dialog.ShowModal()==wx.ID_OK:
            self.loadProgLib(dialog.GetPath())

    def onSaveProgLib(self, evt):
        wildcard="Program Library (*.vlb)|*.vlb|All Files|*"
        dialog = wx.FileDialog(None, "Save Program Library", style=wx.SAVE,
                               wildcard=wildcard)
        if dialog.ShowModal()==wx.ID_OK:
            try:
                self.interface.proglib.saveToFile(dialog.GetPath())
            except IOError as error:
                showError('Error writing program library.\n' +
                          "%s: '%s'" % (error.strerror, error.filename))

    def onLimit(self, evt):
        self.limitdialog.Show()

    def onRevert(self, evt):
        self.interface.revertProg()
    def onDelete(self, evt):
        self.interface.proglib.deleteProg()

    def onStore(self, evt):
        name = wx.GetTextFromUser("Enter program name", "Store Program",
                                  default_value=self.interface.current.name)
        if name!='':
            self.interface.storeProg(name)

    def onAppend(self, evt):
        name = wx.GetTextFromUser("Enter program name", "Append Program",
                                  default_value=self.interface.current.name)
        if name!='':
            self.interface.appendProg(name)

    def onNotebookGoto(self, evt):
        page = self.navgotoDict[evt.GetId()]
        self.notebook.ChangeSelection(page)


class vxcGUI(object):
    def __init__(self):
        self.app = wx.PySimpleApp()
        self.midinotify = self.nop
        self.app.Bind(EVT_MIDI, self.onMidi)

        print "setup midi"
        self.interface = vxcmidi.ProgInterface(self)
        self.frame = vxcFrame(self.interface)

#        self.frame.Fit()
        self.frame.Show()

    def run(self):
        self.app.MainLoop()

    def postEvent(self, msg):
        evt = MidiEvent(vcEVT_MIDI, -1, msg)
        wx.PostEvent(self.frame, evt)

    def setNotify(self, notify):
        self.midinotify = notify

    def onMidi(self, evt):
        self.frame.setMidiMsg(evt.msg.getInfoStr())
        self.midinotify(evt.msg)

    def setMidiMsg(self, str):
        self.frame.setMidiMsg(str)

    def nop(self, val):
        pass


def showError(errstr):
    wx.MessageBox(errstr, "VirusXControl Error", wx.OK | wx.ICON_ERROR)



if __name__=="__main__":
    vxcgui = vxcGUI()
    vxcgui.run()
    print "bye"


