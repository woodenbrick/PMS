#users.py
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
from google.appengine.api import memcache
import models
import hashlib
import time
import random
import string
import server
import logging
import re

class Add(webapp.RequestHandler):
    """
    Mapping: /usr/add
    """
    def post(self):
        """
        Creates a new user
         Parameters:
          - name: The name of the new user
          - password: A sha1 hash of the users password
          - email: A valid email address for the user
        """
        name = self.request.get("name")
        salt = server.generate_salt()
        password = hashlib.sha1(self.request.get("password") + salt).hexdigest()
        email = self.request.get("email")
        #check if this user exists already
        check_user = models.User.get_by_key_name(name)
        if check_user is not None:
            return server.response(self, values={"status" : "USEREXISTS"})
        if re.search("^\w{5,18}$", name) is None:
            return server.response(self, values={"status" : "BADUSERNAME"})   
        if re.search("^(?:[a-zA-Z0-9_'^&amp;/+-])+(?:\.(?:[a-zA-Z0-9_'^&amp;/+-])+)*@(?:(?:\[?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\.){3}(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\]?)|(?:[a-zA-Z0-9-]+\.)+(?:[a-zA-Z]){2,}\.?)$", email) is None:
            return server.response(self, values={"status" : "BADEMAIL"})

        try:
            new_user = models.User(key_name=name, name=name, password=password,
                                   email=email, salt=salt)
            new_user.put()
            server.response(self)
        except db.BadValueError, e:
            server.response(self, values={"status" : "ERROR -" + str(e)})

class List(webapp.RequestHandler):
    """Mapping: /usr/list"""
    def get(self):
        """Retrieves a list of all users"""
        users = models.User.all()
        server.response(self, {"status" : "OK", "users" : users}, "userlist")

class Groups(webapp.RequestHandler):
    """Mapping: /usr/groups/(user)"""
    def get(self, user):
        """
        Get a list of groups that a user is a member of
         :Parameters:
          - user: The name of the user. This is the tail of the url
        """
        user = models.User.get_by_key_name(user)
        if user is None:
            return server.response(self, values={"status" : "NOUSER"})
        groups = models.GroupMember.all().filter("user =", user)
        server.response(self, {"status" : "OK", "groups" : groups,
                               "user" : user, }, template="usr-groups")
        
class ResetPasswordPart1(webapp.RequestHandler):
    """Mapping: /usr/changepass"""
    def post(self):
        """
        Recieve a new password from user and send out an activation link to their email
         :Parameters:
          - email: The email address of the user wanting password change
          - password: The new password  
        """
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
    """Mapping: /usr/<name>/changepass/<activation_code>"""
    def get(self, name, activation_code):
        """Checks the activation code is correct and reset the users password to
        the temporary one recieved in `pms.server.users.ResetPasswordPart1`
         :Parameters:
          - name: The user wanting their password changed
          - activation_code: An activation code that was emailed to the user
        """
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
    """Mapping: /usr/changeavatar"""
    def post(self):
        """
        Update the users avatar
         :Parameters:
          - `session_data`: See `pms.server.server.is_valid_key`
          - avatar: An image containing the new avatar
        """
        user, user_data = server.is_valid_key(self)
        if not user:
            return server.response(self, {"status" : "BADAUTH"})
        users_avatar = models.UserAvatar.get_by_key_name(user.name)
        if users_avatar is None:
            users_avatar = models.UserAvatar(key_name=user.name)
        users_avatar.avatar = str(self.request.get("avatar"))
        users_avatar.user = user
        users_avatar.upload_time = time.time()
        users_avatar.put()
        memcache.set("useravatar-" + user.name, users_avatar)
        return server.response(self)
        
class RetrieveAvatar(webapp.RequestHandler):
    """Mapping: /usr/<username>/avatar"""
    def get(self, username):
        """
        Serves the specified users avatar, or a default if none found
         Parameters:
          - username: The name of the user whose avatar is requested
        """
        req = models.UserAvatar.get_by_key_name(username)
        if req is None:
            self.redirect("/usr/defaultavatar")
            return
        self.response.headers['Content-Type'] = "image/png"
        self.response.out.write(req.avatar)
        
class AvatarList(webapp.RequestHandler):
    """Mapping: /usr/avatarlist"""
    def post(self):
        """
        Outputs a list of avatars for users this user requires the avatar for,
        uploaded after a certain time. This is desirable if there are many users.
         :Paramters:
          - `session_data`: See `pms.server.server.is_valid_key`
          - time: A unix timestamp of the last downloaded avatar
          - userlist: A list of users we want to check
        """
        user, user_details = server.is_valid_key(self)
        last_time = self.request.get("time")
        if not user:
            return server.response(self, values={"status" : "BADAUTH"})
        userlist = self.request.get("userlist").split(",")
        logging.info(str(userlist))
        new_avatars = []
        logging.info("name list %s" % str(userlist))
        for name in userlist:
            avatar = memcache.get("useravatar-" + name)
            if avatar is None:
                avatar = models.UserAvatar.get_by_key_name(name)
                memcache.set("useravatar-" + name, avatar)
            if avatar is None:
                logging.info("There is no avatar for '%s' continue" % name)
                continue
            if last_time != "all":
                logging.info(avatar.upload_time - float(last_time))
            if last_time == "all":
                new_avatars.append(avatar)
                logging.info("Appended avatar")
            elif avatar.upload_time > float(last_time):
                new_avatars.append(avatar)
                logging.info("Appended avatar")
            else:
                logging.info("avatar not appened: %s" % name)
                logging.info("upload time: %s last time: %s" % (avatar.upload_time, last_time))
        return server.response(self, values={"status" : "OK", "avatars" : new_avatars},
                               template="avatars")
        
class RetrieveFacebookSessionKey(webapp.RequestHandler):
    """It's useful to store this here in case a user has PMS installed on multiple computers
    it will check here first, if its not found, the client can then open the users browser"""
    def post(self):
        user, user_details = server.is_valid_key(self)
        if not user:
            return server.response(self, values={"status" : "BADAUTH"})
        facebook_session_key = models.FacebookSession.get_by_key_name(user.name)
        if not facebook_session_key:
            return server.response(self, values={"status" : "NOFBKEY"})
        return server.response(self, values={"status": "OK", "session" : facebook_session_key},
                               template="session")

class AddFacebookSessionKey(webapp.RequestHandler):
    def post(self):
        user, user_details = server.is_valid_key(self)
        if not user:
            return server.response(self, values={"status": "BADAUTH"})
        facebook_session_key = models.FacebookSession.get_by_key_name(user.name)
        if not facebook_session_key:
            facebook_session_key = models.FacebookSession(key_name=user.name,
                                                          user=user, uid=self.request.get("uid"),
                                                          session_key=self.request.get("facebook_session_key"),
                                                          expires=int(self.request.get("expires")))
        else:
            facebook_session_key.uid = self.request.get("uid")
            facebook_session_key.session_key = self.request.get("facebook_session_key")
            facebook_session_key.expires = self.request.get("expires")
        facebook_session_key.put()
        return server.response(self)
        