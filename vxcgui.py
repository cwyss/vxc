#!/usr/bin/env python


import wx, vxcmidi, vxcctrl, csv, os


vcEVT_MIDI = wx.NewEventType()
EVT_MIDI = wx.PyEventBinder(vcEVT_MIDI)

class MidiEvent(wx.PyEvent):
    def __init__(self, evtType, wid, msg):
        wx.PyEvent.__init__(self, wid, evtType)
        self.msg = msg


class CtrlGUI(wx.Panel):
    def __init__(self, parent, interface, cdef):
        wx.Panel.__init__(self, parent)
        self.interface = interface
        self.cdef = cdef
        interface.addListener(cdef.cid, self.setVal)

        self.label = wx.StaticText(parent, label=cdef.name)

    def setVal(self, val):
        pass

    def onGUI(self, val):
        try:
            self.interface.setCtrl(self.cdef.cid, val)
        except StandardError as error:
            showError(str(error))

    def Show(self, show=True):
        wx.Panel.Show(self, show)
        self.label.Show(show)

    def Hide(self):
        wx.Panel.Hide(self)
        self.label.Hide()


class StdCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        self.slider = wx.Slider(parent=self, minValue=cdef.valrange[0],
                                maxValue=cdef.valrange[1],
                                size=(60,-1),
                                style=wx.SL_HORIZONTAL)
        self.slider.SetPageSize((cdef.valrange[1]-cdef.valrange[0]+1)/16)
        self.valtext \
            = wx.StaticText(parent=self,
                            label=self.getValSpareText())
#                            style=wx.ALIGN_RIGHT|wx.ST_NO_AUTORESIZE)
        self.valtext.SetMinSize(self.valtext.GetSize())

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.slider, 1)
        self.sizer.Add(self.valtext, 0, wx.ALIGN_CENTER)
        self.SetSizer(self.sizer)
#        self.Layout()
        self.sizer.SetSizeHints(self)

        self.updateValText()

        self.Bind(wx.EVT_SCROLL, self.onSlider)

    def onSlider(self, evt):
        if evt.GetEventType()==wx.wxEVT_SCROLL_CHANGED or \
                evt.GetEventType()==wx.wxEVT_SCROLL_THUMBTRACK:
            self.updateValText()
            self.onGUI(self.slider.GetValue())

    def setVal(self, val):
        if val!=self.slider.GetValue():
            self.slider.SetValue(val)
            self.updateValText()

    def updateValText(self):
        val = self.slider.GetValue()
        self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        return '127'

class SignCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()-64
        self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        return '-64'

class SignPercentCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.negspan = 64 - cdef.valrange[0]
        self.posspan = cdef.valrange[1] - 64
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()-64
        if val<0:
            val = val*100/self.negspan
        else:
            val = val*100/self.posspan
        self.valtext.SetLabel(str(val)+'%')

    def getValSpareText(self):
        return '-100%'

class SignLabelCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.normlbl,val = cdef.valinfo.get(0,'x 0').split()
        self.normval = int(val)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()-64
        if val==self.normval:
            self.valtext.SetLabel(self.normlbl)
        else:
            self.valtext.SetLabel(str(val))

    def getValSpareText(self):
        return self.normlbl

class PercentCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.minflt = int(cdef.valinfo.get(0,'0'))
        self.minval = cdef.valrange[0]
        maxflt = int(cdef.valinfo.get(1,'100'))
        self.factor = float(maxflt-self.minflt) \
            / (cdef.valrange[1]-self.minval)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = (self.slider.GetValue()-self.minval)*self.factor+self.minflt
        self.valtext.SetLabel('%.1f%%' % val)

    def getValSpareText(self):
        return '100.0%'

class InterpolCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        self.setupInterpol(cdef)
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def setupInterpol(self, cdef):
        self.interpol = []
        preval = -1
        try:
            for entry in cdef.valinfo.values():
                flt,val = entry.split()
                flt = float(flt)
                val = int(val)
                if preval>=0:
                    m = (flt-preflt)/(val-preval)
                    self.interpol.append((preval,val,preflt,m))
                preflt = flt
                preval = val
        except ValueError as error:
            showError("While setting up InterpolCtrlGUI %s:\n%s" \
                          % (cdef.name, str(error)))

    def updateValText(self):
        val = self.slider.GetValue()
        for entry in self.interpol:
            minval,maxval,b,m = entry
            if val<=maxval:
                val = (val-minval)*m+b
                self.valtext.SetLabel('%.1f' % val)
                return

    def getValSpareText(self):
        return '99.9'

