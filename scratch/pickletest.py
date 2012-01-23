
import pickle


class A(object):
    def __init__(self, name):
        self.name = name
        self.zahl = 15

    def getName(self):
        return self.name


def create(name):
    a = A(name)

    file = open(name+'.pck', 'w')
    pickle.dump(a, file)
    file.close()

def read(name):
    file = open(name+'.pck', 'r')
    a = pickle.load(file)

    print a.getName()

def readdir(name):
    file = open(name+'.pck', 'r')
    a = pickle.load(file)

    print dir(a)

def create2(name):
    a = A(name)
    b = A('mehr daten')

    file = open(name+'.pck', 'w')
    pickle.dump(a, file)
    pickle.dump(b, file)
    file.close()

def read2(name):
    file = open(name+'.pck', 'r')
    a = pickle.load(file)
    b = pickle.load(file)

    print a.getName(), b.getName()

def create3(name):
    a = A(name)
    b = A('mehr daten')

    file = open(name+'.pck', 'w')
    pickler = pickle.Pickler(file)
    pickler.dump(a)
    pickler.dump(b)

def read3(name):
    file = open(name+'.pck', 'r')
    unp = pickle.Unpickler(file)
    a = unp.load()
    b = unp.load()

    print a.getName(), b.getName()
