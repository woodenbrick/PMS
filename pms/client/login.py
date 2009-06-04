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
        self.gae_conn = libpms.AppEngineConnection(self.PROGRAM_DETAILS)
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
            self.gae_conn.default_values['name'] = self.username
            has_key = self.gae_conn.check_for_session_key(self.username)
            if has_key and user_details[3] != 0:
                #we should check if the server is available here
                self.show_main()
            else:
                self.wTree.get_widget("username_entry").set_text(self.username)
                self.wTree.get_widget("password_entry").set_text(self.password)
                self.wTree.get_widget("login_window").show()
    

    def on_login_window_destroy(self, widget=None, quit=True):
        if quit:
            log.info("Quit")
            gtk.main_quit()
        else:
            self.wTree.get_widget("login_window").hide()

    def show_main(self, dump=False):
        self.gae_conn.set_password(self.password)
        self.on_login_window_destroy(quit=False)
        main.PMS(self)
        
        
       
    def on_entry_key_press_event(self, widget, key):
        #focus the passwordbox if press Enter from the username box
        if key.keyval == 65293 or key.keyval == 65289:
            #if it was enter we focus the password, tab will auto focus it
            if key.keyval == 65293:
                self.wTree.get_widget("password_entry").grab_focus()
            #get password from db if exists
            user = self.db.return_user_details(self.wTree.get_widget("username_entry").get_text())
            if user is not None:
                self.wTree.get_widget("password_entry").set_text(user[1])
            
            
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
    


    def request_session_key(self):
        #only request a new key if the old one is outdated
        self.wTree.get_widget("login_error").set_text("Requesting session key...")
        data = {"name" : self.username, "password" : self.password}
        log.info("Requesting session key")
        response = self.gae_conn.app_engine_request(data, "/getsessionkey", auto_now=True)
        if response == "OK":
            self.wTree.get_widget("login_error").set_text("Requesting session key...OK")
            self.gae_conn.default_values['session_key'] = self.gae_conn.get_tag("key")
            self.gae_conn.expires = int(self.gae_conn.get_tag("expires"))
            self.db.update_login_time(self.username)
            if self.wTree.get_widget("remember_password").get_active():
                self.db.add_user(self.username, self.password)
                self.db.auto_login_user(self.username, self.wTree.get_widget("auto_login").get_active())
            self.gae_conn.dump_session_key()
            self.show_main()
        else:
            self.wTree.get_widget("login_error").set_text(self.gae_conn.error)
            self.wTree.get_widget("login").set_sensitive(True)
            


        
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
        has_key = self.gae_conn.check_for_session_key(self.username)
        self.gae_conn.default_values['name'] = self.username
        if has_key:
            self.show_main()
        else:
            self.request_session_key()
        
    def on_register_clicked(self, widget):
        self.wTree.get_widget("login_window").hide()
        self.wTree.get_widget("reg_username").set_text("")
        self.wTree.get_widget("reg_password").set_text("")
        self.wTree.get_widget("register_error").set_text("")
        self.wTree.get_widget("email").set_text("")
        self.wTree.get_widget("register_window").show()
        
    def on_create_account_clicked(self, widget):
        username = self.wTree.get_widget("reg_username").get_text()
        if not self.sanity_check("username", username):
            return 
        password = self.wTree.get_widget("reg_password").get_text()
        if not self.sanity_check("password", password,
                                 self.wTree.get_widget("reg_password_check").get_text()):
            return
        email = self.wTree.get_widget("email").get_text()
        if not self.sanity_check("email", email):
            return
        self.wTree.get_widget("register_error").set_text("Creating new account...")
        data = {
            "name" : username,
            "password" : hashlib.sha1(password).hexdigest(),
            "email" : email
        }
        response = self.gae_conn.app_engine_request(data, "/usr/add")
        if response == "OK":
            self.wTree.get_widget("login_window").show()
            self.wTree.get_widget("register_window").hide()
            self.wTree.get_widget("login_error").set_text("Registration successful")
            self.wTree.get_widget("username_entry").set_text(data['name'])
            self.wTree.get_widget("password_entry").set_text(data['password'])
        else:
            self.wTree.get_widget("register_error").set_text(self.gae_conn.error)
    
    def sanity_check(self, type, value, pass_check=None):
        """types are email, username, password.  use pass_check to compare passwords with value"""
        if type == "username":
            reg = "^\w{5,18}$"
            error = "User name must be alpha-numeric and between 5 and 18 characters"
        elif type == "email":
            reg = "^(?:[a-zA-Z0-9_'^&amp;/+-])+(?:\.(?:[a-zA-Z0-9_'^&amp;/+-])+)*@(?:(?:\[?(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?))\.){3}(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\]?)|(?:[a-zA-Z0-9-]+\.)+(?:[a-zA-Z]){2,}\.?)$"
            error = "Invalid email address"
        else:
            reg = pass_check
            error = "Passwords don't match"
        if re.search(reg, value):
            self.wTree.get_widget("register_error").set_text("")
            return True
        self.wTree.get_widget("register_error").set_text(error)
        return False

    def reg_focus_out(self, widget, *args):
        if widget.name == "reg_username":
            self.sanity_check("username", widget.get_text())
        if widget.name == "reg_password_check":
            self.sanity_check("password", self.wTree.get_widget("reg_password").get_text(),
                              self.wTree.get_widget("reg_password_check").get_text())
        if widget.name == "email":
            self.sanity_check("email", widget.get_text())
    
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
    