#!/usr/bin/env python
import os

class Settings(object):
    NAME = "pms"
    VERSION = "0.10"
    AUTHOR = "Daniel Woodhouse"
    EMAIL = "wodemoneke@gmail.com"
    WEBSITE = "https://launchpad.net/pms-client/"
    WEBSITE_BUG = "https://launchpad.net/pms-client/+filebug"
    LICENCE = """
pms is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

pms is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with pms.  If not, see http://www.gnu.org/licenses/
"""
    FACEBOOK_TIMEOUT = 400000
    AVATAR_CHECK_TIMEOUT = 600000
    NICETIME_TIMOUT = 60000
    #these will be tweaked at runtime if necessary,
    #however for testing I have included some defaults
    HOME = os.environ['HOME'] + "/.eventnotify/"
    HOMEMAIN = os.environ['HOME']
    IMAGES = "images/"
    GLADE = "glade/"
    LOGGING_LEVEL = None
    LOGO1 = "images/logo1.png"
    LOGO2 = "images/log2.png"
    LOGO1_SMALL = "images/logo1_64.png"
    SERVER = "http://wor-creator.appspot.com" 
    USERNAME = ""