class NegCtrlGUI(StdCtrlGUI):
    def __init__(self, parent, interface, cdef):
        StdCtrlGUI.__init__(self, parent, interface, cdef)

    def updateValText(self):
        val = self.slider.GetValue()
        self.valtext.SetLabel('-%d' % val)

    def getValSpareText(self):
        return '-127'
    
class ShapeCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)
        span = cdef.valrange[1] - cdef.valrange[0] + 1
        self.halfspan = span/2
        self.valmax = cdef.valrange[1]
        self.labels = [cdef.valinfo.get(i,'') for i in range(5)]

        self.slider = wx.Slider(parent=self, minValue=cdef.valrange[0],
                                maxValue=cdef.valrange[1],
                                size=(60,-1),
                                style=wx.SL_HORIZONTAL)
        self.slider.SetPageSize(span/16)
        self.valtext \
            = wx.StaticText(parent=self,
                            label=self.getValSpareText())
#                            style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
#        self.valtext.SetMinSize(self.valtext.GetSize())

        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.sizer.Add(self.slider, 0, wx.EXPAND)
        self.sizer.Add(self.valtext, 0, wx.ALIGN_CENTER)
        self.SetSizer(self.sizer)
        self.sizer.SetSizeHints(self)
#        self.Fit()

        self.updateValText()

        self.Bind(wx.EVT_SCROLL, self.onSlider)

    def onSlider(self, evt):
        if evt.GetEventType()==wx.wxEVT_SCROLL_CHANGED or \
                evt.GetEventType()==wx.wxEVT_SCROLL_THUMBTRACK:
            self.updateValText()
            self.onGUI(self.slider.GetValue())

    def setVal(self, val):
        if val!=self.slider.GetValue():
            self.slider.SetValue(val)
            self.updateValText()

    def updateValText(self):
        val = self.slider.GetValue()
        if val==0:
            text = self.labels[0]
        elif val<self.halfspan:
            text = self.labels[1] + ' %d%%' % (val*100/self.halfspan)
        elif val==self.halfspan:
            text = self.labels[2]
        elif val<self.valmax:
            text = self.labels[3] + ' %d%%' % \
                ((val-self.halfspan)*100/(self.halfspan-1))
        else:
            text = self.labels[4]
        self.valtext.SetLabel(text)
        self.Layout()

    def getValSpareText(self):
        if len(self.labels[1])>len(self.labels[3]):
            return self.labels[1]+' 99%'
        else:
            return self.labels[3]+' 99%'

class PrefixCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)
        self.setupLabels(cdef)

        self.slider = wx.Slider(parent=self, minValue=0,
                                maxValue=cdef.valrange[1],
                                size=(60,-1),
                                style=wx.SL_HORIZONTAL)
        self.valtext \
            = wx.StaticText(parent=self,
                            label=self.getValSpareText())
#                            style=wx.ALIGN_CENTER|wx.ST_NO_AUTORESIZE)
        self.valtext.SetMinSize(self.valtext.GetSize())

        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.sizer.Add(self.slider, 1)
        self.sizer.Add(self.valtext, 0, wx.ALIGN_CENTER)
        self.SetSizer(self.sizer)
        self.sizer.SetSizeHints(self)
