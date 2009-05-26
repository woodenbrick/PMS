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
import re
import libpms
import db
import main
import cPickle
import logger

log = logger.new_logger("LOGIN")


class Login(object):
    
    def __init__(self, PROGRAM_DETAILS, new_user=False):
        self.PROGRAM_DETAILS = PROGRAM_DETAILS
        self.wTree = gtk.glade.XML(self.PROGRAM_DETAILS['glade'] + "login.glade")
        self.wTree.signal_autoconnect(self)
        self.gae_conn = libpms.AppEngineConnection(self.PROGRAM_DETAILS['server'])
        self.db = db.UserDB(self.PROGRAM_DETAILS['home'] + "usersDB")
        user_details = self.db.return_user_details()
        self.login_auto_completer()
        if user_details is None or new_user is True:
            log.info("No previous user found")
            self.wTree.get_widget("login_window").show()
        else:
            log.info("Previous user found: %s" % user_details[0])
            #we will use pickles here to store the session key
            #rather than in the database, as not all users will choose to save
            #their details, though we should still keep their sessionkey
            self.username = user_details[0]
            self.password = user_details[1]
            self.session_key, self.expires = self.check_for_session_key()
            if self.session_key and user_details[3] != 0:
                self.show_main()
            else:
                self.wTree.get_widget("username_entry").set_text(self.username)
                self.wTree.get_widget("password_entry").set_text(self.password)
                self.wTree.get_widget("login_window").show()


    def on_login_window_destroy(self, widget=None):
        log.info("Quit")
        gtk.main_quit()

    def show_main(self):
        self.gae_conn.default_values = { "name" : self.username,
                                         "session_key" : self.session_key}
        self.gae_conn.set_password(self.password)
        main.PMS(self)
        self.wTree.get_widget("login_window").hide()
        
       
    def on_entry_key_press_event(self, widget, key):
        #this logs in the user if they press Enter from the password box
        #or focus the passwordbox if press Enter from the username box
        if key.keyval == 65293:
            if widget.name == "password_entry":
                self.on_login_clicked(widget)
            else:
                #get password from db if exists
                user = self.db.return_user_details(self.wTree.get_widget("username_entry").get_text())
                if user is not None:
                    self.wTree.get_widget("password_entry").set_text(user[1])
                self.wTree.get_widget("password_entry").grab_focus()
                
                
    def login_auto_completer(self):
        self.completion = gtk.EntryCompletion()
        self.completion.set_inline_completion(True)
        self.completion.set_popup_completion(False)
        self.wTree.get_widget("username_entry").set_completion(self.completion)
        liststore = gtk.ListStore(str)
        self.completion.set_model(liststore)
        pixbufcell = gtk.CellRendererPixbuf()
        self.completion.pack_start(pixbufcell)
        self.completion.add_attribute(pixbufcell, 'pixbuf', 3)
        self.completion.set_text_column(0)
        users = self.db.cursor.execute("""SELECT username FROM users""").fetchall()
        for user in users:
            liststore.append([user[0]])
    
    
    
    def check_for_session_key(self):
        """check if user has a sessionkey and return sessionkey, expires
        or False, False if the key doesnt exist or is outdated"""
        try:
            f = open(self.PROGRAM_DETAILS['home'] + "sessionkey_" + self.username, "r")
        except IOError:
            log.info("No session key available")
            return False, False
        key, exp = cPickle.load(f)
        f.close()
        if exp <= time.time():
            log.info("Outdated session key")
            return False, False
        log.info("Session key available, expires in %s minutes" % ((exp - time.time()) / 60))
        return key, exp
    
    def dump_session_key(self):
        f = open(self.PROGRAM_DETAILS['home'] + "sessionkey_" + self.username, "w")
        log.info("Saving session key")
        cPickle.dump([self.session_key, self.expires], f)
        f.close()

    def request_session_key(self):
        #only request a new key if the old one is outdated
        self.wTree.get_widget("login_error").set_text("Requesting session key...")
        data = {"name" : self.username, "password" : self.password}
        log.info("Requesting session key")
        response = self.gae_conn.app_engine_request(data, "/getsessionkey", auto_now=True)
        if response == "OK":
            self.session_key = self.gae_conn.get_tag("key")
            self.expires = int(self.gae_conn.get_tag("expires"))
            self.dump_session_key()
            self.db.update_login_time(self.username)
            self.show_main()
        else:
            self.wTree.get_widget("login_error").set_text(self.gae_conn.error)
            self.wTree.get_widget("login").set_sensitive(True)
            
        if self.wTree.get_widget("remember_password").get_active():
            self.db.add_user(self.username, self.password)
            self.db.auto_login_user(self.username, self.wTree.get_widget("auto_login").get_active())

        
    def on_login_clicked(self, widget):
        self.wTree.get_widget("login").set_sensitive(False)
        while gtk.events_pending():
            gtk.main_iteration()
        self.username = self.wTree.get_widget("username_entry").get_text()
        self.password = self.wTree.get_widget("password_entry").get_text()
        if not re.findall(r"^([a-fA-F\d]{40})$", self.password):
            self.password = hashlib.sha1(self.password).hexdigest()
        if self.wTree.get_widget("remember_password").get_active():
            self.db.add_user(self.username, self.password)
        else:
            self.db.remove_user(self.username)
        self.session_key, self.expires = self.check_for_session_key()
        if self.session_key:
            self.show_main()
        else:
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
            
    def on_forgot_pass_clicked(self, widget):
        self.wTree.get_widget("pass_change").show()
        
    def on_forgot_pass_finished(self, widget):
        if widget.name == "apply_pass_change":
            data = {
            "password" : hashlib.sha1(self.wTree.get_widget("pwd_change").get_text()).hexdigest(),
            "email" : self.wTree.get_widget("email_pwd_change").get_text()
        }
            response = self.gae_conn.app_engine_request(data, "/usr/changepass")
            if response == "OK":
                self.wTree.get_widget("pass_change").hide()
                self.wTree.get_widget("login_window").show()
                self.wTree.get_widget("login_error").set_text("Your password wont be changed until you click the activation link in your email")
            else:
                self.wTree.get_widget("pass_change_error").set_text(response)
        
        else:
            self.wTree.get_widget("pass_change").hide()
        
        
    def on_remember_password_toggled(self, widget):
        self.wTree.get_widget("auto_login").set_sensitive(widget.get_active())
    