#messages.py
"""
For adding and retrieving messages
"""
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

import logging
import hashlib
import time
import random
import string

import server
import models
from cgi import escape

class New(webapp.RequestHandler):
    """
    Mapping /msg/add
    """
    def post(self):
        """
        Add new messages to the specified group
         :Parameters:
          - `session_data`: See `pms.server.server.is_valid_key`
          - `group`: The group the message is been sent to
          - `message`: The message to be added
        """
        user, user_data = server.is_valid_key(self)
        if user:
            group_name = escape(self.request.get("group"))
            message = escape(self.request.get("message"))
            if message == "" or group_name == "":
                return server.response(self, {"status" : "MISSINGVALUES"})
            group = memcache.get("group-" + group_name)
            if group is None:
                group = models.Group.get_by_key_name(group_name)
            if group is None:
                return server.response(self, {"status" : "NOTGROUP"})
            member = memcache.get("member-" + user.name + group.name)
            if member is None:
                member = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
            if member is None:
                return server.response(self, {"status" : "NONMEMBER"})
            #cache member and group
            memcache.set("member-" + user.name + group.name, member)
            memcache.set("group-" + group.name, group)
            mess = models.Message(user=user, group=group, comment=message, date=int(time.time()))
            mess.put()
            #cache this date for other users
            memcache.set("last_message-" + group.name, mess.date)
            server.response(self)
        else:
            server.response(self, {"status" : "BADAUTH"})
    
class Check(webapp.RequestHandler):
    """
    :Mapping: /msg/check
    """
    def post(self):
        """
        Checks the server for new messages
         :Parameters:
          - session_data: See `pms.server.server.is_valid_key`
          - time: The timestamp of the last message recieved
        """
        user, user_data = server.is_valid_key(self)
        if not user:
            return server.response(self, {"status" : "BADAUTH"})
        last_checked = int(self.request.get("time"))
        membership = memcache.get("user-groups" + user.name)
        if membership is None:
            membership = models.GroupMember.all().filter("user =", user)
            memcache.set("user-groups" + user.name, membership)
        all_messages = []
        for member in membership:
            logging.info("Checking %s" % member.group.name)
            if member.group.name == "Facebook":
                continue
            last_message = memcache.get("last_message-" + member.group.name)
            logging.info("Last stored message in memcache: %s" % last_message)
            if last_message is not None:
                logging.info("%s : %s" % (last_message, last_checked))
                if last_message == "No new" or int(last_message) == last_checked:
                    continue
            logging.info("Using datastore for %s" % member.group.name)
            logging.info("Last check: %s" % last_checked)
            messages = models.Message.all().filter("group =", member.group).filter(
                "date >", last_checked).order("-date").fetch(100)
            for message in messages:
                logging.info("date: %s" % message.date)
            if len(messages) > 0:
                logging.info("We have %s messages, setting memcache" % len(messages))
                memcache.set("last_message-" + member.group.name, float(messages[0].date))
            else:
                logging.info("No new messages")
                memcache.set("last_message-" + member.group.name, "No new")
            all_messages.extend(messages)
        server.response(self, values={"status" : "OK", "messages" : all_messages}, template="messages")

