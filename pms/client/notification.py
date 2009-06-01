#!/usr/bin/env python
try:
    import pynotify
    pynotify.init('PMS Notification')
except ImportError:
    #presumably we are on windows
    pass
import time
import gtk



class NotificationSystem(object):
    
    def __init__(self, main_program):
        self.main_program = main_program
    
    def new_message(self, last_msg, msg_count, nicetime, avatar):
        #this is currently useless on windows
        if sys.platform == "win32":
            return
        header = "%(user)s said:" % last_msg
        if msg_count > 1:
            footer = "\nYou have %d other unread messages" % (msg_count - 1,)
        else:
            footer = ""
        formatted_msg = "%s\n\n%s%s" % (last_msg['data'], nicetime, footer)
        n = pynotify.Notification(header, formatted_msg)
        n.set_timeout(5)
        n.set_icon_from_pixbuf(avatar)
        n.add_action("open_program", "Open", self.open_program_cb)
        n.attach_to_status_icon(self.main_program.tray_icon)
        n.show()
        
    def open_program_cb(self, n, action):
        assert action == "open_program"
        n.close()
        #open program
        print 'opening program'
        self.main_program.main_window.show()