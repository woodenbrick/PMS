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
import time
import cPickle
import hashlib
import gtk
import gtk.glade
import pygtk
import gobject

import logger

log = logger.new_logger("GROUP")

class GroupWindow():
    def __init__(self, parent):
        self.parent = parent
        self.wTree = gtk.glade.XML(self.parent.PROGRAM_DETAILS['glade'] + "group.glade")
        self.wTree.signal_autoconnect(self)
        self.grouplist_file = self.parent.PROGRAM_DETAILS['home'] + "grouplist_" + self.parent.login.username
        self.columns = ["name", "owner", "description", "password", "membership", "passimg", "memimage"]
        
        self.group_list = self.check_for_old_grouplist()
        if not self.group_list:
            self.group_list = self.new_grouplist()
        self.group_liststore = gtk.ListStore(str, str, str, bool, bool, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf)
        for item in self.group_list:
            img_pass = self.create_pixbuf(value=item[3], member=False)
            img_member = self.create_pixbuf(value=item[4])
            self.group_liststore.append(item + [img_pass, img_member])
        self.wTree.get_widget("groupview").set_model(self.group_liststore)
        self.create_columns()
        self.timer = gobject.timeout_add(60000, self.update_refresh_button)
        self.update_refresh_button()
        
    def on_window_destroy(self, widget):
        gobject.source_remove(self.timer)

    def update_refresh_button(self):
        diff = int((time.time() - self.mtime) / 60)
        self.wTree.get_widget("refresh_label").set_text("Refresh (last done \n%s minutes ago)" % diff)
    
    
    def check_for_old_grouplist(self):
        """check for a pickled list for groupliststore and use this instead,
        along with a warning about its date"""
        try:
            f = open(self.grouplist_file, "r")
            stat = os.stat(self.grouplist_file)
            self.mtime = float(stat.st_mtime)
        except IOError:
            return False
        return cPickle.load(f)
        
    def update_pickled_grouplist(self):
        log.debug(str(self.group_list))
        f = open(self.grouplist_file, "w")
        cPickle.dump(self.group_list, f)
        self.mtime = time.time()

   
    
    def new_grouplist(self, widget=None):
        """Returns all the groups from the server and puts them into a treeview
        we need: a list of all groups a list of the groups the user is already a member of"""
        response = self.parent.gae_conn.app_engine_request(None, "/group/list")
        if response != "OK":
            self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
            return
        all_groups_tree = self.parent.gae_conn.xtree
        response =  self.parent.gae_conn.app_engine_request(None, "/usr/groups/%s" %
                                                            self.parent.login.username)
        if response != "OK":
            self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
            return
        user_groups_tree = self.parent.gae_conn.xtree
        user_groups = []
        for i in user_groups_tree.getiterator():
            if i.tag == "name":
                user_groups.append(i.text.strip())
        iter = all_groups_tree.getiterator()
        
        self.group_list = []
        group = []

        for child in iter:
            if child.tag in self.columns:
                if child.tag == "password":
                    pass_req = True if child.attrib["required"] == "True" else False
                    group.append(pass_req)
                    #we need to check if the user is a member of this group
                    if group[0] in user_groups:
                        group.append(True)
                    else:
                        group.append(False)
                    self.group_list.append(group)
                    group = []
                else:
                    group.append(child.text)
        #cache the groupliststore for later use
        f = open(self.grouplist_file, "w")
        cPickle.dump(self.group_list, f)
        f.close()
        self.mtime = time.time()
        return self.group_list
    
    def refresh_grouplist(self, widget):
        old_list = self.group_list
        self.new_grouplist()
        for item in self.group_list:
            if item not in old_list:
                img_pass = self.create_pixbuf(item[3], False)
                img_member = self.create_pixbuf(item[4])
                self.group_liststore.append(item + [img_pass, img_member])
                
    def create_pixbuf(self, value, member=True):
        if value is False:
            return  gtk.gdk.pixbuf_new_from_file(self.parent.PROGRAM_DETAILS['images'] + "blank.png")
        if member:
            return gtk.gdk.pixbuf_new_from_file(self.parent.PROGRAM_DETAILS['images'] + "member.png")
        return gtk.gdk.pixbuf_new_from_file(self.parent.PROGRAM_DETAILS['images'] + "password.png")
        

    def create_columns(self):
        #create columns
        for i in range(0, len(self.columns)):
            col = gtk.TreeViewColumn(self.columns[i])
            if i == 5 or i == 6:
                cell = gtk.CellRendererPixbuf()
            else:
                cell = gtk.CellRendererText()
            col.pack_start(cell, False)
            if i == 5 or i == 6:
                col.set_attributes(cell, pixbuf=i)
            else:
                col.set_attributes(cell, text=i)
                
            col.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
            col.set_min_width(30)
            col.set_max_width(250)
            col.set_resizable(True)
            col.set_spacing(10)
            self.wTree.get_widget("groupview").append_column(col)
    
    
    
    def change_join_button(self, widget):
        """check if user belongs to a group and adjust the join/leave button accordingly
        returns the action and group"""
        member, group = self.is_member()
        if member:
            action = "joined"
            button = "Leave"
            image = gtk.STOCK_CANCEL
        else:
            action = "left"
            button = "Join"
            image = gtk.STOCK_OK
            
        self.wTree.get_widget("group_label").set_text(button)
        self.wTree.get_widget("group_image").set_from_stock(image, gtk.ICON_SIZE_BUTTON)
        
        return action, group

    
    
    
    def is_member(self):
        """Checks the current selection and returns (True, group) if user is a member"""
        model, iter = self.wTree.get_widget("groupview").get_selection().get_selected()
        member = model.get_value(iter, 4)
        if member is True:
            return True, model.get_value(iter, 0)
        return False, model.get_value(iter, 0)
    
    
    
    def change_membership(self):
        """Change membership status without touching the server"""
        model, iter = self.wTree.get_widget("groupview").get_selection().get_selected()
        membership = True if model.get_value(iter, 4) is False else False
        model.set_value(iter, 4, membership)
        if membership:
            model.set_value(iter, 6, self.create_pixbuf(membership))
        owner = model.get_value(iter, 1)
        desc = model.get_value(iter, 2)
        pass_req = model.get_value(iter, 3)
        action, group = self.change_join_button(None)
        self.auto_message(action, group)
        
        self.update_local_grouplist([group, owner, desc, pass_req, membership],
            join=membership)


    def on_join_leave_group_clicked(self, widget):
        member, group = self.is_member()
        values = {"group" : group}
        if member:
            #leave group
            response = self.parent.gae_conn.app_engine_request(values, "/group/leave")
            if response == "OK":
                self.change_membership()
            else:
                self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
                
        else:
            #join group
            #password required?
            model, iter = self.wTree.get_widget("groupview").get_selection().get_selected()
            pass_req = model.get_value(iter, 3)
            if pass_req == "True":
                #password popup
                self.wTree.get_widget("group_pass_label").set_text(
                    "The group %s requires a password:" % group)
                response = self.wTree.get_widget("password").run()
                if response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
                    self.wTree.get_widget("password").hide()
                    return
                else:
                    values["password"] = hashlib.sha1(self.wTree.get_widget("join_group_pass").get_text()).hexdigest()
            
            response = self.parent.gae_conn.app_engine_request(values, "/group/join")
            if response == "OK":
                self.change_membership()
                pass
            else:
                self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
            self.wTree.get_widget("password").hide()
            
    
    
    def on_create_group_clicked(self, widget):
        response = self.wTree.get_widget("new_dialog").run()
        self.wTree.get_widget("new_dialog").hide()
    
    def on_group_pass_keypress(self, widget, key):
        if key.keyval == 65293:
            return gtk.RESPONSE_OK
    
    
    def on_group_close(self, widget):
        if widget.name == "apply":
            values = {
                "group" : self.wTree.get_widget("group_name").get_text(),
                "description" : self.wTree.get_widget("description").get_text()
            }
            if self.wTree.get_widget("group_pass").get_text() != "":
                values['password'] = hashlib.sha1(self.wTree.get_widget("group_pass").get_text()).hexdigest()
                pass_req = True
            else:
                pass_req = False
            response = self.parent.gae_conn.app_engine_request(values, "/group/add")
            if response == "OK":
                self.update_local_grouplist([values['group'], self.parent.login.username,
                                             values['description'], pass_req, True], create=True)
            else:
                self.wTree.get_widget("group_error").set_text("Error: " +
                                                              self.parent.gae_conn.error)
                #show the error message on the main group window
        self.wTree.get_widget("new_dialog").hide()
        
    
    def update_local_grouplist(self, group_details, create=False, join=True):
        """Adds/removes the newly created/join/left group to the liststore combobox and pickle
        group_details is [groupname, owner, description, pass_req, membership
        iter is required if leaving a group"""
        if create:
            pass_img = self.create_pixbuf(group_details[3], False)
            member_img = self.create_pixbuf(True)
            self.group_liststore.append(group_details + [pass_img, member_img])
            self.group_list.append(group_details)
            self.update_pickled_grouplist()
            self.auto_message("created", group_details[0])
            return
        model, iter = self.wTree.get_widget("groupview").get_selection().get_selected()
        if join:
            self.parent.add_group(group_details[0], add=True)
            self.parent.group_box.set_active(0)
            model.set_value(iter, 6, self.create_pixbuf(True))
        else:
            self.parent.add_group(group_details[0], add=False)
            model.set_value(iter, 6, self.create_pixbuf(False))
        


    def auto_message(self, action, group):
        """adds a message of type [left, joined, created] groups"""
        data = {'message' : "%s has %s the group %s" % (self.parent.login.username,
                                          action, group),
                'group' : group}
        response = self.parent.gae_conn.app_engine_request(data, "/msg/add")