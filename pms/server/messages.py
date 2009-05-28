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
from google.appengine.api import memcache
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
            group_name = self.request.get("group")
            message = self.request.get("message")
            if message == "" or group_name == "":
                return server.response(self, {"status" : "MISSINGVALUES"})
            group = models.Group.get_by_key_name(group_name)
            member = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
            if member is None:
                return server.response(self, {"status" : "NONMEMBER"})
            mess = models.Message(user=user, group=group, comment=message, date=int(time.time()))
            mess.put()
            #cache this for other users
            memcache.set(group_name, mess.date)
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
            return server.response(self, {"status" : "BADAUTH"})
        last_time = int(float(self.request.get("time")))
        if self.request.get("groups") == "":
            return server.response(self, {"status" : "MISSINGVALUES"})
        groups = self.request.get("groups").split(",")
        #use memcache here
        #lets save the last message sent to a group in a variable
        # lastmsg-[groupname]
        #we can checkthis and if it is further in the past than our last check we
        #skip over this group

        all_messages = []
        for group in groups:
            lmsg = memcache.get(group)
            if lmsg is not None and lsmg < last_time:
                continue
            g = models.Group.get_by_key_name(group)
            messages = models.Message.all().filter("group =", g).filter("date >", last_time).fetch(100)
            memcache.set(group, messages[-1].date)
            all_messages.extend(messages)  
        server.response(self, values={"status" : "OK", "messages" : all_messages}, template="messages")

