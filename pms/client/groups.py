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
import pango
import gobject
from settings import Settings
from misc import new_logger, nicetime
log = new_logger("group.py", Settings.LOGGING_LEVEL)

class GroupWindow():
    def __init__(self, parent):
        self.parent = parent
        self.wTree = gtk.glade.XML(Settings.GLADE + "group.glade")
        self.wTree.signal_autoconnect(self)
        self.wTree.get_widget("group_error").set_text("Loading groups")
        self.grouplist_file = Settings.HOME + "grouplist_" + Settings.USERNAME
        self.columns = ["Name", "Owner", "Description", "password", "membership", "Password?", "Member?"]
        self.wTree.get_widget("window").set_icon_from_file(Settings.LOGO1)
        self.group_list = self.check_for_old_grouplist()
        self.group_liststore = gtk.ListStore(str, str, str, bool, bool, gtk.gdk.Pixbuf, gtk.gdk.Pixbuf)
        if not self.group_list:
            self.group_list = self.new_grouplist()
        if self.group_list is not None:
            self.refresh_grouplist(None)
        self.wTree.get_widget("groupview").set_model(self.group_liststore)
        self.create_columns()
        self.wTree.get_widget("group_error").set_text("")
        self.timer = gobject.timeout_add(60000, self.update_refresh_button)
        self.update_refresh_button()
        
    def on_window_destroy(self, widget):
        gobject.source_remove(self.timer)

    def update_refresh_button(self):
        self.wTree.get_widget("refresh_label").set_text("Refresh (last done \n%s)" % nicetime(self.mtime))
    
    
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
        self.wTree.get_widget("group_error").set_text("Downloading new group list...")
        response = self.parent.gae_conn.app_engine_request(None, "/group/list")
        if response != "OK":
            self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
            return
        all_groups_tree = self.parent.gae_conn.xtree
        response =  self.parent.gae_conn.app_engine_request(None, "/usr/groups/%s" %
                                                            Settings.USERNAME)
        if response != "OK":
            self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
            return
        self.wTree.get_widget("group_error").set_text("Downloading new group list...Done")
        
        user_groups_tree = self.parent.gae_conn.xtree
        user_groups = []
        for i in user_groups_tree.getiterator():
            if i.tag == "name":
                user_groups.append(i.text)

        groups = all_groups_tree.findall("group")
        self.group_list = []
        for group in groups:
            self.group_list.append([
                group.find("name").text,
                group.find("owner").text,
                group.find("description").text,
                True if group.find("password").attrib["required"] == "True" else False,
                True if group.find("name").text in user_groups else False
            ])
        #cache the groupliststore for later use
        f = open(self.grouplist_file, "w")
        cPickle.dump(self.group_list, f)
        f.close()
        self.mtime = time.time()
        return self.group_list
    
    def refresh_grouplist(self, widget):
        self.group_liststore.clear()
        if widget is not None:
            self.new_grouplist()
        for item in self.group_list:
                img_pass = self.create_pixbuf(value=item[3], member=False)
                img_member = self.create_pixbuf(value=item[4])
                self.group_liststore.append(item + [img_pass, img_member])
        self.update_refresh_button()
                
    def create_pixbuf(self, value, member=True):
        if value is False:
            return  gtk.gdk.pixbuf_new_from_file(Settings.IMAGES + "blank.png")
        if member:
            return gtk.gdk.pixbuf_new_from_file(Settings.IMAGES + "member.png")
        return gtk.gdk.pixbuf_new_from_file(Settings.IMAGES + "password.png")
        

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
            if i == 3 or i == 4:
                col.set_visible(False)
            col.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
            if i == 2:
                #description
                cell.props.wrap_mode = pango.WRAP_WORD_CHAR
                cell.props.wrap_width = 300
            #else:
            #    col.set_min_width(30)
            #    col.set_max_width(100)
            col.set_resizable(True)
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
            self.wTree.get_widget("group_error").set_text("Leaving group %s..." % values['group'])
            response = self.parent.gae_conn.app_engine_request(values, "/group/leave")
            if response == "OK":
                self.change_membership()
                self.wTree.get_widget("group_error").set_text("Left the group %s" % values['group'])
            else:
                self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
                
        else:
            #join group
            #password required?
            model, iter = self.wTree.get_widget("groupview").get_selection().get_selected()
            pass_req = model.get_value(iter, 3)
            if pass_req is True:
                #password popup
                self.wTree.get_widget("group_pass_label").set_text(
                    "The group %s requires a password:" % group)
                response = self.wTree.get_widget("password").run()
                self.wTree.get_widget("password").hide()
                if response == gtk.RESPONSE_CANCEL or response == gtk.RESPONSE_DELETE_EVENT:
                    return
                else:
                    values["password"] = hashlib.sha1(self.wTree.get_widget("join_group_pass").get_text()).hexdigest()
            self.wTree.get_widget("group_error").set_text("Joining group %s..." % values['group'])

            response = self.parent.gae_conn.app_engine_request(values, "/group/join")
            if response == "OK":
                self.change_membership()
                self.wTree.get_widget("group_error").set_text("Joined the group %s" % values['group'])
            else:
                self.wTree.get_widget("group_error").set_text("Error: " + self.parent.gae_conn.error)
            
    
    def on_create_group_clicked(self, widget):
        self.wTree.get_widget("group_name").set_text("")
        self.wTree.get_widget("group_pass").set_text("")
        self.wTree.get_widget("description").get_buffer().set_text("")
        response = self.wTree.get_widget("new_dialog").run()
        
    
    def on_group_pass_keypress(self, widget, key):
        if key.keyval == 65293:
            return gtk.RESPONSE_OK
    
    
    def on_group_close(self, widget):
        """Creates a new group"""
        self.wTree.get_widget("new_dialog").hide()
        if widget.name == "apply":
            self.wTree.get_widget("group_error").set_text("Creating new group...")
            start, end = self.wTree.get_widget("description").get_buffer().get_bounds()
            values = {
                "group" : self.wTree.get_widget("group_name").get_text(),
                "description" : self.wTree.get_widget("description").get_buffer().get_text(start, end)
            }
            if self.wTree.get_widget("group_pass").get_text() != "":
                values['password'] = hashlib.sha1(self.wTree.get_widget("group_pass").get_text()).hexdigest()
                pass_req = True
            else:
                pass_req = False
            response = self.parent.gae_conn.app_engine_request(values, "/group/add")
            if response == "OK":
                self.update_local_grouplist([values['group'], Settings.USERNAME,
                                             values['description'], pass_req, True], create=True)
                self.wTree.get_widget("group_error").set_text("")
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
            self.parent.add_group(group_details[0], add=True)
            self.parent.group_box.set_active(0)
            return
        model, iter = self.wTree.get_widget("groupview").get_selection().get_selected()
        if join:
            self.parent.add_group(group_details[0], add=True)
            self.parent.group_box.set_active(0)
            model.set_value(iter, 6, self.create_pixbuf(True))

        else:
            self.parent.add_group(group_details[0], add=False)
            model.set_value(iter, 6, self.create_pixbuf(False))
            
        for group in self.group_list:
            if group[0] == group_details[0]:
                group[4] = group_details[4]
                break
        self.update_pickled_grouplist()



    def auto_message(self, action, group):
        """adds a message of type [left, joined, created] groups"""
        if group == "Facebook":
            return
        data = {'message' : "%s has %s the group %s" % (Settings.USERNAME,
                                          action, group),
                'group' : group}
        response = self.parent.gae_conn.app_engine_request(data, "/msg/add")