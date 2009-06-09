#!/usr/bin/env python
try:
  import pynotify
  pynotify.init('PMS Notification')
except ImportError:
  #running windows
  import balloontips
import time
import gtk
import sys

class NotificationSystem(object):
    
    def __init__(self, main_program):
        self.main_program = main_program
        self.timeout = 5
    
    def new_message(self, last_msg, msg_count, nicetime, avatar):
        if not self.main_program.main_window.is_active():
            self.set_icon("logo2")
        header = "%(user)s said:" % last_msg
        if msg_count > 1:
            footer = "You have %d other unread messages" % (msg_count - 1,)
        else:
            footer = ""
        formatted_msg = "%s (sent %s) %s" % (last_msg['data'], nicetime, footer)
        self.popup(header, formatted_msg, avatar)
        

        
class WindowsNotifier(NotificationSystem):
    def __init__(self, main_program):
        NotificationSystem.__init__(self, main_program)
        self.tray_icon = balloontips.DemoTaskbar(self.main_program)
        
    def popup(self, header, formatted_msg, avatar):
        #currently i dont know how to show windows users avatar in bubble
        #may not be possible
        self.tray_icon.new_message(header, formatted_msg, self.timeout)
        
    def hide(self):
        self.tray_icon.OnDestroy()
        
    def set_icon(self, state="logo1"):
        #currently not working
        pass
        #self.tray_icon.update_icon(self.main_program.PROGRAM_DETAILS[state])           
            
        
    
class LinuxNotifier(NotificationSystem):
    def __init__(self, main_program):
        NotificationSystem.__init__(self, main_program)
        self.tray_icon = gtk.StatusIcon()
        self.tray_icon.set_from_file(self.main_program.PROGRAM_DETAILS['logo1'])
        self.tray_icon.connect("activate", self.main_program.activate_menu, None)
        self.tray_icon.connect("popup-menu", self.main_program.popup_menu, None)
        
    def popup(self, header, formatted_msg, avatar):
        n = pynotify.Notification(header, formatted_msg)
        #timeout seems to cause breakage?
        #n.set_timeout(self.timeout)
        n.set_icon_from_pixbuf(avatar)
        n.add_action("open_program", "Open", self.open_program_cb)
        n.attach_to_status_icon(self.tray_icon)
        n.show()
        
    def hide(self):
        self.tray_icon.set_visible(False)
        
    def set_icon(self, state="logo1"):
        self.tray_icon.set_from_file(self.main_program.PROGRAM_DETAILS[state])
        
    def open_program_cb(self, n, action):
        assert action == "open_program"
        n.close()
        #open program
        self.main_program.main_window.show()
    
