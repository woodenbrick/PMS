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
        
    def change_users_online_status(self, came_online, went_offline, avatars):
        if len(came_online) == 0 and len(went_offline) == 0:
            return False
        try:
            avatar = avatars[came_online[0]].pixbuf
        except IndexError:
            try:
                avatar = avatars[went_offline[0]].pixbuf
            except IndexError:
                avatar = gtk.gdk.pixbuf_new_from_file(Settings.LOGO1_SMALL)
        came_str = ", ".join(came_online) + " came online\n" if len(came_online) > 0 else ""
        went_str = ", ".join(went_offline) + " went offline" if len(went_offline) > 0 else ""
        
        self.popup("PMS", came_str + went_str, avatar)
        
    def hide(self):
        self.tray_icon.set_visible(False)
        
    def set_icon(self, state=Settings.LOGO1):
        self.tray_icon.set_from_file(state)
        
class WindowsNotifier(NotificationSystem):
    def __init__(self, main_program):
        NotificationSystem.__init__(self, main_program)
        self.notify_stack = []
        self.offset = 0
        
    def popup(self, header, formatted_msg, avatar):
        self.notify_stack.append(WindowsPopup(self.offset, self.destroy_popup_cb,
                                              header, formatted_msg, avatar))
        self.offset += self.notify_stack[-1].y
        
    def destroy_popup_cb(self, popup):
        self.notify_stack.remove(popup)
        #move them about
        offset = 0
        for note in self.notify_stack:
            offset = note.reposition(offset)
        self.offset = offset
    
    
class WindowsPopup(object):
    def __init__(self, offset, destroy_cb, header, formatted_msg, avatar):
        self.destroy_cb = destroy_cb
        self.wTree = gtk.glade.XML(Settings.GLADE + "notification.glade")
        self.wTree.signal_autoconnect(self)
        self.wTree.get_widget("header").set_markup("<b>%s</b>" % header)
        self.wTree.get_widget("message").set_text(formatted_msg)
        self.wTree.get_widget("avatar").set_from_pixbuf(avatar)
        self.window = self.wTree.get_widget("window")
        self.x, self.y = self.window.get_size()
        self.window.move(gtk.gdk.screen_width() - self.x, gtk.gdk.screen_height()- self.y - offset)
        self.window.show()
        self.wTree.get_widget("counter").set_markup("<b>5</b>")
        self.fade_in_timer = gobject.timeout_add(100, self.fade_in)
        self.hover = False
        
    
    def reposition(self, offset):
        """reposition any popups after old ones have disappeared
        new position is this popups position in the stack, offset is
        the offset from the bottom of the entire stack"""
        new_offset = self.y + offset
        self.window.move(gtk.gdk.screen_width()-self.x, gtk.gdk.screen_height()-new_offset)
        return new_offset

    
    def fade_in(self):
        opacity = self.window.get_opacity()
        opacity += 0.10
        if opacity >= 1:
            self.counter = 5
            self.wait_timer = gobject.timeout_add(1000, self.wait)
            return False
        self.window.set_opacity(opacity)
        return True
            
    def wait(self):
        if not self.hover:
            self.counter -= 1
        self.wTree.get_widget("counter").set_markup(str("<b>%s</b>" % self.counter))
        if self.counter == 0:
            self.fade_out_timer = gobject.timeout_add(100, self.fade_out)
            return False

        return True
      
    
    def fade_out(self):
        opacity = self.window.get_opacity()
        opacity -= 0.10
        if opacity <= 0:
            self.in_progress = False
            self.hide_notification()
            return False
        self.window.set_opacity(opacity)
        return True
    
    def on_window_enter_notify_event(self, *args):
        self.hover = True
    
    def on_window_leave_notify_event(self, *args):
        self.hover = False
        
    def hide_notification(self, *args):
        """The user has clicked the 'X' in the corner to close"""
        #destroy timers if they are running
        for timer in ("fade_in_timer", "fade_out_timer", "wait_timer"):
            if hasattr(self, timer):
                gobject.source_remove(getattr(self, timer))
        self.window.destroy()
        self.destroy_cb(self)
    
    
    

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





if __name__ == "__main__":
    
    def notify_factory():
        notifier.popup("Hello", "Hello Hello", None)
        return True

    notifier = WindowsNotifier(None)
    Settings.GLADE = "client/glade/"
    gobject.timeout_add(2000, notify_factory)
    gtk.main()
