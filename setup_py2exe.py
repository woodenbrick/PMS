#!/usr/bin/env python
from distutils.core import setup
import py2exe
import os
import glob

src_dir = "client"
glade = glob.glob(os.path.join(src_dir, "glade", "*.glade"))
images = glob.glob(os.path.join(src_dir, "images", "*.png|*.ico"))
emotes = glob.glob(os.path.join(src_dir, "images", "emotes", "*"))

setup(
name='PMS',
version='0.01',
packages=['client', 'client.libs', 'client.libs.poster'],
#scripts=['pms'],

windows=[{
    'script': 'bin/pms',
    'icon_resources': [(1, 'client/images/logo1_128.ico')]
    }],

data_files=[
('glade', glade),
('images', images),
('images/emotes', emotes)
],

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
