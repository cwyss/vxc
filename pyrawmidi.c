
#include <Python.h>
#include <alsa/asoundlib.h>


static snd_rawmidi_t *MidiIn = NULL;
static snd_rawmidi_t *MidiOut = NULL;

#define FILTER_ECHO_MASK		0x000F
#define FILTER_DISCARD_MASK		0x0F00
#define FILTER_NOTE			0x0101
#define FILTER_CHNPRESS			0x0202
#define FILTER_PITCH			0x0404
#define FILTER_MOD			0x0808

static int filter = 0;


static PyObject *midiexcept(char *errtempl, int status) {
    char errstr[200];
    sprintf(errstr, errtempl, snd_strerror(status));
    PyErr_SetString(PyExc_IOError, errstr);
    return NULL;
}

static PyObject *midiexcept2(char *errtempl, const char *text, int status) {
    char errstr[200];
    sprintf(errstr, errtempl, text, snd_strerror(status));
    PyErr_SetString(PyExc_IOError, errstr);
    return NULL;
}

static PyObject *pyrm_open(PyObject *self, PyObject *args) {
    int status;
    const char *port;

    if(MidiIn!=NULL)
	return midiexcept("midi already openend", 0);

    if(!PyArg_ParseTuple(args, "s", &port))
	return NULL;

    status = snd_rawmidi_open(&MidiIn, &MidiOut, port, 
			      SND_RAWMIDI_SYNC|SND_RAWMIDI_NONBLOCK);
    if(status<0)
	return midiexcept2("error opening midi port '%s': %s", port, status);

    status = snd_rawmidi_nonblock(MidiOut, 0); /* set blocking mode */
    if(status<0)
	return midiexcept("error setting up midi: %s", status);

    Py_RETURN_NONE;
}

static PyObject *pyrm_close(PyObject *self, PyObject *args) {
    if(MidiIn!=NULL) {
	snd_rawmidi_close(MidiIn);
	MidiIn = NULL;
    }
    if(MidiOut!=NULL) {
	snd_rawmidi_close(MidiOut);
	MidiOut = NULL;
    }

    Py_RETURN_NONE;
}

static int pylist2buffer(PyObject *list, unsigned char **bufptr) {
    int i, buflen;
    unsigned char *buffer;
    PyObject *item;

    if(!PyList_Check(list)) {
	PyErr_SetString(PyExc_TypeError, "expected list of integers");
	return -1;
    }

    buflen = PyList_Size(list);

    if( !(buffer=malloc(buflen)) ) {
	PyErr_NoMemory();
	return -1;
    }
    *bufptr = buffer;

    for(i=0; i<buflen; ++i) {
	item = PyList_GetItem(list, i);
	if(!PyInt_Check(item)) {
	    PyErr_SetString(PyExc_TypeError, "expected list of integers");
	    free(buffer);
	    return -1;
	}
	buffer[i] = PyInt_AS_LONG(item);
    }

    return buflen;
}

static int midiwrite(unsigned char *buffer, int buflen) {
    int status;

    if(MidiOut==NULL) {
	midiexcept("midi not opened", 0);
	return 0;
    }

    status = snd_rawmidi_write(MidiOut, buffer, buflen);

    if(status<0) {
	midiexcept("error writing midi: %s", status);
	return 0;
    }
    return 1;
}

static PyObject *pyrm_write(PyObject *self, PyObject *args) {
    PyObject *datalist;
    int succ, buflen;
    unsigned char *buffer;
 
    if(!PyArg_ParseTuple(args, "O", &datalist))
        return NULL;

    buflen = pylist2buffer(datalist, &buffer);
    if(buflen<0)
	return NULL;

    succ = midiwrite(buffer, buflen);
    free(buffer);

    if(succ)
	Py_RETURN_NONE;
    else
	return NULL;
}

static PyObject *buffer2pylist(unsigned char *buffer, int buflen) {
    PyObject *list, *item;
    int i;

    if( !(list=PyList_New(buflen)) )
	return NULL;

    for(i=0; i<buflen; ++i) {
	item = PyInt_FromLong(buffer[i]);
	PyList_SET_ITEM(list, i, item);
    }

    return list;
}

static int getmidicmdlen(unsigned char cb) {
    switch(cb&0xF0) {
    case 0x80: return 3;	/* note off */
    case 0x90: return 3;	/* note on */
    case 0xB0: return 3;	/* controller */
    case 0xD0: return 2;	/* channel pressure */
    case 0xE0: return 3;	/* pitch bend */
    default: return 0;
    }
}

