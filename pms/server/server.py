#server.py
"""Contains mappings and widely used functions by all server modules"""
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

import hashlib
import time
import random
import string
import os

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from google.appengine.ext.webapp.template import render
from google.appengine.api import memcache

import models
import groups
import users
import messages
import errors
import logging

def is_valid_key(handler_obj):
    """
    Checks if the session key is valid
     :Parameters:
      - handler_obj: The webapp.RequestHandler that called the function which contains
       - name: The name of the user
       - session_key: The session key to check
       - ip: The users IP. The key will be rejected if the IP has changed
     Returns a tuple containing:
       - The `models.User` object of the user model, the handler_obj parameters
       - False, A `pms.server.errors` code
    """
    user_data = { "name" : handler_obj.request.get("name"),
            "session_key" : handler_obj.request.get("session_key"),
            "ip" : handler_obj.request.remote_addr}
    user = memcache.get("user-" + user_data['name'])
    if user is None:
        user = models.User.get_by_key_name(user_data['name'])
        memcache.set("user-" + user_data['name'], user)
    if user is None:
        return False, "NOUSER"       
    sess = memcache.get("session-" + user_data['name'])
    if sess is None:
        sess = models.Session.all().filter("user =", user).get()
        memcache.set("session-" + user_data['name'], sess)
    if sess is None:
        return False, "BADAUTH"
    logging.debug("Session:" + "\n" + sess.session_key  + "\n" + user_data['session_key'])
    try:
        if sess.session_key == user_data['session_key'] and sess.ip == user_data['ip'] and sess.expires > time.time():
            return user, user_data
    except AttributeError:
        #If there was no sessionkey   
        pass
    return False, "BADAUTH"

def response(handler, values={"status" : "OK" }, template="default", content="xml"):
    """
    Output a response to the client
     :Parameters:
      - handler: The webapp.RequestHandler that called the function
      - values: A dictionary of values to be passed to the renderer. Must contain status and either 'OK' or a valid `pms.server.errors.errors`
      - template: The html/xml template to be rendered, from /templates
      - content: The Content-Type of the template
    """
    type = "image" if content == "png" else "text" 
    if values["status"] != "OK":
        values["error"] = errors.errors[values["status"]]
    template_path = os.path.join(os.path.dirname(__file__), "templates", template) + "." + content
    handler.response.headers['Content-Type'] = "%s/%s" % (type, content)
    handler.response.out.write(render(template_path, values))


def generate_salt():
    """
    Generates a 15 character random string to be used as a password salt, session key etc.
    """
    salt = []
    st = string.ascii_letters + string.digits
    while len(salt) < 15:
        num = random.randint(0, len(st) - 1)
        salt.append(st[num])
    return "".join(salt)

class GetSessionKey(webapp.RequestHandler):
    """
    Mapping: /getsessionkey
    """
    def post(self):
        """
        Return a new session key for the user. This is valid for 24 hours.
         :webapp.RequestHandler parameters:
          - name: Name of the user.
          - password: A sha1 hash of the users password
        """
        name = self.request.get("name")
        hash = self.request.get("password")
        ip = self.request.remote_addr

        user = memcache.get("user-" + name)
        if user is None:
            user = models.User.get_by_key_name(name)
        if user is None:
            return response(self, {"status" : "NOUSER"})
        hash_check = hashlib.sha1(hash + user.salt).hexdigest()
        if not user.password == hash_check:
            return response(self, {"status" : "BADPASS"})

        #generate a sessionkey
        session_key = []
        st = string.ascii_letters + string.digits
        while len(session_key) < 20:
            session_key.append(random.choice(st))
        expires = int(time.time() + 1000)
        session_key = "".join(session_key)
        try:
            sess = models.Session.get_by_key_name(name)
            sess.user = user
            sess.session_key = session_key
            sess.expires = expires
            sess.ip = self.request.remote_addr
        except AttributeError:
            sess = models.Session(key_name=name, user=user, session_key=session_key,
                               expires=expires, ip=self.request.remote_addr)
        sess.put()
        memcache.set("session-" + name, sess)
        temp_values = {"status" : "OK",
                        "session_key" : session_key,
                        "expires" : expires}
        response(self, temp_values, template="session")
        
        
class Error(webapp.RequestHandler):
    def get(self, mapping):
        """
        Called when an invalid mapping is recieved
         :Parameters:
          - mapping: The url mapping used
        """
        self.response.headers['Content-Type'] = 'text/plain'
        self.response.out.write("404 Not Found: %s" % mapping)    


application = webapp.WSGIApplication([
    ('/getsessionkey', GetSessionKey),
    
    ('/msg/add', messages.New),
    ('/msg/check', messages.Check),

    ('/usr/add', users.Add),
    ('/usr/list', users.List),
    (r'/usr/groups/(.+)', users.Groups),
    (r'/usr/(.+)/avatar', users.RetrieveAvatar),
    ('/usr/changeavatar', users.ChangeAvatar),
    ('/usr/avatarlist', users.AvatarList),
    ('/usr/changepass', users.ResetPasswordPart1),
    (r'/usr/(.+)/changepass/(.+)', users.ResetPasswordPart2),
    
    ('/group/add', groups.Add),
    ('/group/join', groups.Join),
    ('/group/list', groups.List),
    (r'/group/list/(.+)', groups.Members),
    ('/group/leave', groups.Leave),
    ('/group/changeowner', groups.ChangeOwner),
    ('/group/delete', groups.Delete),

    (r'/(.*)', Error),
    ], debug=True)


#: Run the server
run_wsgi_app(application)


