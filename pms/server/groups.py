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

class Add(webapp.RequestHandler):
    def post(self):
        user, user_data = server.is_valid_key(self)
        if not user:
            return server.response(self, user_data)
        password = self.request.get("password")
        password_required = True if self.request.get("passreq") == "1" else False
        group = self.request.get("group")
        if group == "":
            return server.response(self, "MISSINGVALUES")
        salt = self.request.get("salt")
        check = models.Group.get_by_key_name(group)
        if check is not None:
            return server.response(self, "GROUPEXISTS")
        new_group = models.Group(key_name=group, name=group, owner=user,
                                 password_required=password_required,
                                 password=password, salt=salt)
        new_group.put()
        member = models.GroupMember(group=new_group, user=user)
        member.put()
        server.response(self)
    
class Join(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        if not user:
            return server.response(self, userdata)
        if self.request.get("group") == "":
            return server.response(self, response="MISSINGVALUES")
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, response="NOTGROUP")
        if group.password_required:
            password = hashlib.sha1(self.request.get("password") + group.salt).hexdigest()
            if password != group.password:
                return server.response(self, response="BADAUTH" + " " +group.password + " " + group.salt)
        member = models.GroupMember(group=group, user=user)
        member.put()
        return server.response(self)

class Leave(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, response="NOGROUP")
        member = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
        if member is None:
            return server.response(self, response="NONMEMBER")
        #owners cant leave their group
        if user.name == group.owner.name:
            return server.response(self, response="ISOWNER")
        member.delete()
        server.response(self)
        
class Delete(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, response="NOGROUP")
        if models.GroupMember.all().filter("group =", group).count(2) > 1:
            return server.response(self, response="HASMEMBERS")
        member = models.GroupMember.all().filter("group =", group).get()
        member.delete()
        group.delete()
        server.response(self)


class ChangeOwner(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, response="NOGROUP")
        if user.name != group.owner.name:
            return server.response(self, response="NOTOWNER")
        owner = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
        new_owner = models.User.get_by_key_name(self.request.get("newowner"))
        is_member = models.GroupMember.all().filter("group =", group).filter("user = ", new_owner).get()
        if is_member is None:
            return server.response(self, response="NONMEMBER")
        owner.owner = new_owner
        owner.put()
        server.response(self)

class List(webapp.RequestHandler):
    def post(self):
        """Returns a list of all groups"""
        groups = models.Group.all()
        for group in groups:
            server.response(self, response="%s %s %s\n" % (group.name, group.owner.name,
                                                      str(group.password_required)),
                                                      header=False)

    
class Members(webapp.RequestHandler):
    def post(self):
        """Get a list of members for a particular group"""
        if self.request.get("group") == "":
            return server.response(self, "MISSINGVALUES")
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, "NOTGROUP")
        members = models.GroupMember.all().filter("group =", group)
        for member in members:
            server.response(self, response=member.user.name + "\n", header=False)