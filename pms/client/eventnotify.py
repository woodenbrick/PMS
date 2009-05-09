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

import os
import gtk
import gtk.glade
import pygtk
pygtk.require("2.0")
import sys
import urllib, urllib2
import random
import string
import hashlib
import time
import cPickle

class EventNotify(object):
    
    def __init__(self, PROGRAM_DETAILS):
        self.PROGRAM_DETAILS = PROGRAM_DETAILS
        self.MAIN_GLADE = os.path.join(self.PROGRAM_DETAILS['extras'], "glade", "main.glade")
        self.IMAGES_DIR = os.path.join(self.PROGRAM_DETAILS['extras'], "images") + os.sep
        self.wTree = gtk.glade.XML(self.MAIN_GLADE)
        
        self.main_window = self.wTree.get_widget("window")
        self.right_click_menu = self.wTree.get_widget("right_click_menu")
        
        self.tray_icon = gtk.StatusIcon()
        self.tray_icon.set_from_file(self.IMAGES_DIR + "event-notify-blue.png")
        self.tray_icon.connect("activate", self.activate_menu, None)
        self.tray_icon.connect("popup-menu", self.popup_menu, None)
        
        self.main_window.show()
        self.wTree.signal_autoconnect(self)

    def gtk_main_quit(self, widget=None):
        gtk.main_quit()

    def activate_menu(self, *args):
        if self.main_window.props.visible:
            self.main_window.hide()
        else:
            self.main_window.show()
        
    def popup_menu(self, *args):
        self.right_click_menu.popup(parent_menu_shell=None, parent_menu_item=None,
                                    func=gtk.status_icon_position_menu,
                                        button=args[1], activate_time=args[2],
                                        data=self.tray_icon)


class AppEngineConnection(object):
    def __init__(self, username):
        self.url = "http://127.0.0.1:8080"
        self.HOMEDIR = os.path.join(os.environ['HOME'], ".eventnotify") + os.sep
        if not os.path.exists(self.HOMEDIR):
            os.mkdir(self.HOMEDIR)
        if username == "":
            self.add_new_user()
        else:
            self.username = username
        
    def add_new_user(self):
        post_values = {}
        post_values['name'] = raw_input("name: ")
        self.username = post_values['name']
        post_values['email'] = raw_input("email: ")
        post_values['password']= hashlib.sha1(raw_input("password: ")).hexdigest()
        post_values['timezone'] = raw_input("timezone: ")
        
        encoded_vals = urllib.urlencode(post_values)
        req = urllib2.urlopen(self.url + "/usr/add", encoded_vals)
        for line in req.readlines():
            print line
            
    def request_session_key(self):
        print "Requesting session key"
        post_values = {}
        post_values['name'] = raw_input("name: ").strip()
        password = raw_input("password: ")
        post_values['time'] = time.time()
        post_values['password'] = hashlib.sha1(password).hexdigest()
        encoded_vals = urllib.urlencode(post_values)
        req = urllib2.urlopen(self.url + "/getsessionkey", encoded_vals)
        response = req.readline().strip()
        if response == "OK":
            self.session_key = req.readline().strip()
            self.expires = int(req.readline().strip())
            self.pickle_key()
            return True
        else:
            self.session_key = False
            self.error = response
            return False
    
    def load_session_key(self):
        """Trys to load a sessionkey, if it fails it downloads a new one"""
        try:
            f = open(self.HOMEDIR + "sessionkey_" + self.username, "r")
            self.session_key, self.expires = cPickle.load(f)
            f.close()
            if self.expires <= time.time():
                print 'key is outdated, requesting new'
                self.request_session_key()
        except IOError:
            self.request_session_key()
        if self.session_key:
            return True
        return False
    
    def pickle_key(self):
        """Saves the current sessionkey"""
        f = open(self.HOMEDIR + "sessionkey_" + self.username, "w")
        data = [self.session_key, self.expires]
        cPickle.dump(data, f)
        f.close()

    def app_engine_request(self, data, mapping, auto_now=False):
        if auto_now:
            data['time'] = time.time()
        data['session_key'] = self.session_key
        data['name'] = self.username
        encoded_values = urllib.urlencode(data)
        request = urllib2.urlopen(self.url + mapping, encoded_values)
        return request.readlines()
    
def get_values(*args):
    """A simple commandline raw input parser to get values to send to the server
    special values: password hashes the input, salt creates a salt automatically"""
    vals = {}
    for arg in args:
        vals[arg] = raw_input("Enter value for %s: " % arg)
        if arg == "password":
            if vals["password"] != "":
                vals[arg] = hashlib.sha1(vals[arg]).hexdigest()
                vals["passreq"] = 1
            else:
                vals["passreq"] = 0
    return vals


    
    
class OldMessages(object):
    """Keeps track of previous messages and their timestamps
    the pickle is in the form of: [ [name, user, message, group, timestamp], [etc] ]
    """
    def __init__(self, username):
        self.HOME_DIR = os.path.join(os.environ['HOME'], ".eventnotify") + os.sep
        self.msg_file = "messages_" + username
        try:
            f = open(self.msg_file, "r")
            self.msgs = cPickle.load(f)
            f.close()
            self.last_time = int(self.msg[-1][4])
            
        except IOError:
            self.msgs = None
            self.last_time = ""
        

    def save(self):
        f = open(self.msg_file, "w")
        cPickle.dump(self.msgs, f)
        f.close()

def run():
    user = raw_input("Login as: (blank for new user) ")
    conn = AppEngineConnection(username=user)
    if not conn.load_session_key():
        sys.exit(conn.error)
    #all_groups = conn.app_engine_request({}, "/group/list")
    #print all_groups
    #msgs = OldMessages(conn.username)
    #groups = conn.app_engine_request({}, "/usr/groups")
    #print "groups:", groups
    #while True:
    #    print "Checking for new messages:"
    #    values = { "time" : msgs.last_time, "groups" : groups}
    #    new_messages =  conn.app_engine_request(values, "/msg/check")
    #    for line in new_messages:
    #        print line
            #msgs.last_time = time.time()
    #    time.sleep(4)
    ##print "join group"
    #values = get_values("group", "password")
    #print conn.app_engine_request(values, "/group/join")
    print "create group"
    values = get_values("group", "password", "salt")
    print conn.app_engine_request(values, "/group/add", auto_now=True)
    ##print "checking messages"
    #print "getting groups"
    #print conn.app_engine_request({}, "/group/list")
    #print "getting users"
    #values = get_values("group")
    #print conn.app_engine_request(values, "/group/list")
    #values = get_values("newowner", "group")
    #print conn.app_engine_request(values, "/changegroupowner")
    #print "removing group"
    #values = get_values("group")
    #print conn.app_engine_request(values, "/leavegroup")
    #print "deleteing group"
    #print conn.app_engine_request(values, "/deletegroup")
    #values = get_values("group")
    #print conn.app_engine_request(values, "/msg/check")
    #print "adding message"
    #values = get_values("message", "group")
    #print conn.app_engine_request(values, "/msg/add", auto_now=True)