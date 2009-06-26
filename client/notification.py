#!/usr/bin/env python

import time
import gtk
import gtk.glade
import sys
import cgi
import gobject
from settings import Settings
from libs import gtkPopupNotify

class NotificationSystem(object):
    
    def __init__(self, main_program):
        self.main_program = main_program
        self.tray_icon = gtk.StatusIcon()
        self.tray_icon.set_from_file(Settings.LOGO1)
        self.tray_icon.connect("activate", self.main_program.activate_menu, None)
        self.tray_icon.connect("popup-menu", self.main_program.popup_menu, None)
        self.timeout = 5
    
    def new_message(self, last_msg, msg_count, nicetime, avatar):
        header = "%s -> %s" % (last_msg[1], last_msg[2])
        if msg_count > 1:
            footer = "You have %d other unread messages" % (msg_count - 1,)
        else:
            footer = ""

        formatted_msg = "%s\n%s\n%s" % (cgi.escape(last_msg[3]), nicetime, footer)

        self.new_popup(header, formatted_msg, avatar)
        
    def change_users_online_status(self, came_online, went_offline, avatars):
        if len(came_online) == 0 and len(went_offline) == 0:
            return False
        try:
            avatar = avatars[came_online[0]].pixbuf
        except:
            try:
                avatar = avatars[went_offline[0]].pixbuf
            except:
                avatar = gtk.gdk.pixbuf_new_from_file(Settings.LOGO1_SMALL)
        came_str = ", ".join(came_online) + " came online. " if len(came_online) > 0 else ""
        went_str = ", ".join(went_offline) + " went offline." if len(went_offline) > 0 else ""
        
        self.new_popup("PMS", came_str + went_str, avatar)
        
    def hide(self):
        self.tray_icon.set_visible(False)
        
    def set_icon(self, state=Settings.LOGO1):
        self.tray_icon.set_from_file(state)
        
        

class CrossPlatformNotifier(NotificationSystem, gtkPopupNotify.NotificationStack):
    def __init__(self, main_program):
        NotificationSystem.__init__(self, main_program)
        gtkPopupNotify.NotificationStack.__init__(self)
        self.edge_offset_y = 30
        #self.bg_color = gtk.gdk.Color("green")
    
    

class LinuxNotifier(NotificationSystem):
    def __init__(self, main_program):
        #notification system based on pynotify
        import pynotify
        pynotify.init('PMS Notification')
        NotificationSystem.__init__(self, main_program)

        
    def new_popup(self, header, formatted_msg, avatar):
        if sys.platform == "linux2":
            n = pynotify.Notification(header, formatted_msg)
            #timeout seems to cause breakage?
            #n.set_timeout(self.timeout)
            try:
                n.set_icon_from_pixbuf(avatar)
            except TypeError:
                pass
            n.add_action("open_program", "Open PMS", self.open_program_cb)
            n.add_action("clear_new", "OK Thanks", self.clear_taskbar_cb)
            n.attach_to_status_icon(self.tray_icon)
            n.show()
        else:
            print 'Currently windows notifications are not supported'
        

    
    def clear_taskbar_cb(self, n, action):
        assert action == "clear_new"
        n.close()
        
       
        
    def open_program_cb(self, n, action):
        assert action == "open_program"
        print "open programs"
        n.close()
        #open program
        self.main_program.main_window.show()





if __name__ == "__main__":
    
    def notify_factory():
        notifier.popup("Hello", "Hello Hello", None)
        return True

    notifier = WindowsNotifier(None)
    Settings.GLADE = "client/glade/"
    gobject.timeout_add(2000, notify_factory)
    gtk.main()
