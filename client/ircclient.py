from libs import irclib
#irclib.DEBUG = True
import gtk
import pygtk
pygtk.require("2.0")
import gtk.glade
import sys
import gobject
import pango
import time
from settings import Settings

def set_tag_table(buffer):
    tag_table = buffer.get_tag_table()
    name_tag = gtk.TextTag("name")
    name_tag.set_property("foreground", "red")
    name_tag.set_property("weight", pango.WEIGHT_BOLD)
    server_msg_tag = gtk.TextTag("server_msg")
    server_msg_tag.set_property("foreground", "dark green")
    server_msg_tag.set_property("weight", pango.WEIGHT_BOLD)
    tag_table.add(name_tag)
    tag_table.add(server_msg_tag)


class IRCGlobal():
    def __init__(self, username, network="irc.freenode.net", port=6667):
        self.username = username
        self.irc = irclib.IRC()
        gobject.timeout_add(1000, self.process)
        self.server = self.irc.server()
        self.server.connect(network, port, self.username)


    def set_handlers(self, server_obj):
        self.irc.add_global_handler("welcome", server_obj.echo_server_response)
        self.irc.add_global_handler("privnotice", server_obj.echo_server_response)
        self.irc.add_global_handler("pubmsg", server_obj.handle_message)
        self.irc.add_global_handler("namreply", server_obj.handle_user_list)
        self.irc.add_global_handler("users", server_obj.handle_user_list)
        self.irc.add_global_handler("join", server_obj.handle_join_and_part)
        self.irc.add_global_handler("part", server_obj.handle_join_and_part)
        self.irc.add_global_handler("nicknameinuse", server_obj.nickname_in_use)
        
    def process(self):
        self.irc.process_once()
        return True
    


class IRCRoom():
    def __init__(self, connection, channel):
        self.wTree = gtk.glade.XML(Settings.GLADE + "irc.glade")
        self.wTree.signal_autoconnect(self)
        self.wTree.get_widget("entry").get_buffer().connect_after("insert-text", self.remove_nl_cb)
        self.view_buffer = self.wTree.get_widget("view").get_buffer()
        self.channel = channel
        self.conn = connection
        self.conn.set_handlers(self)
        set_tag_table(self.view_buffer)
        self.conn.server.join(self.channel)
        self.user_liststore = gtk.ListStore(str)
        self.wTree.get_widget("users").set_model(self.user_liststore)

        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn("Users", cell)
        col.add_attribute(cell, "text", 0)
        self.wTree.get_widget("users").append_column(col)
        self.scroller = self.wTree.get_widget("scrolledwindow").get_vadjustment()
        #setting the value now for autoscrolling
        self.scroller.value = self.scroller.upper
    
    def echo_server_response(self, connection, event):
        self.render_message("", event.arguments()[0], special=True)            


    def render_message(self, name, message, special=False):
        """special refers to join/part messages etc."""
        make_adj = True if self.scroller.value == self.scroller.upper else False
        local_time = time.strftime("[%H:%M] ", time.localtime(time.time()))
        iter = self.view_buffer.get_end_iter()
        self.view_buffer.insert(iter, local_time)
        if special:
            data = """%s %s\n""" % (name, message)
            self.view_buffer.insert_with_tags_by_name(iter, data, "server_msg")
        else:
            self.view_buffer.insert_with_tags_by_name(iter, name + ": ", "name")
            self.view_buffer.insert_at_cursor(message + "\n")
        self.wTree.get_widget("view").scroll_to_mark(self.view_buffer.get_insert(), 0.2)

    
    def remove_nl_cb(self, text_buffer, position, text, length):
        if text == "\n":
            text_buffer.set_text("")
    
    def handle_message(self, connection, event):
        """Adds a new message from the IRC room to the users buffer"""
        self.render_message(self.convert_irc_name_to_pms(event.source()), event.arguments()[0])
        
    def handle_join_and_part(self, connection, event):
        """A new user enters the room"""
        if event.target() != self.channel:
            return
        name = self.convert_irc_name_to_pms(event.source())
        if event.eventtype() == "join":
            action = "has joined the room"
            if name != self.convert_irc_name_to_pms(self.conn.username):
                self.user_liststore.append([name])
        else:
            action = "has left the room"
            iter = self.user_liststore.get_iter_first()
            while iter is not None:
                if name == self.user_liststore.get_value(iter, 0):
                    self.user_liststore.remove(iter)
                    break
                iter = self.user_liststore.iter_next(iter)
        self.render_message(name, action, special=True)

    
    def nickname_in_use(self, connection, event):
        self.render_message("", "This nickname is already in use", special=True)
    
    def handle_user_list(self, connection, event):
        """Gets the userlist for this room as we enter"""
        if event.arguments()[1] != self.channel:            
            return
        users = event.arguments()[2].split(" ")
        for user in users:
            u = user.strip("@")
            if u != "":
                self.user_liststore.append([self.convert_irc_name_to_pms(u)])
    
    def convert_irc_name_to_pms(self, irc_name):
        irc_name = irc_name.split("!")[0]
        return irc_name[irc_name.find("_")+1:]
    
    def on_entry_key_press_event(self, textview, key):
        if key.keyval == 65293:
            buffer = self.wTree.get_widget("entry").get_buffer()
            start, end = buffer.get_bounds()
            self.conn.server.privmsg(self.channel, buffer.get_text(start, end).strip())
            self.render_message(self.convert_irc_name_to_pms(self.conn.username), buffer.get_text(start, end).strip())
            buffer.delete(start, end)
            
    def on_chat_window_destroy(self, widget):
        self.conn.server.part(self.channel, message="Bye")


