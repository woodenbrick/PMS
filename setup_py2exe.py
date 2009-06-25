#!/usr/bin/env python
from distutils.core import setup
import py2exe
import os
import glob
import sys
f = open("shite", "w")
sys.stdout = f
src_dir = "client"
glade = glob.glob(os.path.join(src_dir, "glade", "*.glade"))
images = glob.glob(os.path.join(src_dir, "images", "*"))


setup(
name='PMS',
version='0.01',
packages=['client', 'client.libs', 'client.libs.poster'],
scripts=['bin/pms'],

windows=[{
    'script': 'bin/pms',
    'icon_resources': [(1, 'client/images/logo1.png')]
    }],

data_files=[
('glade', glade),

('images', images),],

options = {
'py2exe' : {
  'packages': 'encodings',
  'includes': 'cairo, pango, pangocairo, atk, gobject',
  'excludes' : ['_ssl', 'inspect', 'pdb', 'difflib', 'doctest', 'locale', 'calendar']
},
#'sdist': {
#  'formats': 'zip',
#}

}
)
