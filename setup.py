#!/usr/bin/env python
# encoding: utf-8

import os
from distutils.core import setup

setup(name='pyvona',
      version='1.0',
      description='Python text-to-speech IVONA Wrapper',
      author='Zachary Bears',
      author_email='bears.zachary@gmail.com',
      url='http://www.zacharybears.com/pyvona',
      py_modules=['pyvona'],
      install_requires=['requests']
    )

