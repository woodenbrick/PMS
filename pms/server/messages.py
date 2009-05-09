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

class New(webapp.RequestHandler):
    def post(self):
        """
        Add a new message to group
        Requires: name of user, session_key, message, group(s), IP
        """
        user, user_data = server.is_valid_key(self)
        if user:
            group = self.request.get("group")
            message = self.request.get("message")
            if message == "" or group == "":
                return server.response(self, response="MISSINGVALUES")
            group = models.Group.get_by_key_name(group)
            member = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
            if member is None:
                return server.response(self, response="NONMEMBER")
            mess = models.Message(user=user, group=group, comment=message)
            mess.put()
            server.response(self)
        else:
            server.response(self, user_data)
    
class Check(webapp.RequestHandler):
    """
    Checks the server for new messages
    Requires: name of user, session_key, timestamp of last msg recieved, IP
    """
    def post(self):
        user, user_data = server.is_valid_key(self)
        grouplist = self.request.get("groups").split(",")
        while True:
            try:
                grouplist.remove("")
            except ValueError:
                break
        groups = models.Group.get_by_key_name(grouplist)
        if user:
            query = models.Message.gql("where group IN :1", groups).fetch(100)
            server.response(self, response="OK\n")
            for line in query:
                server.response(self, response=line.comment + " " + str(line.date) +
                                " " + line.group.name + " " + line.user.name + "\n", header=False)


