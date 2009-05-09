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

from google.appengine.ext import webapp
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db

import models
import groups
import users
import admin
import messages

def is_valid_key(handler_obj):
    """Checks if the session key is valid, Returns the user model if True"""
    user_data = { "name" : handler_obj.request.get("name"),
            "session_key" : handler_obj.request.get("session_key"),
            "ip" : handler_obj.request.remote_addr}
    user = models.User.get_by_key_name(user_data['name'])
    sess = models.Session.all().filter("user =", user).get()
    try:
        if sess.session_key == user_data['session_key'] and sess.ip == user_data['ip']:
            return user, user_data
    except AttributeError:
        #If there was no sessionkey   
        pass
    return False, "BADAUTH"

def response(handler, response="OK", header=True):
    if header:
        handler.response.headers['Content-Type'] = 'text/plain'
    handler.response.out.write(response)

class GetSessionKey(webapp.RequestHandler):

    def post(self):
        """The user should send a request with their
        username, password&time hash, time, ip"""
        name = self.request.get("name")
        hash = self.request.get("password")
        send_time = self.request.get("time")
        ip = self.request.remote_addr

        if time.time() - float(send_time) > 60:
            return response(self, "BADTIME")
    
        user = models.User.all().filter("name =", name).get()
        if user is None:
            return response(self, 'NOUSER')
        hash_check = hashlib.sha1(hash + user.salt).hexdigest()
        if not user.password == hash_check:
            return response(self, 'BADPASS')

        #generate a sessionkey
        session_key = []
        st = string.ascii_letters + string.digits + string.punctuation
        while len(session_key) < 30:
            session_key.append(random.choice(st))
        expires = int(time.time() + 86400)
        session_key = user.name + "_" + str(expires) + "_" + "".join(session_key)
        try:
            sess = models.Session.all().filter("user =", user).get()
            sess.user = user
            sess.session_key = session_key
            sess.expires = expires
            sess.ip = self.request.remote_addr
            sess.put()
        except IndexError:
            s = models.Session(user=user, session_key=session_key, expires=expires,
                           ip=self.request.remote_addr)
            s.put()
        response(self, "OK\n" + session_key + "\n" + str(expires) + "\n")



application = webapp.WSGIApplication([
    ('/getsessionkey', GetSessionKey),
    
    ('/msg/add', messages.New),
    ('/msg/check', messages.Check),

    ('/usr/add', users.Add),
    ('/usr/list', users.List),
    ('/usr/groups', users.Groups),
    
    ('/group/add', groups.Add),
    ('/group/join', groups.Join),
    ('/group/list', groups.List),
    (r'/group/list/(.*)', groups.Members),
    ('/group/leave', groups.Leave),
    ('/group/changeowner', groups.ChangeOwner),
    ('/group/delete', groups.Delete),

    ('/allmessages', admin.AllMessages), #admin
    ], debug=True)

def main():
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

