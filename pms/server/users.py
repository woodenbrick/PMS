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
from google.appengine.api import mail
import models
import hashlib
import time
import random
import string
import server

class Add(webapp.RequestHandler):
    def post(self):
        name = self.request.get("name")
        salt = server.generate_salt()
        password = hashlib.sha1(self.request.get("password") + salt).hexdigest()
        email = self.request.get("email")
        timezone = self.request.get("timezone")
        #check if this user exists already
        check_user = models.User.get_by_key_name(name)
        if check_user is not None:
            return server.response(self, values={"status" : "USEREXISTS"})
        try:
            new_user = models.User(key_name=name, name=name, password=password,
                                   email=email, timezone=timezone, salt=salt)
            new_user.put()
            server.response(self)
        except db.BadValueError, e:
            server.response(self, values={"status" : "ERROR -" + str(e)})

class List(webapp.RequestHandler):
    def get(self):
        users = models.User.all()
        server.response(self, {"status" : "OK", "users" : users}, "userlist")

class Groups(webapp.RequestHandler):
    """Get a list of groups that a user is a member of"""
    def get(self, user):
        user = models.User.get_by_key_name(user)
        if user is None:
            return server.response(self, values={"status" : "NOUSER"})
        groups = models.GroupMember.all().filter("user =", user)
        server.response(self, {"status" : "OK", "groups" : groups,
                               "user" : user, }, template="usr-groups")
        
class ResetPasswordPart1(webapp.RequestHandler):
    """recieve a new password from user and send out an activation link to their email"""
    
    def post(self):
        user = models.User.all().filter("email =", self.request.get("email")).get()
        if user is None:
            return server.response(self, values={"status" : "NOUSER"})
        password = self.request.get("password")
        activation_code = server.generate_salt()
        temp = models.TempPassword.get_by_key_name(user.name)
        if temp is None:
            temp = models.TempPassword(key_name=user.name, user=user, temp_pass=password,
                                       activation_link=activation_code,
                                       time=time.time())
        else:
            temp.activation_link = activation_code
            temp.temp_pass = password
            temp.time = time.time()
        temp.put()

        message = mail.EmailMessage(sender="wodemoneke@gmail.com",
                            subject="Password change")
        message.to = "%s <%s>" % (user.name, user.email)
        message.body = """
        Dear %s,
        You, or someone pretending to be you has asked for a password change.
        To complete the change please follow this link:
        
        http://zxvf.appspot.com/usr/%s/changepass/%s
        
        This link is valid for 2 days.
        
        If you didn't request a password change, please disregard this message.""" % (
            user.name, user.name, activation_code)
        message.send()
        server.response(self)
        
class ResetPasswordPart2(webapp.RequestHandler):
    """Check that the activation link is correct, and change password"""
    
    def get(self, name, activation_code):
        user = models.User.get_by_key_name(name)
        if user is None:
            return server.response(self, {"status" : "NOUSER"}, "password_change", content="html")
        temp = models.TempPassword.get_by_key_name(user.name)
        if temp is None:
            return server.response(self, {"status" : "OUTDATED"}, "password_change", content="html")
        if temp.time > time.time():
            return server.response(self, {"status" : "BADTIME"}, "password_change", content="html")
        if temp.activation_link != activation_code:
            return server.response(self, {"status" : "BADAUTH"}, "password_change", content="html")
        user.password = hashlib.sha1(temp.temp_pass + user.salt).hexdigest()
        user.put()
        temp.delete()
        server.response(self, template="password_change", content="html")
        
class ChangeAvatar(webapp.RequestHandler):
    def post(self):
        user, user_data = server.is_valid_key(self)
        if not user:
            return server.response(self, user_data)
        users_avatar = models.UserAvatar.get_by_key_name(user.name)
        if users_avatar is None:
            users_avatar = models.UserAvatar(key_name=user.name)
        users_avatar.avatar = str(self.request.get("avatar"))
        users_avatar.user = user
        users_avatar.upload_time = time.time()
        users_avatar.put()
        return server.response(self)
        
class RetrieveAvatar(webapp.RequestHandler):
    def get(self, useravatar):
        #user, user_data = server.is_valid_key(self)
        #if user is False:
        #    return server.response(self, values={"status" : user_data})
        req = models.UserAvatar.get_by_key_name(useravatar)
        if req is None:
            return server.response(self, values={"status" : "NOUSER"})
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write(req.avatar)
        #return server.response(self, values={"status" : "OK", "avatar" : req},
        #                       template='avatar', content='png')