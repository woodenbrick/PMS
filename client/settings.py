#!/usr/bin/env python

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
    FACEBOOK_TIMEOUT = 300000
    AVATAR_CHECK_TIMEOUT = 900000
    NICETIME_TIMOUT = 60000
    #these will be set at runtime
    HOME = ""
    HOMEMAIN = ""
    IMAGES = ""
    GLADE = ""
    LOGGING_LEVEL = None
    LOGO1 = ""
    LOGO2 = ""
    SERVER = "" 
    USERNAME = ""
