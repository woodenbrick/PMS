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
                return server.response(self, {"status" : "MISSINGVALUES"})
            group = models.Group.get_by_key_name(group)
            member = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
            if member is None:
                return server.response(self, {"status" : "NONMEMBER"})
            mess = models.Message(user=user, group=group, comment=message)
            mess.put()
            server.response(self)
        else:
            server.response(self, {"status" : "BADAUTH"})
    
class Check(webapp.RequestHandler):
    """
    Checks the server for new messages
    Requires: name of user, session_key, timestamp of last msg recieved, IP
    groups that you want
    """
    def post(self):
        user, user_data = server.is_valid_key(self)
        if not user:
            server.response(self, {"status" : "BADAUTH"})
        import datetime
        t = time.gmtime(float(self.request.get("time")))
        dtime = datetime.datetime(*(t[0:6]))
        groups = self.request.get("groups").split(",")
        all_messages = []
        for group in groups:
            g = models.Group.get_by_key_name(group)
            messages = models.Message.all().filter("group =", g).filter("date >", dtime).fetch(100)
            all_messages.extend(messages)  
        server.response(self, values={"status" : "OK", "messages" : all_messages}, template="messages")

