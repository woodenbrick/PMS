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
import os
import time
import gtk
import gtk.glade
import pygtk
pygtk.require20()

import libpms
import db
import main


class Login(object):
    
    def __init__(self, PROGRAM_DETAILS):
        self.PROGRAM_DETAILS = PROGRAM_DETAILS
        self.wTree = gtk.glade.XML(self.PROGRAM_DETAILS['glade'] + "login.glade")
        self.wTree.signal_autoconnect(self)
        self.gae_conn = libpms.AppEngineConnection()
        self.db = db.UserDB(self.PROGRAM_DETAILS['home'] + "usersDB")
        user_details = self.db.return_user_details()
        if user_details is None:
            self.wTree.get_widget("login_window").show()
        else:
            self.username = user_details[0]
            self.password = user_details[1]
            self.session_key = user_details[2]
            self.expires = user_details[3]
            if self.expires <= time.time():
                print 'key is outdated, requesting new.'
                self.request_session_key()
            else:
                print 'success'

    def gtk_main_quit(self, widget=None):
        gtk.main_quit()

    def show_main(self):
        self.wTree.get_widget("login_window").destroy()
        main.PMS(self)


    def request_session_key(self):
        self.wTree.get_widget("login_error").set_text("Authenticating")
        data = {"name" : self.username, "password" : self.password}
        response = self.gae_conn.app_engine_request(data, "/getsessionkey", auto_now=True)
        if response == "OK":
            data = {
            "expires" : self.gae_conn.get_tag("expires"),
            "session_key" : self.gae_conn.get_tag("key"),
            "last_login" : time.time(),
            "user" : self.username}
            self.db.update_user(data)
            self.gae_conn.default_values = { "name" : self.username,
                                            "session_key" : data['session_key']}
            self.show_main()
        else:
            self.wTree.get_widget("login_error").set_text("Error:" + self.gae_conn.error)

        
    def on_login_clicked(self, widget):
        self.username = self.wTree.get_widget("username_entry").get_text()
        self.password = hashlib.sha1(self.wTree.get_widget("password_entry").get_text()).hexdigest()
        self.request_session_key()
        
    def on_register_clicked(self, widget):
        self.wTree.get_widget("login_window").hide()
        self.wTree.get_widget("reg_username").set_text("")
        self.wTree.get_widget("reg_password").set_text("")
        self.wTree.get_widget("email").set_text("")
        self.wTree.get_widget("register_window").show()
        
    def on_create_account_clicked(self, widget):
        data = {
            "name" : self.wTree.get_widget("reg_username").get_text(),
            "password" : hashlib.sha1(self.wTree.get_widget("reg_password").get_text()).hexdigest(),
            "email" : self.wTree.get_widget("email").get_text()
        }
        response = self.gae_conn.app_engine_request(data, "/usr/add")
        if response == "OK":
            self.wTree.get_widget("login_window").show()
            self.wTree.get_widget("register_window").hide()
            self.wTree.get_widget("login_error").set_text("Registration successful")
        else:
            self.wTree.get_widget("register_error").set_text(response)