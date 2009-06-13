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
import shutil
import cPickle
import gtk
import pygtk
import gtk.glade
import urllib
import time
import gobject
import sys
from settings import Settings
from misc import new_logger
log = new_logger("Preferences.py", Settings.LOGGING_LEVEL)

class PreferencesWindow(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.preferences = self.parent.preferences
        self.wTree = gtk.glade.XML(Settings.GLADE + "preferences.glade")
        self.wTree.signal_autoconnect(self)
        self.set_gui()
        self.new_avatar = False
        self.thumb_path = os.path.join(Settings.IMAGES, "thumbnails", "_temp.thumbnail")

        
    def set_gui(self):
        self.wTree.get_widget("msg_check").set_value(self.preferences.msg_check)
        self.wTree.get_widget("avatar").set_from_file(self.preferences.avatar)  
        self.wTree.get_widget("popup").set_active(self.preferences.popup)
    
    def change_avatar(self, widget):
        self.file_selection = gtk.FileChooserDialog(title="Select an avatar", parent=None, 
                                                    action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                                    buttons=(gtk.STOCK_CANCEL,
                                                             gtk.RESPONSE_CANCEL,
                                                             gtk.STOCK_OK, gtk.RESPONSE_OK),
                                                    backend=None)
        self.file_selection.set_current_folder(Settings.HOMEMAIN)
        preview = gtk.Image()
        self.file_selection.set_preview_widget(preview)
        self.file_selection.connect("update-preview", self.update_preview_cb, preview)        
        filter = gtk.FileFilter()
        filter.set_name("Images (jpg, gif, png, bmp)")
        filter.add_pattern("*.png")
        filter.add_pattern("*.bmp")
        filter.add_pattern("*.jpg")
        filter.add_pattern("*.jpeg")
        filter.add_pattern("*.gif")
        self.file_selection.add_filter(filter)
        filter = gtk.FileFilter()
        filter.set_name("All Files")
        filter.add_pattern("*")
        self.file_selection.add_filter(filter)
        
        response = self.file_selection.run()
        if response == gtk.RESPONSE_OK:
            #create a thumbnail
            import Image
            img = Image.open(self.file_selection.get_filename())
            img.thumbnail((64, 64))
            img.save(self.thumb_path, img.format)
            self.wTree.get_widget("avatar").set_from_file(self.thumb_path)
            self.new_avatar = True
        self.file_selection.destroy()
    
    
    def update_preview_cb(self, file_chooser, preview):
        filename = file_chooser.get_preview_filename()
        try:
            pixbuf = gtk.gdk.pixbuf_new_from_file_at_size(filename, 128, 128)
            preview.set_from_pixbuf(pixbuf)
            have_preview = True
        except:
            have_preview = False
        file_chooser.set_preview_widget_active(have_preview)
        
    def on_apply_clicked(self, widget):
        new_msg_check = int(self.wTree.get_widget("msg_check").get_value())
        if new_msg_check != self.preferences.msg_check:
            #our time check has changed delete old timeout and add new
            gobject.source_remove(self.parent.check_timer)
            self.parent.check_timer = gobject.timeout_add(new_msg_check * 1000,
                                                          self.parent.check_messages)
            self.preferences.msg_check = new_msg_check
        self.preferences.popup = self.wTree.get_widget("popup").get_active()
        self.parent.wTree.get_widget("notifications").set_active(self.preferences.popup)
        #check if avatar has changed
        if self.new_avatar:
            response = self.parent.gae_conn.send_avatar(self.thumb_path)
            if response != "OK":
                self.wTree.get_widget("preference_error").set_text(self.parent.gae_conn.error)
                return
            if sys.platform == "linux2":
                os.rename(self.thumb_path, self.preferences['avatar'])
            else:
                #XXX
                #windows magically changes the name of the file by divination
                #actually no, it will freeze the program if it tries to delete
                #old file and rename
                #no solution yet
                pass
            response = self.parent.gae_conn.send_avatar(self.preferences.avatar)
            self.parent.update_liststore_pixbufs(self.parent.avatars[Settings.USERNAME])
        self.parent.preferences.save_options()
        self.wTree.get_widget("window").destroy()

        
    def on_cancel_clicked(self, widget):
        self.wTree.get_widget("window").destroy()


class Preferences(object):
    def __init__(self):
        try:
            f = open(Settings.HOME + "preferences_" + Settings.USERNAME, "r")
            self.msg_check, self.avatar, self.popup = cPickle.load(f)
            f.close()
        except IOError:
            self.load_defaults()


    def load_defaults(self):
        self.msg_check = 10
        self.avatar = os.path.join(Settings.HOME, "thumbnails",
                                    Settings.USERNAME) + ".thumbnail"
        self.popup = True
    

    def save_options(self):
        f = open(Settings.HOME + "preferences_" + Settings.USERNAME, "w")
        cPickle.dump([self.msg_check, self.avatar, self.popup], f)
        f.close()
     

class Avatar(object):
    
    def __init__(self, username, dir, facebook=False):
        self.username = username
        if facebook:
            pic_square = facebook.split("/")[-1]
            self.path = dir + pic_square
        else:
            self.path = dir + username + ".thumbnail"
        try:
            self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)
        except:
            if facebook:
                urllib.urlretrieve(facebook, dir + pic_square)
                self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)
            else:
                shutil.copy(dir + "avatar-default.png", self.path)
                self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)
        self.stat_time = os.stat(dir).st_mtime
        
    
    def update(self):
        """Updates the pixbuf with the saved thumbnail"""
        self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)