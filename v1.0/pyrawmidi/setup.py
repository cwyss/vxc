#!/usr/bin/env python

from distutils.core import setup, Extension

module = Extension("pyrawmidi", sources=["pyrawmidi.c"],
                   libraries=["asound"])

setup(name = "packname", version = "0.1",
      description = "rawmidi support",
      ext_modules = [module])
