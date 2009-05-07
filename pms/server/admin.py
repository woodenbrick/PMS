# Copyright 2009 Daniel Woodhouse
#
#This file is part of pms.
#
#pms is free software: you can redistribute it and/or modify
#it under the terms of the GNU General Public License as published by
#the Free Software Foundation, either version 3 of the License, or
#(at your option) any later version.
#
#pms is distributed in the hope that it will be useful,
#but WITHOUT ANY WARRANTY; without even the implied warranty of
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#GNU General Public License for more details.
#
#You should have received a copy of the GNU General Public License
#along with pms.  If not, see http://www.gnu.org/licenses/
from google.appengine.ext import webapp
from google.appengine.ext import db
import models
import hashlib
import time
import random
import string
import server

#ADMIN CLASSES
#These are for testing purposes only and should be removed on deployment
#or require password


class AllMessages(webapp.RequestHandler):
    """Test class for checking all messages"""
    def get(self):
        messages = models.Message.all()
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("Messages\n")
        for mess in messages:
            self.response.out.write(mess.user.name + " " + mess.comment + mess.group.name + "\n")
