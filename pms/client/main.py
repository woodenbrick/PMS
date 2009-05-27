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
import cPickle
import gobject
import gtk
import gtk.glade
import pygtk
pygtk.require20()

import libpms
import db
import groups
import time
import login
import preferences
import threading


class PMS(object):
    
    def __init__(self, login_obj):
        self.PROGRAM_DETAILS = login_obj.PROGRAM_DETAILS
        self.wTree = gtk.glade.XML(self.PROGRAM_DETAILS['glade'] + "main.glade")
        self.wTree.signal_autoconnect(self)
        #show a loading window so user knows whats happening
        self.login = login_obj
        self.gae_conn = login_obj.gae_conn
        self.preferences = preferences.Preferences(self.PROGRAM_DETAILS, self.login.username)

        self.main_window = self.wTree.get_widget("window")
        self.right_click_menu = self.wTree.get_widget("right_click_menu")
        
        self.tray_icon = gtk.StatusIcon()
        self.tray_icon.set_from_file(self.PROGRAM_DETAILS['images'] + "event-notify-blue.png")
        self.tray_icon.connect("activate", self.activate_menu, None)
        self.tray_icon.connect("popup-menu", self.popup_menu, None)
        
        #show icons
        images = ["refresh", "bug", "groups"]
        for i in images:
            new_img = gtk.Image()
            new_img.set_from_file(self.PROGRAM_DETAILS['images'] + i + ".png")
            self.wTree.get_widget("menu_" + i).set_image(new_img)

        
        self.db = db.MessageDB(self.PROGRAM_DETAILS['home'] + "MessageDB_" + self.login.username)
        self.set_groups()
        
        if not self.fill_groups():
            popup = gtk.MessageDialog(None, gtk.DIALOG_MODAL,
                                  gtk.MESSAGE_INFO, gtk.BUTTONS_YES_NO,
                                  "You are not a member of any group.  See group list?")
            response = popup.run()
            if response == gtk.RESPONSE_YES:
                self.show_groups(None)
            popup.destroy()
        else:
            self.main_window.show()
        self.last_time = self.db.last_date()
        self.fill_messages()
        #set a timer to check messages
        self.check_messages()
        self.check_timer = gobject.timeout_add(5000, self.check_messages)
    
    def update_status_bar(self, message, time=False):
        if time:
            self.wTree.get_widget("last_time").set_text(message)
        else:
            self.wTree.get_widget("main_error").set_text(message)
        while gtk.events_pending():
            gtk.main_iteration()
    
    def check_key(self, widget, key):
        if key.keyval == 65293:
            self.on_send_message_clicked(widget) 
    
    def check_messages(self):
        data = {"time" : self.last_time,
                "groups" : ",".join(self.user_groups)}
        response = self.gae_conn.app_engine_request(data, "/msg/check")
        if response == "OK":
            self.update_status_bar("")
            self.update_status_bar("Last update: " + time.strftime("%I:%M:%S %p",
                                                    time.localtime(time.time())), time=True)
        else:
            return self.update_status_bar(self.gae_conn.error)
        message = {}
        msg_count = 0
        for i in self.gae_conn.iter:
            if i.tag == "date":
                message[i.tag] = int(i.text)
                self.db.add_new(message)
                #add to liststore
                self.messages_liststore.prepend([message["user"] + message["group"] + message["data"] + str(message["date"])])
                msg_count += 1
                continue
            message[i.tag] = i.text
        if msg_count != 0:
            #we have new messages, lets update the last_time
            self.last_time = self.db.last_date()
        return True

    def gtk_main_quit(self, widget=None):
        print widget.name
        gtk.main_quit()

    def on_logout_clicked(self, widget):
        gobject.source_remove(self.check_timer)
        self.wTree.get_widget("window").destroy()
        login.Login(self.PROGRAM_DETAILS, new_user=True)
    
    def activate_menu(self, *args):
        if self.main_window.props.visible:
            self.main_window.hide()
        else:
            self.main_window.show()
        return True
        
    def popup_menu(self, *args):
        self.right_click_menu.popup(parent_menu_shell=None, parent_menu_item=None,
                                    func=gtk.status_icon_position_menu,
                                        button=args[1], activate_time=args[2],
                                        data=self.tray_icon)


    def fill_messages(self):
        treeview = self.wTree.get_widget("message_view")
        self.messages_liststore = gtk.ListStore(str)
        treeview.set_model(self.messages_liststore)
        messages = self.db.message_list()
        for m in messages:
            mess = [m[0] + "\n" + m[1] + "\n" + m[2] + "\n" + "\n" + str(m[3])]
            self.messages_liststore.append(mess)
        col = gtk.TreeViewColumn("")
        cell = gtk.CellRendererText()
        col.pack_start(cell, False)
        col.set_attributes(cell, text=0)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        col.set_min_width(100)
        col.set_max_width(250)
        col.set_resizable(True)
        col.set_spacing(10)
        treeview.append_column(col)
        
    def on_send_message_clicked(self, widget):
        """Sends a new message to the server"""
        self.wTree.get_widget("send_message").set_sensitive(False)
        self.update_status_bar("Sending message...")
        buffer = self.wTree.get_widget("new_message").get_buffer()
        start, end = buffer.get_bounds()
        data = {'message' : buffer.get_text(start, end),
        'group' : self.group_box.get_active_text()}
        response = self.gae_conn.app_engine_request(data, "/msg/add")
        self.wTree.get_widget("send_message").set_sensitive(True)
        if response == "OK":
            buffer.set_text("")
            self.check_messages()
        else:
            self.update_status_bar(self.gae_conn.error)

        
    def set_groups(self, refresh=False):
        """set groups for the user"""
        if refresh is False:
            try:
                f = open(self.PROGRAM_DETAILS['home'] + "%s_user_groups" % self.login.username, "r")
                self.user_groups = cPickle.load(f)
                return self.user_groups
            except IOError:
                pass
        response = self.gae_conn.app_engine_request(None, "/usr/groups/%s" % self.login.username)
        self.user_groups = self.gae_conn.get_tags("name")
        f = open(self.PROGRAM_DETAILS['home'] + "%s_user_groups" % self.login.username, "w")
        cPickle.dump(self.user_groups, f)
        return self.user_groups
    
    def add_group(self, group_name, add=True):
        """Add/remove a single new group to the users groups"""
        if add:
            self.user_groups.insert(0, group_name)
        else:
            self.user_groups.remove(group_name)
        f = open(self.PROGRAM_DETAILS['home'] + "%s_user_groups" % self.login.username, "w")
        cPickle.dump(self.user_groups, f)
        self.fill_groups(regenerate=True)
        return self.user_groups
        
        
    
    def fill_groups(self, regenerate=False):
        if not regenerate:
            self.group_box = gtk.combo_box_new_text()
            self.set_groups()
        if len(self.user_groups) == 0:
            return False
        liststore = gtk.ListStore(str)
        self.group_box.set_model(liststore)
        self.wTree.get_widget("combo_container").pack_start(self.group_box)
        for item in self.user_groups:
            self.group_box.append_text(item)
        self.group_box.set_active(0)
        self.group_box.show()
        return True

    
    def show_groups(self, widget):
        groups.GroupWindow(self)
        
    def report_bug(self, widget):
        pass
    
    def on_preferences_clicked(self, widget):
        preferences.PreferencesWindow(self)
        
    def about(self, widget):
        dialog = gtk.AboutDialog()
        dialog.set_name(self.PROGRAM_DETAILS['name'])
        dialog.set_version(self.PROGRAM_DETAILS['version'])
        dialog.set_authors("\n".join(self.PROGRAM_DETAILS['authors']))
        dialog.set_license(self.PROGRAM_DETAILS['licence'])
        dialog.set_wrap_license(True)
        dialog.set_website(self.PROGRAM_DETAILS['website'])
        dialog.set_website_label("Github repository")
        dialog.set_logo(gtk.gdk.pixbuf_new_from_file(self.PROGRAM_DETAILS['logo']))
        dialog.run()
        dialog.destroy()
        
