#!/usr/bin/env python
from distutils.core import setup
import py2exe

setup(
name='PMS',
version='0.01',
packages=['client', 'poster'],
scripts=['pms'],

windows=[{
    'script': 'pms',
    'icon_resources': [(1, 'client/images/event-notify-blue.ico')]
    }],

data_files=[
('glade', [
  'client/glade/main.glade',
  'client/glade/group.glade',
  'client/glade/login.glade',
  'client/glade/preferences.glade',
  ]),

('images', [
  'client/images/avatar-default.png',
  'client/images/bug.png',
  'client/images/event-notify-blue.ico',
  'client/images/event-notify-red.ico',
  'client/images/groups.png',
  'client/images/member.png',
  'client/images/blank.png',
  'client/images/password.png',
  'client/images/refresh.png']),],

options = {
'py2exe' : {
  'packages': 'encodings',
  'includes': 'cairo, pango, pangocairo, atk, gobject',
},
#'sdist': {
#  'formats': 'zip',
#}
}
)
