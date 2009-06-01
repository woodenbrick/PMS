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
from google.appengine.ext.webapp import template
from google.appengine.api import memcache
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
            return server.response(self, {"values" : "BADAUTH"})
        password_required = True if self.request.get("password") != "" else False
        group = self.request.get("group")
        if group == "":
            return server.response(self, {"status" : "MISSINGVALUES"})
        if password_required:
            salt = server.generate_salt()
            password = hashlib.sha1(self.request.get("password") + salt).hexdigest()
        else:
            password = None
            salt = None
        description = self.request.get("description")
        check = models.Group.get_by_key_name(group)
        if check is not None:
            return server.response(self, {"status" : "GROUPEXISTS"})
        new_group = models.Group(key_name=group, name=group, owner=user,
                                 description=description,
                                 password_required=password_required,
                                 password=password, salt=salt)
        new_group.put()
        memcache.delete("user-groups" + user.name)
        member = models.GroupMember(group=new_group, user=user)
        member.put()
        server.response(self)
    
class Join(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        if not user:
            return server.response(self, {"status": userdata})
        if self.request.get("group") == "":
            return server.response(self, {"status" : "MISSINGVALUES"})
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, {"status" : "NOTGROUP"})
        if group.password_required:
            password = hashlib.sha1(self.request.get("password") + group.salt).hexdigest()
            if password != group.password:
                return server.response(self, {"status" : "BADPASS"})
        member = models.GroupMember(group=group, user=user)
        member.put()
        memcache.delete("user-groups" + user.name)
        return server.response(self)

class Leave(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, {"status" : "NOGROUP"})
        member = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
        if member is None:
            return server.response(self, {"status" : "NONMEMBER"})
        #owners cant leave their group
        if user.name == group.owner.name:
            return server.response(self, {"status" : "ISOWNER"})
        member.delete()
        memcache.delete("user-groups" + user.name)
        server.response(self)
        
class Delete(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, {"status" : "NOGROUP"})
        if models.GroupMember.all().filter("group =", group).count(2) > 1:
            return server.response(self, {"status" : "HASMEMBERS"})
        member = models.GroupMember.all().filter("group =", group).get()
        member.delete()
        group.delete()
        memcache.delete("user-groups" + user.name)
        server.response(self)


class ChangeOwner(webapp.RequestHandler):
    def post(self):
        user, userdata = server.is_valid_key(self)
        group = models.Group.get_by_key_name(self.request.get("group"))
        if group is None:
            return server.response(self, {"status" : "NOGROUP"})
        if user.name != group.owner.name:
            return server.response(self, {"status" : "NOTOWNER"})
        owner = models.GroupMember.all().filter("group =", group).filter("user =", user).get()
        new_owner = models.User.get_by_key_name(self.request.get("newowner"))
        is_member = models.GroupMember.all().filter("group =", group).filter("user = ", new_owner).get()
        if is_member is None:
            return server.response(self, {"status" : "NONMEMBER"})
        owner.owner = new_owner
        owner.put()
        server.response(self)

class List(webapp.RequestHandler):
    def get(self):
        """Returns a list of all groups"""
        groups = models.Group.all()
        server.response(self, values={"status" : "OK", "groups" : groups},
                        template='groups')

    
class Members(webapp.RequestHandler):
    def get(self, groupname):
        """Get a list of members for a particular group"""
        group = models.Group.get_by_key_name(groupname)
        if group is None:
            return server.response(self, {"status" : "NOTGROUP"})
        members = models.GroupMember.all().filter("group =", group)
        server.response(self, {"status" : "OK", "members" : members}, template="groupmembers")
        