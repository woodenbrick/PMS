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
    """Returns OK if successful or ERROR\nError details if unsuccessful"""
    def post(self):
        self.response.headers['Content-Type'] = 'text/plain'
        name = self.request.get("name")
        salt = server.generate_salt()
        password = hashlib.sha1(self.request.get("password") + salt).hexdigest()
        email = self.request.get("email")
        timezone = self.request.get("timezone")
        #check if this user exists already
        check_user = models.User.get_by_key_name(name)
        if check_user is not None:
            return server.response(self, response="USEREXISTS")
        try:
            new_user = models.User(key_name=name, name=name, password=password,
                                   email=email, timezone=timezone, salt=salt)
            new_user.put()
            server.response(self)
        except db.BadValueError, e:
            response("ERROR\n" + str(e))

class List(webapp.RequestHandler):
    def get(self):
        users = models.User.all()
        for user in users:
            server.response(self, user.to_xml(), False)
        #server.response(self, users, False)
        #for user in users:
        #    self.response.out.write(user.name + "\n" + user.salt + "\n" + user.password +"\n\n")


class Groups(webapp.RequestHandler):
    """Get a list of groups that a user is a member of"""
    def get(self):
        user, userdata = server.is_valid_key(self)
        groups = models.GroupMember.all().filter("user =", user)
        server.response(self, "OK\n")
        for group in groups:
            server.response(self, group.group.name + ",", header=False)