static int filtercmd(unsigned char *buffer, int buflen) {
    int cb = buffer[0];
    int cb0 = cb&0xF0;
    int b1;
    int f = 0;

    if(cb0==0x80 || cb0==0x90)		/* note */
	f = filter & FILTER_NOTE;
    else if(cb0==0xD0)			/* channel pressure */
	f = filter & FILTER_CHNPRESS;
    else if(cb0==0xE0)			/* pitch bend */
	f = filter & FILTER_PITCH;
    else if(cb0==0xB0) {		/* controller */
	b1 = buffer[1];
	if(b1==0x01)			/* mod wheel */
	    f = filter & FILTER_MOD;
    }

    if(f & FILTER_ECHO_MASK) {
	if(!midiwrite(buffer, buflen))
	    return -1;
	else
	    return 1;
    }
    else if(f & FILTER_DISCARD_MASK)
	return 1;
    else
	return 0;
}

#define READLOOP_BUFLEN		10000

static int midireadloop(unsigned char *buffer) {
    int bufpos=0, cmdlen;
    unsigned char sb;
    int status;

    while(MidiIn!=NULL) {
	Py_BEGIN_ALLOW_THREADS
	status = snd_rawmidi_read(MidiIn, &sb, 1);
	Py_END_ALLOW_THREADS
	if(status<0) {
	    midiexcept("error reading midi: %s", status);
	    return -1;
	}

	buffer[bufpos++] = sb;

	if(sb&0x80) {				/* received command byte */
	     if(buffer[0]==0xF0 && sb==0xF7) {	/* SysEx End */
		 cmdlen = bufpos;
	     }
	     else if(bufpos>1) {	    /* previous command incomplete */
		 buffer[0] = sb;
		 bufpos = 1;
		 cmdlen = getmidicmdlen(sb);
	     }
	     else
		 cmdlen = getmidicmdlen(sb);
	}

	if(bufpos==cmdlen) {			/* command complete */
	    status = filtercmd(buffer, bufpos);
	    if(status==0)
		return bufpos;
	    else if(status<0)
		return -1;
	    bufpos = 0;
	}
    }

    midiexcept("midi closed", 0);
    return -1;
}

static PyObject *pyrm_read(PyObject *self, PyObject *args) {
    unsigned char buffer[READLOOP_BUFLEN];
    int buflen;

    if(MidiOut==NULL)
    	return midiexcept("midi not opened", 0);
    if(!PyArg_ParseTuple(args, ""))
        return NULL;

    buflen = midireadloop(buffer);

    if(buflen<0)
	return NULL;
    else
	return buffer2pylist(buffer, buflen);
}

static PyObject *pyrm_setfilter(PyObject *self, PyObject *args) {
    int fecho, fdiscard;

    if(!PyArg_ParseTuple(args, "ii", &fecho, &fdiscard))
	return NULL;

    fecho &= FILTER_ECHO_MASK;
    fdiscard = (fdiscard<<8) & FILTER_DISCARD_MASK;
    filter = fecho | fdiscard;

    Py_RETURN_NONE;
}

static PyObject *pyrm_out(PyObject *self, PyObject *args) {
    printf("hallo\n");

    Py_RETURN_NONE;
}

static PyObject *pyrm_wait(PyObject *self, PyObject *args) {
    Py_BEGIN_ALLOW_THREADS
    sleep(2);
    Py_END_ALLOW_THREADS

    Py_RETURN_NONE;
}

static PyMethodDef RawMidiMethods[] = {
    {"open", pyrm_open, METH_VARARGS, "open midi port"},
    {"close", pyrm_close, METH_VARARGS, "close midi port"},
    {"write", pyrm_write, METH_VARARGS, "write midi data"},
    {"read", pyrm_read, METH_VARARGS, "read midi data"},
    {"setfilter", pyrm_setfilter, METH_VARARGS, "set filter mode"},
    {"out", pyrm_out, METH_VARARGS, "test output"},
    {"wait", pyrm_wait, METH_VARARGS, "wait 2 secs"},
    {NULL, NULL, 0, NULL}
};


PyMODINIT_FUNC initpyrawmidi(void) {
    Py_InitModule("pyrawmidi", RawMidiMethods);
}
