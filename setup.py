#!/usr/bin/python

from distutils.core import setup
import os
import glob 

PROGRAM_NAME = 'pms-client'
VERSION = '0.10'

glade = glob.glob(os.path.join("pms", "client", "glade", "*.glade"))
images = glob.glob(os.path.join("pms", "client", "images", "*"))
desc = """Desktop client for private microblogging service"""
long_desc = """ Allows the user to keep in touch with groups of people. Groups can be password protected. Also includes Facebook status update and retrieval."""

setup ( name = PROGRAM_NAME,
        version = VERSION,
        description = desc,
        long_description = long_desc,
        author = 'Daniel Woodhouse',
        author_email = 'wodemoneke@gmail.com',
	    license = 'GPLv3',
        platforms = ['Linux'],
        url = 'http://github.com/woodenbrick/pms/tree',
        packages = ['pms.client', 'pms.client.poster', 
                    'pms.client.facebook'],
        data_files = [
            ('share/applications/', ['pms.desktop']),
            ('share/pms/glade', glade),
            ('share/pms/images', images),
            ('bin/', ['bin/pms'])],
)
