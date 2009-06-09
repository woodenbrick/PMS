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
import sys
import os
import cPickle
import gobject
import gtk
import gtk.glade
import pygtk
pygtk.require20()
import webbrowser

from PIL import Image
import libpms
import db
import groups
import time
import login
import preferences
import threading
import logger
import misc
import notification
import facebookstatus


log = logger.new_logger("MAIN")

class PMS(object):
    
    def __init__(self, login_obj):
        self.PROGRAM_DETAILS = login_obj.PROGRAM_DETAILS
        self.wTree = gtk.glade.XML(self.PROGRAM_DETAILS['glade'] + "main.glade")
        self.wTree.signal_autoconnect(self)
        #show a loading window so user knows whats happening
        self.login = login_obj
        self.gae_conn = login_obj.gae_conn
        self.preferences = preferences.Preferences(self.PROGRAM_DETAILS, self.login.username)
        self.wTree.get_widget("username_label").set_text("Logged in as " + self.login.username)
        self.main_window = self.wTree.get_widget("window")
        self.right_click_menu = self.wTree.get_widget("right_click_menu")
        
        if sys.platform == "win32":
            self.notifier = notification.WindowsNotifier(self)
        else:
            self.notifier = notification.LinuxNotifier(self)

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
                popup.destroy()
                self.show_groups(None)
            else:
                popup.destroy()
        else:
            self.facebook_status = facebookstatus.FaceBookStatus(self)
            self.facebook_timer = gobject.timeout_add(25000, self.check_facebook_status)
            self.main_window.show()
        self.avatars = {}
        self.last_time = self.db.last_date()
        self.fill_messages()
        #set a timer to check messages
        self.check_in_progress = False
        self.facebook_check_in_progress = False
        self.check_messages()
        self.check_timer = gobject.timeout_add(self.preferences.preferences['msg_check'] * 1000,
                                               self.check_messages)
        self.avatar_timer = gobject.timeout_add(60000, self.retrieve_avatar_from_server)
        self.nicetime_timer = gobject.timeout_add(15000, self.update_nicetimes)
        self.check_facebook_status()
        
        
    
    def update_nicetimes(self):
        for row in self.messages_liststore:
            old_info = row[1].split("\n") 
            old_info[1] = misc.nicetime(row[3])
            row[1] = "\n".join(old_info)
            return True
    
    def update_status_bar(self, message, time=False):
        if time:
            self.wTree.get_widget("last_time").set_text(message)
        else:
            self.wTree.get_widget("main_error").set_text(message)
    
    def check_key(self, widget, key):
        #XXX connect this with the combobox the "key" needs to be taken into account
        if self.group_box.get_active_text() == "Facebook":
            if self.wTree.get_widget("new_message").get_buffer().get_char_count() >= 255:
                self.wTree.get_widget("main_error").set_text("Facebook messages have a maximum length of 255 characters.")
                self.wTree.get_widget("send_message").set_sensitive(False)
                return
            else:
                self.wTree.get_widget("send_message").set_sensitive(True)
        if key.keyval == 65293:
            self.on_send_message_clicked(widget)

    def on_send_message_clicked(self, widget):
        """Sends a new message to the server"""
        buffer = self.wTree.get_widget("new_message").get_buffer()
        start, end = buffer.get_bounds()
        message = buffer.get_text(start, end).strip()
        self.wTree.get_widget("send_message").set_sensitive(False)
        
        if self.group_box.get_active_text() == "Facebook":
            self.update_status_bar("Updating status...")
            self.facebook_status.change_status(message)
        else:
            self.update_status_bar("Sending message...")
            data = {'message' : message,
            'group' : self.group_box.get_active_text()}
            response = self.gae_conn.app_engine_request(data, "/msg/add")
            if response == "OK":
                buffer.set_text("")
                buffer.place_cursor(buffer.get_iter_at_offset(0))
                self.update_status_bar("Message sent")
            else:
                self.update_status_bar(self.gae_conn.error)
        self.wTree.get_widget("send_message").set_sensitive(True)
        
    def check_facebook_status(self):
        if self.facebook_check_in_progress:
            log.info("Facebook check in progress, cancelling")
            return True
        self.facebook_check_in_progress = True
        make_adj = True if self.wTree.get_widget("scrolledwindow").get_vadjustment().value == 0 else False
        messages = self.facebook_status.get_friends_status()
        for message in messages:
            #self.db.add_new(message)
            #add to liststore

            nicetime = misc.nicetime(message['status']['time'])
            msg = "from %s to %s\n%s\n%s" % (message['name'], "Facebook",
                                         message['status']['message'],
                                         nicetime)
            self.messages_liststore.prepend([self.get_avatar(message["name"],
                                                             facebook=message['pic_square']),
                                         msg, message['name'], message['status']['time']])
        if len(messages) > 0:
            self.login.db.cursor.execute("""update facebook set last_time=?
                                      where uid=?""", (messages[0]['status']['time'],
                                                       self.facebook_status.fb.uid))
            self.login.db.db.commit()
            self.facebook_status.last_time = messages[-1]['status']['time']
            msg = {'user' : messages[-1]['name'], 'data': messages[-1]['status']['message']}
            self.notifier.new_message(msg, len(messages),
                        nicetime, self.get_avatar(messages[-1]['name'],
                                                  messages[-1]['pic_square']))
        vadj = self.wTree.get_widget("scrolledwindow").get_vadjustment()
        if make_adj:
            vadj.value = -1
        while gtk.events_pending():
            gtk.main_iteration(False)
        self.facebook_check_in_progress = False
        return True


    def check_messages(self):
        #prevent check from multiple instances running
        if self.check_in_progress:
            log.info("Check in progress, cancelling")
            return True
        self.check_in_progress = True
        data = {"time" : self.last_time}
        response = self.gae_conn.app_engine_request(data, "/msg/check")
        if response == "OK":
            self.update_status_bar("Last update: " + time.strftime("%I:%M:%S %p",
                                                    time.localtime(time.time())), time=True)
        else:
            self.check_in_progress = False
            self.update_status_bar(self.gae_conn.error)
            return True
        make_adj = True if self.wTree.get_widget("scrolledwindow").get_vadjustment().value == 0 else False
        msg_count = 0
        message = {}
        for i in self.gae_conn.iter:
            if i.tag == "date":
                message[i.tag] = float(i.text)
                self.db.add_new(message)
                #add to liststore
                nicetime = misc.nicetime(message['date'])
                msg = "from %s to %s\n%s\n%s" % (message['user'], message['group'],
                                                 message['date'], message['data'])
                self.messages_liststore.prepend([self.get_avatar(message["user"]),
                                                 msg, message['user'], message['date']])
                if message['user'] != self.login.username:
                    pass
                msg_count += 1
                continue
            message[i.tag] = i.text
        self.last_time = self.db.last_date()
        if msg_count != 0:
            self.notifier.new_message(message, msg_count,
                        nicetime, self.get_avatar(message['user']))
        vadj = self.wTree.get_widget("scrolledwindow").get_vadjustment()
        if make_adj:
            vadj.value = -1
        while gtk.events_pending():
            gtk.main_iteration(False)
        self.check_in_progress = False    
        return True

    def close_pms(self, widget=None):
        #remove icon
        self.notifier.hide()
        self.main_window.hide()
        gobject.source_remove(self.check_timer)
        gobject.source_remove(self.avatar_timer)
        gobject.source_remove(self.nicetime_timer)
        try:
            gobject.source_remove(self.facebook_timer)
        except AttributeError:
            pass
        #XXX kill/wait for requests to finish
        gtk.main_quit()
    
    def destroy_window(self, widget, *args):
        widget.hide()
        return True

    def on_logout_clicked(self, widget):
        gobject.source_remove(self.check_timer)
        gobject.source_remove(self.avatar_timer)
        gobject.source_remove(self.nicetime_timer)
        try:
            gobject.source_remove(self.facebook_timer)
        except AttributeError:
            pass
        self.notifier.hide()
        self.wTree.get_widget("window").destroy()
        login.Login(self.PROGRAM_DETAILS, new_user=True)
    
    def activate_menu(self, *args, **kwargs):
        #if self.main_window.props.visible:
        if self.main_window.is_active():
            self.main_window.hide()
        else:
            self.main_window.present()
        return True
        
    def on_window_focus_in_event(self, *args):
        """Sets the status icon back to normal if necessary"""
        self.notifier.set_icon("logo1")
            
    def popup_menu(self, *args):
        self.right_click_menu.popup(parent_menu_shell=None, parent_menu_item=None,
                                    func=gtk.status_icon_position_menu,
                                        button=args[1], activate_time=args[2],
                                        data=self.notifier.tray_icon)
    
    def get_avatar(self, username, facebook=False):
        """Takes a username and returns a pixbuf of their avatar
        or the default if none found"""
        if facebook:
            try:
                av = self.avatars[facebook].pixbuf
            except KeyError:
                avatar_path = os.path.join(self.PROGRAM_DETAILS['home'], "thumbnails", "facebook") + os.sep
                self.avatars[facebook] = preferences.Avatar(facebook, avatar_path, facebook)
                return self.avatars[facebook].pixbuf
        try:
            av = self.avatars[username].pixbuf
            return av
        except KeyError:
            avatar_path = os.path.join(self.PROGRAM_DETAILS['home'], "thumbnails") + os.sep
            self.avatars[username] = preferences.Avatar(username, avatar_path)
            return self.avatars[username].pixbuf

    
    def retrieve_avatar_from_server(self):
        log.info("Checking for new avatars")
        #retrieve list
        try:
            f = open(self.PROGRAM_DETAILS['home'] + "av_dl_" + self.login.username, "r")
            last_download = cPickle.load(f)
            f.close()
        except IOError:
            log.debug("no avatar list for this user, downloading all")
            last_download = "all"

        query = self.db.cursor.execute("""SELECT DISTINCT username
                                                from messages""").fetchall()
        users = []
        for i in range(0, len(query)):
            users.append(query[i][0])
        users = ",".join(users)          
        if len(users) == 0:
            #user doesnt have any visible messages so,
            return True
        response = self.gae_conn.app_engine_request(data={"time" : last_download,
                                                        "userlist" : users},
                                                    mapping="/usr/avatarlist")
        if response != "OK":
            #fail silently, we have better things to do
            return True
        
        #we have a list of users who uploaded their avatar after our specified time
        newest = None
        download_users = []
        for i in self.gae_conn.iter:
            if i.tag == "user" and i.text.strip() != "":
                download_users.append(i.text)
            if i.tag == "uploaded" and i.text > newest:
                newest = i.text
        log.debug(str(download_users))
        #download these avatars are store in home dir
        for user in download_users:
            try:
                av = self.avatars[user]
            except KeyError:
                av = preferences.Avatar(user, os.path.join(self.PROGRAM_DETAILS['home'],
                                                              "thumbnails") + os.sep)
            great_success = self.gae_conn.app_engine_request(data=None, mapping="/usr/%s/avatar" % user,
                                                            get_avatar=av.path)
            if great_success:
                av.update()
                self.update_liststore_pixbufs(av)
                #if all this completes correctly we update the time given
                f = open(self.PROGRAM_DETAILS['home'] + "av_dl_" + self.login.username, "w")
                cPickle.dump(newest, f)
                f.close()
        return True
    
    def update_liststore_pixbufs(self, av_obj):
        for row in self.messages_liststore:
            if row[2] == av_obj.username:
                row[0] = av_obj.pixbuf

    def fill_messages(self):
        treeview = self.wTree.get_widget("message_view")
        self.messages_liststore = gtk.ListStore(gtk.gdk.Pixbuf, str, str, float)
        treeview.set_model(self.messages_liststore)
        messages = self.db.message_list()
        for message in messages:
            self.messages_liststore.append([self.get_avatar(message[0]), "from " + message[0] + " to " +
                                                 message[1] + "\n" +
                                                 misc.nicetime(message[3]) + "\n"
                                                 + message[2] + "\n", message[0],
                                                 message[3]])
        col = gtk.TreeViewColumn("Pic")
        cell = gtk.CellRendererPixbuf()
        col.pack_start(cell, False)
        col.set_attributes(cell, pixbuf=0)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        col.set_min_width(64)
        col.set_max_width(64)
        col.set_resizable(False)
        col.set_spacing(10)
        treeview.append_column(col)
        
        col = gtk.TreeViewColumn("Text")
        cell = gtk.CellRendererText()
        col.pack_start(cell, False)
        col.set_attributes(cell, text=1)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        col.set_min_width(100)
        col.set_max_width(250)
        col.set_resizable(True)
        col.set_spacing(10)
        treeview.append_column(col)
        
        col = gtk.TreeViewColumn("User")
        cell = gtk.CellRendererText()
        col.pack_start(cell, False)
        col.set_attributes(cell, text=1)
        col.set_sizing(gtk.TREE_VIEW_COLUMN_GROW_ONLY)
        col.set_min_width(100)
        col.set_max_width(250)
        col.set_resizable(True)
        col.set_visible(False)
        col.set_spacing(10)
        treeview.append_column(col)
        


        
    def set_groups(self, refresh=False):
        """set groups for the user"""
        if refresh is False:
            try:
                f = open(self.PROGRAM_DETAILS['home'] + "%s_user_groups" % self.login.username, "r")
                self.user_groups = cPickle.load(f)
                return self.user_groups
            except IOError:
                pass
        response = self.gae_conn._app_engine_request(None, "/usr/groups/%s" % self.login.username)
        self.user_groups = self.gae_conn.get_tags("name")
        f = open(self.PROGRAM_DETAILS['home'] + "%s_user_groups" % self.login.username, "w")
        cPickle.dump(self.user_groups, f)
        return self.user_groups
    
    def add_group(self, group_name, add=True):
        """Add/remove a single new group to the users groups"""
        if add:
            self.user_groups.insert(0, group_name)
            if group_name == "Facebook":
                self.facebook_status = facebookstatus.FaceBookStatus(self)
        else:
            self.user_groups.remove(group_name)
            if group_name == "Facebook":
                self.facebook_status = None
                gobject.source_remove(self.facebook_timer)
        f = open(self.PROGRAM_DETAILS['home'] + "%s_user_groups" % self.login.username, "w")
        cPickle.dump(self.user_groups, f)
        self.fill_groups(regenerate=True)
        return self.user_groups
        
            
    
    def fill_groups(self, regenerate=False):
        if not regenerate:
            self.group_box = gtk.combo_box_new_text()
            self.group_box.connect("changed", self.group_box_changed)
            self.set_groups()
        if len(self.user_groups) == 0:
            return False
        liststore = gtk.ListStore(str)
        self.group_box.set_model(liststore)
        self.wTree.get_widget("combo_container").pack_start(self.group_box)
        if "Facebook" in self.user_groups:
            self.facebook_status = facebookstatus.FaceBookStatus(self)
            self.facebook_timer = gobject.timeout_add(100000, self.check_facebook_status)
        else:
            self.facebook_status = None
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
        dialog.set_authors(self.PROGRAM_DETAILS['authors'])
        dialog.set_license(self.PROGRAM_DETAILS['licence'])
        dialog.set_wrap_license(False)
        dialog.set_website(self.PROGRAM_DETAILS['website'])
        dialog.set_website_label("Github repository")
        dialog.set_logo(gtk.gdk.pixbuf_new_from_file(self.PROGRAM_DETAILS['logo1']))
        gtk.about_dialog_set_url_hook(self.open_website, self.PROGRAM_DETAILS['website'])
        dialog.run()
        dialog.destroy()
    
    def report_bug(self, widget):
        webbrowser.open_new_tab("http://bugreportsite.com")
        
    def open_website(dialog, link, user_data):
        webbrowser.open(link)
