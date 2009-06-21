#!/usr/bin/env python
try:
  import pynotify
  pynotify.init('PMS Notification')
except ImportError:
  #running windows
  import balloontips
import time
import gtk
import gtk.glade
import sys
import cgi
import gobject
from settings import Settings

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

        self.popup(header, formatted_msg, avatar)
        
    def change_users_online_status(self, came_online, went_offline):
        if len(came_online) == 0 and len(went_offline) == 0:
            return
        came_str = " ,".join(came_online) + " came online\n" if len(came_online) > 0 else ""
        went_str = " ,".join(went_offline) + " went offline" if len(went_offline) > 0 else ""
        print self
        self.popup("PMS", came_str + went_str, None)
        
    def hide(self):
        self.tray_icon.set_visible(False)
        
    def set_icon(self, state=Settings.LOGO1):
        self.tray_icon.set_from_file(state)
        
class WindowsNotifier(NotificationSystem):
    def __init__(self, main_program):
        NotificationSystem.__init__(self, main_program)
        #self.tray_icon = balloontips.DemoTaskbar(main_program)
        self.wTree = gtk.glade.XML(Settings.GLADE + "notification.glade")
        self.wTree.signal_autoconnect(self)
        
    def popup(self, header, formatted_msg, avatar):
        self.wTree.get_widget("header").set_markup("<b>%s</b>" % header)
        self.wTree.get_widget("message").set_text(formatted_msg)
        self.wTree.get_widget("avatar").set_from_pixbuf(avatar)
        self.wTree.get_widget("window").set_opacity(0.5)
        self.wTree.get_widget("window").set_gravity(gtk.gdk.GRAVITY_SOUTH_EAST)
        self.x, self.y = self.wTree.get_widget("window").get_size()
        self.wTree.get_widget("window").move(gtk.gdk.screen_width() - self.x, gtk.gdk.screen_height()-self.y)
        self.wTree.get_widget("window").show()
        self.in_progress = True
        self.fade_in_timer = gobject.timeout_add(100, self.fade_in)
        
    
    def fade_in(self):
        opacity = self.wTree.get_widget("window").get_opacity()
        opacity += 0.07
        if opacity >= 1:
            gobject.timeout_add(3000, self.wait)
            return False
        self.wTree.get_widget("window").set_opacity(opacity)
        return True
            
    def wait(self):
        self.fade_out_timer = gobject.timeout_add(100, self.fade_out)
        return False
      
    
    def fade_out(self):
        opacity = self.wTree.get_widget("window").get_opacity()
        opacity -= 0.07
        if opacity <= 0:
            self.in_progress = False
            return False
        self.wTree.get_widget("window").set_opacity(opacity)
        return True
        
        
        
    
class LinuxNotifier(NotificationSystem):
    def __init__(self, main_program):
        NotificationSystem.__init__(self, main_program)

        
    def popup(self, header, formatted_msg, avatar):
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
    
