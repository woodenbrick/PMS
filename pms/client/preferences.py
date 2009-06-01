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

class PreferencesWindow(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.program_details = self.parent.PROGRAM_DETAILS
        self.preferences = self.parent.preferences.preferences
        self.wTree = gtk.glade.XML(self.program_details['glade'] + "preferences.glade")
        self.wTree.signal_autoconnect(self)
        self.set_gui()
        self.new_avatar = False

        
    def set_gui(self):
        self.wTree.get_widget("msg_check").set_value(self.preferences["msg_check"])
        self.wTree.get_widget("avatar").set_from_file(self.preferences["avatar"])  
        self.wTree.get_widget("popup").set_active(self.preferences["popup"])
    
    def change_avatar(self, widget):
        self.file_selection = gtk.FileChooserDialog(title="Select an avatar", parent=None, 
                                                    action=gtk.FILE_CHOOSER_ACTION_OPEN,
                                                    buttons=(gtk.STOCK_CANCEL,
                                                             gtk.RESPONSE_CANCEL,
                                                             gtk.STOCK_OK, gtk.RESPONSE_OK),
                                                    backend=None)
        self.file_selection.set_current_folder(os.path.split(self.program_details['home'])[0])
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
            print img.format, img.size, img.mode
            img.thumbnail((64, 64))
            thumbnail = os.path.join(self.program_details['home'], "thumbnails",
                                    "_temp.thumbnail")
            img.save(thumbnail, img.format)
            self.wTree.get_widget("avatar").set_from_file(thumbnail)
            self.new_avatar = True
        self.file_selection.destroy()
        
        
    def on_apply_clicked(self, widget):
        self.preferences['msg_check'] = self.wTree.get_widget("msg_check").get_value()
        self.preferences['popup'] = self.wTree.get_widget("popup").get_active()
        #check if avatar has changed
        if self.new_avatar:
            #os.remove(self.preferences['avatar'])
            os.rename(os.path.join(self.program_details['home'], "thumbnails",
                      "_temp.thumbnail"), self.preferences['avatar'])
            response = self.parent.gae_conn.send_avatar(self.preferences['avatar'])
            if response != "OK":
                self.wTree.get_widget("preference_error").set_text(self.parent.gae_conn.error)
                return
            else:
                self.parent.retrieve_avatar_from_server()
        self.parent.preferences.save_options()
        self.wTree.get_widget("window").destroy()


class Preferences(object):
    def __init__(self, program_details, username):
        self.username = username
        self.preference_file = "preferences_" + self.username
        self.program_details = program_details
        try:
            f = open(self.program_details['home'] + self.preference_file, "r")
            self.preferences = cPickle.load(f)
            f.close()
        except IOError:
            self.load_defaults()


    def load_defaults(self):
        self.preferences = {
            "msg_check" : 1,
            "avatar" : os.path.join(self.program_details['home'], "thumbnails",
                                    self.username) + ".thumbnail",
            "popup" : True
        }
    

    def save_options(self):
        f = open(self.program_details['home'] + self.preference_file, "w")
        cPickle.dump(self.preferences, f)
        f.close()
     

class Avatar(object):
    
    def __init__(self, username, dir, default=False):
        self.username = username
        self.path = dir + username + ".thumbnail"
        try:
            self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)
        except:
            shutil.copy(dir + "avatar-default.png", self.path)
            self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)
        self.stat_time = os.stat(dir).st_mtime
        
    
    def update(self):
        """Updates the pixbuf with the saved thumbnail"""
        self.pixbuf = gtk.gdk.pixbuf_new_from_file(self.path)