#        self.Fit()

        self.updateValText()

        self.Bind(wx.EVT_SCROLL, self.onSlider)

    def setupLabels(self, cdef):
        try:
            self.prefixind = cdef.valrange[0]
            self.labels = [cdef.valinfo.get(i,'')
                           for i in range(self.prefixind)]
            template = cdef.valinfo.get(self.prefixind, 'x 0').split()
            self.labels.append(template[0])
            self.indexOffset = int(template[1])-self.prefixind
        except IndexError as error:
            self.labels = ['']
            self.prefixind = 0
            self.indexOffset = 0
            showError("While setting up PrefixCtrlGUI %s:\n%s" \
                          % (cdef.name, str(error)))

    def onSlider(self, evt):
        if evt.GetEventType()==wx.wxEVT_SCROLL_CHANGED or \
                evt.GetEventType()==wx.wxEVT_SCROLL_THUMBTRACK:
            self.updateValText()
            self.onGUI(self.slider.GetValue())

    def setVal(self, val):
        if val!=self.slider.GetValue():
            self.slider.SetValue(val)
            self.updateValText()

    def updateValText(self):
        val = self.slider.GetValue()
        if val<self.prefixind:
            text = self.labels[val]
        else:
            text = self.labels[self.prefixind] + ' %d' % (val+self.indexOffset)
        self.valtext.SetLabel(text)

    def getValSpareText(self):
        return self.labels[self.prefixind] + \
            ' %d' % (self.cdef.valrange[1]+self.indexOffset)

class ListCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        lbls = [cdef.valinfo.get(i,'') 
                for i in range(cdef.valrange[0], cdef.valrange[1]+1)]
        self.choice = wx.Choice(self, -1, choices=lbls)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.choice,0)
        self.SetSizer(sizer)
#        sizer.SetSizeHints(self)
        self.Bind(wx.EVT_CHOICE, self.onChoice)

    def onChoice(self, evt):
        self.onGUI(self.choice.GetSelection())

    def setVal(self, val):
        self.choice.SetSelection(val)

class CheckCtrlGUI(CtrlGUI):
    def __init__(self, parent, interface, cdef):
        CtrlGUI.__init__(self, parent, interface, cdef)

        self.checkbox = wx.CheckBox(self, -1)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.checkbox,0)
        self.SetSizer(sizer)

        self.Bind(wx.EVT_CHECKBOX, self.onCheck)

    def onCheck(self, evt):
        self.onGUI(int(self.checkbox.GetValue()))

    def setVal(self, val):
        self.checkbox.SetValue(val)


