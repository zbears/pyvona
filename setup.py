#!/usr/bin/env python
# encoding: utf-8

import os
from distutils.core import setup


print "Welcome to Pyvona setup. Installing Pyvona..."

setup(name='pyvona',
      version='0.22',
      description='Python text-to-speech IVONA Wrapper',
      author='Zachary Bears',
      author_email='bears.zachary@gmail.com',
      url='http://www.zacharybears.com/pyvona',
      py_modules=['pyvona'],
      install_requires=['requests']
    )

print "Please visit zacharybears.com/pyvona for tutorials, feature requests, and questions."
