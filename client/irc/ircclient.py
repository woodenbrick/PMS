from irclib import irclib
irclib.DEBUG = True
import gtk
import pygtk
pygtk.require("2.0")
import gtk.glade
import sys
import gobject
import pango
import time

class IRCThread():
    def __init__(self):
        irc = irclib.IRC()
        irc.add_global_handler("pubmsg", self.handlePrivMessage)
        irc.add_global_handler("join", self.handle_on_join)
        self.server = irc.server()
        self.server.connect(network, 6667, nick)
        self.server.join(self.channel)
        irc.process_forever()
    
    
    def handlePrivMessage (self, connection, event ):
        print event.source().split ( '!' ) [ 0 ] + ': ' + event.arguments() [ 0 ]
        if event.arguments() [ 0 ].lower().find ( 'hello' ) == 0:
            connection.privmsg ( event.source().split ( '!' ) [ 0 ], 'Hello.' )
    
    def handle_on_join(self, connection, event):
        print event.source()
        print event.arguments()
    
    def send(self, data=None):
        if data is None:
            data = "FUCK"
        self.server.privmsg(self.channel, data)
        return True
        
    def close(self):
        self.server.disconnect("Fucking off")
        
 


class IRCClient():
    def __init__(self, username, channel, network="irc.freenode.net", port=6667):
        self.wTree = gtk.glade.XML("client.glade")
        self.wTree.signal_autoconnect(self)
        self.view_buffer = self.wTree.get_widget("view").get_buffer()
        self.username = username
        self.channel = channel
        #self.sockets = []
        self.irc = irclib.IRC()#self.add_socket, self.remove_socket, self.timeout_socket)
        self.irc.add_global_handler("welcome", self.echo_server_response)
        self.irc.add_global_handler("privnotice", self.echo_server_response)
        self.irc.add_global_handler("pubmsg", self.handle_message)
        self.irc.add_global_handler("namreply", self.handle_user_list)
        self.irc.add_global_handler("users", self.handle_user_list)
        self.irc.add_global_handler("join", self.handle_join_and_part)
        self.irc.add_global_handler("part", self.handle_join_and_part)

        self.server = self.irc.server()
        self.server.connect(network, port, self.username)
        self.server.join(self.channel)
        self.user_liststore = gtk.ListStore(str)
        self.wTree.get_widget("users").set_model(self.user_liststore)
        gobject.timeout_add(1000, self.process)
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn("Users", cell)
        col.add_attribute(cell, "text", 0)
        self.wTree.get_widget("users").append_column(col)

        self.tag_table = self.view_buffer.get_tag_table()
        name_tag = gtk.TextTag("name")
        name_tag.set_property("foreground", "red")
        name_tag.set_property("weight", pango.WEIGHT_BOLD)
        server_msg_tag = gtk.TextTag("server_msg")
        server_msg_tag.set_property("foreground", "dark green")
        server_msg_tag.set_property("weight", pango.WEIGHT_BOLD)
        self.tag_table.add(name_tag)
        self.tag_table.add(server_msg_tag)
        
    def process(self):
        self.irc.process_once()
        return True
    
    #IRC HANDLERS
    
    def render_message(self, name, message, special=False):
        """special refers to join/part messages etc."""
        make_adj = True if self.wTree.get_widget("scrolledwindow").get_vadjustment().value == 0 else False
        local_time = time.strftime("[%H:%M] ", time.localtime(time.time()))
        self.view_buffer.insert_at_cursor(local_time)
        iter = self.view_buffer.get_end_iter()
        if special:
            data = """%s %s\n""" % (name, message)
            self.view_buffer.insert_with_tags_by_name(iter, data, "server_msg")
        else:
            self.view_buffer.insert_with_tags_by_name(iter, name + ": ", "name")
            self.view_buffer.insert_at_cursor(message + "\n")
        if make_adj:
            vadj = self.wTree.get_widget("scrolledwindow").get_vadjustment()
            vadj.value = -1
    
    def echo_server_response(self, connection, event):
        self.render_message("", event.arguments()[0], special=True)
    
    def handle_message(self, connection, event):
        """Adds a new message from the IRC room to the users buffer"""
        self.render_message(event.source().split('!')[0], event.arguments()[0])
        
    def handle_join_and_part(self, connection, event):
        """A new user enters the room"""
        name = event.source().split("!")[0]
        if event.eventtype() == "join":
            action = "has joined the room"
            if name != self.username:
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

        
    def handle_user_list(self, connection, event):
        """Gets the userlist for this room as we enter"""
        users = event.arguments()[2].split(" ")
        print str(users)
        for user in users:
            u = user.strip("@")
            if u != "":
                self.user_liststore.append([u])
    
    #def add_socket(self, sock):
    #    print 'appending socket', sock
    #    self.sockets.append(sock)
    #    self.check_this_bad_body()
    #    
    #def remove_socket(self, sock):
    #    print 'removing socket', sock
    #    i = self.sockets.find(sock)
    #    self.sockets.pop(i)
    #    
    #def timeout_socket(self, seconds):
    #    print 'timeout is ', seconds, "seconds"
    #    
    #    
    #def check_this_bad_body(self):
    #    self.irc.process_data(self.sockets)
    
    def on_entry_key_press_event(self, textview, key):
        if key.keyval == 65293:
            self.server.privmsg(self.channel, self.wTree.get_widget("entry").get_text())
            self.render_message(self.username, self.wTree.get_widget("entry").get_text())
            self.wTree.get_widget("entry").set_text("")
            
    

    def on_chat_window_destroy(self, widget):
        self.irc.disconnect_all(message="Bye")
        gtk.main_quit()
    
IRCClient("woodenbrick", "#testmoneke")
gtk.main()