class CtrlBoxGUI(wx.Panel):
    def __init__(self, pagegui, interface, blockdef):
        wx.Panel.__init__(self, pagegui)
        self.pagegui = pagegui
        self.interface = interface
        self.blockdef = blockdef

        box = wx.StaticBox(self, -1, blockdef.name)
        self.boxsizer = wx.StaticBoxSizer(box, wx.VERTICAL)
        self.SetSizer(self.boxsizer)
        self.sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        self.sizer.AddGrowableCol(1)
        self.boxsizer.Add(self.sizer, 0, wx.EXPAND)

        self.initModeCtrl(blockdef)
        self.controllers = []
        self.ctrlguidict = {
            vxcctrl.CT_STD: StdCtrlGUI,
            vxcctrl.CT_LIST: ListCtrlGUI,
            vxcctrl.CT_SHAPE: ShapeCtrlGUI,
            vxcctrl.CT_PREFIX: PrefixCtrlGUI,
            vxcctrl.CT_SIGN: SignCtrlGUI,
            vxcctrl.CT_SIGNPERCENT: SignPercentCtrlGUI,
            vxcctrl.CT_SIGNLABEL: SignLabelCtrlGUI,
            vxcctrl.CT_PERCENT: PercentCtrlGUI,
            vxcctrl.CT_INTERPOL: InterpolCtrlGUI,
            vxcctrl.CT_CHECKBOX: CheckCtrlGUI,
            vxcctrl.CT_NEGATIVE: NegCtrlGUI,
            }
        for cdef in blockdef.ctrldefs:
            self.buildCtrl(cdef)

    def initModeCtrl(self, blockdef):
        self.modetype = blockdef.modetype
        if blockdef.modetype!=vxcctrl.MODE_NONE:
            self.interface.addListener(blockdef.cid, self.onMode)
            self.updateMode()

    def updateMode(self, modeval=None):
        if self.modetype!=vxcctrl.MODE_NONE:
            if modeval==None:
                self.mode = self.interface.getCtrl(self.blockdef.cid)
            else:
                self.mode = modeval
            if self.modetype==vxcctrl.MODE_OPENEND \
                    and self.mode>self.blockdef.valrange[0]:
                self.mode = self.blockdef.valrange[0]

    def buildCtrl(self, cdef):
        ctrl = self.ctrlguidict[cdef.ctype](self, self.interface, cdef)
        centry = (cdef, ctrl)
        self.controllers.append(centry)
        self.updateCtrl(centry)

    def updateCtrl(self, centry):
        cdef,ctrl = centry
        if self.modetype==vxcctrl.MODE_NONE \
                or self.mode in cdef.modes:
            ctrl.setVal(self.interface.getCtrl(cdef.cid))
            ctrl.Show()
            self.sizer.Add(ctrl.label, 0, 
                           wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
            self.sizer.Add(ctrl, 0, wx.EXPAND)
        else:
            ctrl.Hide()

    def updateActive(self):
        self.sizer.Clear()
        for centry in self.controllers:
            self.updateCtrl(centry)
        self.boxsizer.SetSizeHints(self)

    def update(self):
        self.updateMode()
        self.updateActive()

    def onMode(self, val):
        self.updateMode(val)
        self.updateActive()
        self.pagegui.Layout()


class CtrlPageGUI(wx.Panel):
    def __init__(self, parent, interface, pagedef):
        wx.Panel.__init__(self, parent)
        self.sizer = wx.BoxSizer(wx.HORIZONTAL)
        self.SetSizer(self.sizer)

        self.boxes = []
        for blockdef in pagedef.blocks:
            box = CtrlBoxGUI(self, interface, blockdef)
            self.sizer.Add(box, 1)
            self.boxes.append(box)
#        self.Layout()
#        self.sizer.SetSizeHints(self)

    def update(self):
        for box in self.boxes:
            box.update()
        self.Layout()

class ControllersGUI(object):
    def __init__(self, notebook, interface):
        self.notebook = notebook
        self.interface = interface
        interface.addPrgChngListener(self.onProgChange)

    def setup(self, ctrlpages):
        self.pages = []
        try:
            for pagedef in ctrlpages.pages:
                page = CtrlPageGUI(self.notebook, self.interface, pagedef)
                self.notebook.AddPage(page, pagedef.name)
                self.pages.append(page)
        except StandardError as error:
            raise
#            showError(str(error))

    def onProgChange(self):
        for page in self.pages:
            page.update()


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
        butsizer.Add(self.storebut, 0, wx.LEFT|wx.RIGHT, 20)
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
        if self.storebut.GetValue()==False:
            self.interface.proglib.setProg(pi)
        else:
            self.storebut.SetValue(False)
            self.interface.storeProg(self.storeName, pi)

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


class CtrlDefDialog(wx.Dialog):
    def __init__(self, ctrlpages):
        wx.Dialog.__init__(self, None, title="Setup Controller Definitions",
                           style=wx.RESIZE_BORDER)
        self.setupDialog(ctrlpages)
        self.save = False

    def setupDialog(self, ctrlpages):
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(sizer)

        treesizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(treesizer, 1, wx.EXPAND|wx.ALL, 5)
        self.tree = wx.TreeCtrl(self)
        self.setupTree(ctrlpages)
        treesizer.Add(self.tree, 1, wx.EXPAND|wx.RIGHT, 5)
        butsizer = wx.BoxSizer(wx.VERTICAL)
        treesizer.Add(butsizer, 1, wx.EXPAND|wx.RIGHT, 5)
        self.setupCDef(butsizer)
        self.selNone()

        butsizer = wx.BoxSizer(wx.HORIZONTAL)
        self.setupButtons(butsizer)
        sizer.Add(butsizer, 0, wx.EXPAND|wx.ALL, 5)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self.onTreeSel)
        self.Fit()
        sizer.SetSizeHints(self)

    def setupButtons(self, butsizer):
        but = wx.Button(self, -1, "Add Child")
        but.Bind(wx.EVT_BUTTON, self.onAddChild)
        butsizer.Add(but, 0)
        but = wx.Button(self, -1, "Add Before")
        but.Bind(wx.EVT_BUTTON, self.onAddBefore)
        butsizer.Add(but, 0)
        self.copybut = wx.ToggleButton(self, -1, "Copy")
        self.copybut.Bind(wx.EVT_TOGGLEBUTTON, self.onCopy)
        butsizer.Add(self.copybut, 0, wx.EXPAND)
        but = wx.Button(self, -1, "Delete")
        but.Bind(wx.EVT_BUTTON, self.onDelete)
        butsizer.Add(but, 0, wx.ALIGN_LEFT)
        butsizer.Add((1,10), 1)
        but = wx.Button(self, wx.ID_CANCEL, "Cancel")
        butsizer.Add(but, 0, wx.ALIGN_RIGHT)
        but = wx.Button(self, wx.ID_OK, "Use")
        butsizer.Add(but, 0)
        but = wx.Button(self, -1, "Save")
        but.Bind(wx.EVT_BUTTON, self.onSave)
        butsizer.Add(but, 0)

    def setupCDef(self, butsizer):
        label = wx.StaticText(self, label='Name')
        self.name = wx.TextCtrl(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.name, 1)
        butsizer.Add(sizer, 0, wx.EXPAND|wx.TOP, 5)

        label = wx.StaticText(self, label='Mode Type')
        self.modetype = wx.Choice(self, choices=['None', 'Standard',
                                                 'OpenEnd'])
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.modetype, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Ctrl Type')
        self.ctype = wx.Choice(self, 
                               choices=['Standard','List', 'Shape',
                                        'Prefix', 'Sign', 'SignPercent',
                                        'SignLabel', 'Percent', 'Interpol', 
                                        'Checkbox', 'Negative'])
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.ctype, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Ctrl Id')
        self.idpage = wx.Choice(self, 
                                choices=vxcmidi.CTRL_NAMES)
        self.idnumber = wx.SpinCtrl(self, max=127)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL)
        sizer.Add(self.idpage, 0, wx.LEFT|wx.RIGHT, 5)
        sizer.Add(self.idnumber, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Range min')
        self.rangemin = wx.SpinCtrl(self, max=127)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.rangemin, 0, wx.RIGHT, 10)
        label = wx.StaticText(self, label='max')
        self.rangemax = wx.SpinCtrl(self, max=127)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.rangemax, 0)
        butsizer.Add(sizer, 0, wx.TOP, 5)

        label = wx.StaticText(self, label='Active modes')
        self.modes = wx.TextCtrl(self)
        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(label, 0, wx.ALIGN_CENTER_VERTICAL|wx.RIGHT, 5)
        sizer.Add(self.modes, 1)
        butsizer.Add(sizer, 0, wx.EXPAND|wx.TOP, 5)

        self.labels = wx.ListCtrl(self, style=wx.LC_REPORT)
        self.labels.InsertColumn(0, '#')
        self.labels.InsertColumn(1, 'Label', width=150)
        butsizer.Add(self.labels, 1, wx.EXPAND|wx.TOP, 5)

        self.name.Bind(wx.EVT_TEXT, self.onName)
        self.modetype.Bind(wx.EVT_CHOICE, self.onModeType)
        self.ctype.Bind(wx.EVT_CHOICE, self.onType)
        self.idpage.Bind(wx.EVT_CHOICE, self.onIdPage)
        self.idnumber.Bind(wx.EVT_SPINCTRL, self.onIdNumber)
        self.rangemin.Bind(wx.EVT_SPINCTRL, self.onRangeMin)
        self.rangemax.Bind(wx.EVT_SPINCTRL, self.onRangeMax)
        self.modes.Bind(wx.EVT_TEXT, self.onModes)
        self.labels.Bind(wx.EVT_LIST_ITEM_SELECTED, self.onLabels)

    def setupTree(self, ctrlpages):
        rootid = self.tree.AddRoot("Pages")
        for page in ctrlpages.pages:
            pageid = self.tree.AppendItem(rootid, '')
            self.insertPage(pageid, page)
            self.tree.Expand(pageid)
        self.tree.Expand(rootid)

    def insertPage(self, pageitem, pagedef):
        self.tree.SetItemText(pageitem, pagedef.name)
        self.tree.SetItemPyData(pageitem, pagedef.copy())
        for block in pagedef.blocks:
            blockitem = self.tree.AppendItem(pageitem, block.name)
            self.insertBlock(blockitem, block)

    def insertBlock(self, blockitem, blockdef):
        self.tree.SetItemPyData(blockitem, blockdef.copy())
        for ctrl in blockdef.ctrldefs:
            ctrlitem = self.tree.AppendItem(blockitem, ctrl.name)
            self.insertCtrl(ctrlitem, ctrl)

    def insertCtrl(self, ctrlitem, ctrldef):
        self.tree.SetItemPyData(ctrlitem, ctrldef.copy())

    def onTreeSel(self, evt):
        item = evt.GetItem()
        obj = self.tree.GetItemPyData(item)
        if type(obj)==vxcctrl.CtrlDef:
            self.selCtrl(obj)
        elif type(obj)==vxcctrl.BlockDef:
            self.selBlock(obj)
        elif type(obj)==vxcctrl.PageDef:
            self.selPage(obj)
        else:
            self.selNone()

    def selCtrl(self, ctrldef):
        self.name.Enable()
        self.name.SetValue(ctrldef.name)
        self.modetype.Disable()
        self.ctype.Enable()
        self.ctype.SetSelection(ctrldef.ctype)
        self.idpage.Enable()
        self.idpage.SetSelection(ctrldef.cid[0])
        self.idnumber.Enable()
        self.idnumber.SetValue(ctrldef.cid[1])
        self.rangemin.Enable()
        self.rangemin.SetValue(ctrldef.valrange[0])
        self.rangemax.Enable()
        self.rangemax.SetValue(ctrldef.valrange[1])
        self.modes.Enable()
        self.modes.SetValue(ctrldef.getModeStr())
        self.updateLabels(ctrldef)
    def selBlock(self, blockdef):
        self.name.Enable()
        self.name.SetValue(blockdef.name)
        self.modetype.Enable()
        self.modetype.SetSelection(blockdef.modetype)
        self.ctype.Disable()
        self.idpage.Enable()
        self.idpage.SetSelection(blockdef.cid[0])
        self.idnumber.Enable()
        self.idnumber.SetValue(blockdef.cid[1])
        self.rangemin.Enable()
        self.rangemin.SetValue(blockdef.valrange[0])
        self.rangemax.Enable()
        self.rangemax.SetValue(blockdef.valrange[1])
        self.modes.Disable()
        self.disableLabels()
    def selPage(self, pagedef):
        self.selNone()
        self.name.Enable()
        self.name.SetValue(pagedef.name)
    def selNone(self):
        self.name.Disable()
        self.modetype.Disable()
        self.ctype.Disable()
        self.idpage.Disable()
        self.idnumber.Disable()
        self.rangemin.Disable()
        self.rangemax.Disable()
        self.modes.Disable()
        self.disableLabels()

    def disableLabels(self):
        self.labels.DeleteAllItems()
        self.labels.Disable()
    def setLabelsRange(self, ctrldef, indmin, indmax):
        self.labels.Enable()
        self.labels.DeleteAllItems()
        for i in range(indmin, indmax+1):
            self.labels.InsertStringItem(i, str(i))
            self.labels.SetStringItem(i, 1, ctrldef.valinfo.get(i,''))
    def updateLabels(self, ctrldef):
        if ctrldef.ctype==vxcctrl.CT_LIST:
            self.setLabelsRange(ctrldef,
                                ctrldef.valrange[0], ctrldef.valrange[1])
        elif ctrldef.ctype==vxcctrl.CT_SHAPE:
            self.setLabelsRange(ctrldef, 0, 4)
        elif ctrldef.ctype==vxcctrl.CT_PREFIX:
            self.setLabelsRange(ctrldef, 0, ctrldef.valrange[0])
        elif ctrldef.ctype==vxcctrl.CT_SIGNLABEL:
            self.setLabelsRange(ctrldef, 0, 0)
        elif ctrldef.ctype==vxcctrl.CT_PERCENT:
            self.setLabelsRange(ctrldef, 0, 1)
        elif ctrldef.ctype==vxcctrl.CT_INTERPOL:
            self.setLabelsRange(ctrldef, 0, 11)
        else:
            self.disableLabels()

    def onName(self, evt):
        item = self.tree.GetSelection()
        obj = self.tree.GetItemPyData(item)
        self.tree.SetItemText(item, self.name.GetValue())
        obj.name = self.name.GetValue()
    def onModeType(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.modetype = self.modetype.GetSelection()
    def onType(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.ctype = self.ctype.GetSelection()
        self.updateLabels(obj)
    def onIdPage(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setcid(page=self.idpage.GetSelection())
    def onIdNumber(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setcid(number=self.idnumber.GetValue())
    def onRangeMin(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setRange(min=self.rangemin.GetValue())
        if type(obj)==vxcctrl.CtrlDef:
            self.updateLabels(obj)
    def onRangeMax(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setRange(max=self.rangemax.GetValue())
        if type(obj)==vxcctrl.CtrlDef:
            self.updateLabels(obj)
    def onModes(self, evt):
        obj = self.tree.GetItemPyData(self.tree.GetSelection())
        obj.setModeStr(self.modes.GetValue())
    def onLabels(self, evt):
        ind = evt.GetIndex()
        item = self.labels.GetItem(ind, 1)
        dialog = wx.TextEntryDialog(None, 'Enter Label %d' % ind, 
                                    'Edit Label',
                                    item.GetText())
        if dialog.ShowModal()==wx.ID_OK:
            self.labels.SetStringItem(ind, 1, dialog.GetValue())
            obj = self.tree.GetItemPyData(self.tree.GetSelection())
            obj.valinfo[ind] = dialog.GetValue()
        dialog.Destroy()

    def onAddChild(self, evt):
        item = self.tree.GetSelection()
        obj = self.tree.GetItemPyData(item)
        if type(obj)==vxcctrl.CtrlDef:
            item = self.tree.GetItemParent(item)
        newitem = self.tree.AppendItem(item, '')
        if item==self.tree.GetRootItem():
            self.makeNewPage(newitem)
        elif type(obj)==vxcctrl.PageDef:
            self.makeNewBlock(newitem)
        else:
            self.makeNewCtrl(newitem)
        self.tree.Expand(item)
        self.tree.SelectItem(newitem)

    def onAddBefore(self, evt):
        item = self.tree.GetSelection()
        obj = self.tree.GetItemPyData(item)
        if item==self.tree.GetRootItem():
            return
        parent = self.tree.GetItemParent(item)
        item = self.tree.GetPrevSibling(item)
        if item:
            newitem = self.tree.InsertItem(parent, item, '')
        else:
            newitem = self.tree.PrependItem(parent, '')
        if type(obj)==vxcctrl.PageDef:
            self.makeNewPage(newitem)
        elif type(obj)==vxcctrl.BlockDef:
            self.makeNewBlock(newitem)
        else:
            self.makeNewCtrl(newitem)
        self.tree.SelectItem(newitem)

    def onCopy(self, evt):
        if self.copybut.GetValue()==True:
            self.copyitem = self.tree.GetSelection()
    def getCopyObj(self):
        if self.copybut.GetValue()==True:
            self.copybut.SetValue(False)
            return self.tree.GetItemPyData(self.copyitem)
        else:
            return None

    def makeNewPage(self, item):
        page = self.getCopyObj()
        if type(page)==vxcctrl.PageDef:
            self.getBlocks(self.copyitem, page)
        else:
            page = vxcctrl.PageDef('new page')
        self.insertPage(item, page)
    def makeNewBlock(self, item):
        block = self.getCopyObj()
        if type(block)==vxcctrl.BlockDef:
            self.getCtrls(self.copyitem, block)
        else:
            block = vxcctrl.BlockDef('new block')
        self.insertBlock(item, block)
    def makeNewCtrl(self, item):
        ctrl = self.getCopyObj()
        if type(ctrl)!=vxcctrl.CtrlDef:
            ctrl = vxcctrl.CtrlDef('new ctrl')
        self.insertCtrl(item, ctrl)

    def onDelete(self, evt):
        self.copybut.SetValue(False)
        item = self.tree.GetSelection()
        if item!=self.tree.GetRootItem():
            newsel = self.tree.GetNextSibling(item)
            if not newsel:
                newsel = self.tree.GetPrevSibling(item)
            self.tree.SelectItem(newsel)
            self.tree.Delete(item)

    def onSave(self, evt):
        self.save = True
        self.EndModal(wx.ID_OK)

    def getPages(self):
        ctrlpages = vxcctrl.CtrlPages()
        root = self.tree.GetRootItem()
        item, cook = self.tree.GetFirstChild(root)
        while item:
            pagedef = self.tree.GetItemPyData(item)
            ctrlpages.pages.append(pagedef)
            self.getBlocks(item, pagedef)
            item, cook = self.tree.GetNextChild(root, cook)
        return ctrlpages

    def getBlocks(self, pageitem, pagedef):
        pagedef.blocks = []
        item, cook = self.tree.GetFirstChild(pageitem)
        while item:
            blockdef = self.tree.GetItemPyData(item)
            pagedef.blocks.append(blockdef)
            self.getCtrls(item, blockdef)
            item, cook = self.tree.GetNextChild(pageitem, cook)

    def getCtrls(self, blockitem, blockdef):
        blockdef.ctrldefs = []
        item, cook = self.tree.GetFirstChild(blockitem)
        while item:
            ctrldef = self.tree.GetItemPyData(item)
            blockdef.ctrldefs.append(ctrldef)
            item, cook = self.tree.GetNextChild(blockitem, cook)


class Prefs(wx.Dialog):
    def __init__(self):
        wx.Dialog.__init__(self, None, title="Preferences")

        self.port = 'hw:1,0,1'
        self.proglib = ''
        self.ctrldef = ''
        self.midifilter = 0

        self.load(tryit=True)
        self.setupDialog()

    def setupDialog(self):
        self.sizer = wx.FlexGridSizer(cols=2, hgap=5, vgap=5)
        self.sizer.AddGrowableCol(1)
        self.SetSizer(self.sizer)

        label = wx.StaticText(self, label='Midi Port')
        self.portCtrl = wx.TextCtrl(self)
        self.sizer.Add(label, 0, 
                       wx.ALIGN_RIGHT|wx.ALIGN_CENTER_VERTICAL)
        self.sizer.Add(self.portCtrl, 0, wx.EXPAND)

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

        but = wx.Button(self, wx.ID_CANCEL, 'Cancel')
        self.sizer.Add(but, 0)
        but = wx.Button(self, wx.ID_OK, 'Ok')
        self.sizer.Add(but, 0)

    def load(self, filename='.vxcrc', tryit=False):
        try:
            rdr = csv.reader(open(filename, 'r'))
            self.port, self.proglib, self.ctrldef = rdr.next()
            self.midifilter = int(rdr.next()[0])
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
        if self.ShowModal()==wx.ID_OK:
            self.port = self.portCtrl.GetValue()
            self.proglib = self.proglibCtrl.GetValue()
            self.ctrldef = self.ctrldefCtrl.GetValue()
            self.midifilter = self.getFltValue()
            self.save()


class vxcFrame(wx.Frame):
    def __init__(self, interface):
        wx.Frame.__init__(self, parent=None, title='VirusXControl',
                          size=(800,500))
        self.interface = interface
        interface.addPrgChngListener(self.onProgChange)
        interface.addLibChngListener(self.onLibChange)
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.prefs = Prefs()
        self.limitdialog = LimitDialog(interface.proglib)

        self.statusbar = self.CreateStatusBar()
        self.statusbar.SetFieldsCount(2)
        self.setMidiMsg('disconnected')
        self.createMenu()

        self.notebook = wx.Notebook(self)
        print "proglibGUI"
        self.proglib = ProgLibGUI(self.notebook, interface)
        print "ctrlpages"
        self.initCtrlPages()
        print "controllersGUI"
        self.controllers = ControllersGUI(self.notebook, interface)
        self.setupNotebook()

        print "proglib"
        if len(self.prefs.proglib):
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
        item = menu.Append(-1, 'Store\tctrl-s')
        self.Bind(wx.EVT_MENU, self.onStore, item)
        item = menu.Append(-1, 'Append\tctrl-a')
        self.Bind(wx.EVT_MENU, self.onAppend, item)
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
        dialog = CtrlDefDialog(self.ctrlpages)
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

        print "interface"
        self.interface = vxcmidi.ProgInterface(self)
        print "frame"
        self.frame = vxcFrame(self.interface)

        print "show"
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


