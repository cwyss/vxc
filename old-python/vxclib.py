
"""  VirusXControl -- program library


"""


SINGLE_LEN = 512
SINGLE_OLDLEN = 256

SINGLE_NAME_START = 128+112
SINGLE_NAME_LEN = 10
SINGLE_NAME_END = SINGLE_NAME_START + SINGLE_NAME_LEN


class SingleProgError(Exception):
    def __init__(self):
        Exception.__init__(self, 'invalid single program length')


class SingleProg(object):
    def __init__(self, single=None):
        if type(single)==list:
            if len(single)==SINGLE_LEN:
                self.buf = single
            elif len(single)==SINGLE_OLDLEN:
                self.buf = single
                self.buf.extend([0] * SINGLE_OLDLEN)
            else:
                raise SingleProgError
            self.makeName()
        elif type(single)==SingleProg:
            self.buf = list(single.buf)
            self.makeName()
        elif single==None:
            self.buf = [0] * SINGLE_LEN
            self.name = '-Void-'
        else:
            raise TypeError('expected list or SingleProg object')

    def makeName(self):
        name = ''
        for b in self.buf[SINGLE_NAME_START:SINGLE_NAME_END]:
            name += chr(b)
        self._name = name

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, name):
        self._name = ''
        for i in range(SINGLE_NAME_LEN):
            if i<len(name):
                self.buf[SINGLE_NAME_START+i] = ord(name[i])
                self._name += name[i]
            else:
                self.buf[SINGLE_NAME_START+i] = ord(' ')
                self._name += ' '

        
SINGLE_BANK_LEN = 128

class SingleBank(object):
    def __init__(self, name, proglist=None, initprog=None):
        self.name = name
        if type(proglist)==list:
            self._proglist = proglist[0:SINGLE_BANK_LEN]
        elif proglist==None:
            self._proglist = []
        else:
            raise TypeError('proglist arg: expected list or None')
        
        if len(self._proglist)<SINGLE_BANK_LEN:
            if initprog==None:
                initprog = SingleProg()
            for i in range(len(self._proglist), SINGLE_BANK_LEN):
                self._proglist.append(SingleProg(initprog))

    def __getitem__(self, ind):
        if type(ind)!=int:
            raise TypeError('only integer indices')
        return self._proglist[ind]

    def __setitem__(self, ind, val):
        if type(ind)!=int:
            raise TypeError('only integer indices')
        self._proglist[ind] = SingleProg(val)

