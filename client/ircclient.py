from libs import irclib
irclib.DEBUG = True
import gtk
import os
import re
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
    url_tag = gtk.TextTag(name="url")
    url_tag.set_property("foreground", "blue")
    url_tag.set_property("underline", pango.UNDERLINE_SINGLE)
    tag_table.add(url_tag)
    tag_table.add(name_tag)
    tag_table.add(server_msg_tag)





class IRCGlobal():
    def __init__(self, username, network="irc.freenode.net", port=6667):
        self.username = username
        self.network = network
        self.port = port
        self.irc = irclib.IRC()
        gobject.timeout_add(1000, self.process)
        self.server = self.irc.server()
        self.server.connect(network, port, self.username)
    
    def reconnect(self):
        self.server.connect(self.network, self.port, self.username)

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
        self.wTree.get_widget("window1").set_title("PMS Chat: " + channel.split("pms_")[1])
        self.wTree.get_widget("window1").set_icon_from_file(Settings.LOGO1)
        self.wTree.get_widget("entry").get_buffer().connect_after("insert-text", self.remove_nl_cb)
        #self.wTree.get_widget("window1").connect("destroy", self.main_quit)
        self.view_buffer = self.wTree.get_widget("view").get_buffer()
        self.channel = channel
        self.conn = connection
        self.conn.set_handlers(self)
        set_tag_table(self.view_buffer)
        try:
            self.conn.server.join(self.channel)
        except irclib.ServerNotConnectedError:
            self.conn.reconnect()
        self.user_liststore = gtk.ListStore(str)
        self.wTree.get_widget("users").set_model(self.user_liststore)
        self.emoticons = self.create_emote_dict(self.wTree.get_widget("user_cont"))
        cell = gtk.CellRendererText()
        col = gtk.TreeViewColumn("Users", cell)
        col.add_attribute(cell, "text", 0)
        self.wTree.get_widget("users").append_column(col)
        self.scroller = self.wTree.get_widget("scrolledwindow").get_vadjustment()
        #setting the value now for autoscrolling
        self.scroller.value = self.scroller.upper
        
        #self.wTree.get_widget("user_cont").show_all()
    
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
            message = self.parse_for_changes(message)
            for item in message:
                if type(item) == str:
                    self.view_buffer.insert(iter, item)
                elif type(item) == URLLink:
                    start_mark = self.view_buffer.create_mark(None, iter, True)
                                        #self.view_buffer.get_end_iter(), True)
                    self.view_buffer.insert_at_cursor(item.url)
                    self.view_buffer.apply_tag_by_name("url", self.view_buffer.get_iter_at_mark(start_mark),
                                                        iter) #self.view_buffer.get_end_iter())            
                else:
                    #iter = self.view_buffer.get_end_iter()
                    anchor = self.view_buffer.create_child_anchor(iter)
                    self.wTree.get_widget("view").add_child_at_anchor(item, anchor)
                    item.show()
            self.view_buffer.insert(iter, "\n")
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
        self.conn.username = "_" + self.conn.username
        connection.nick(self.conn.username)
        self.conn.server.join(self.channel)
        
    
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
            try:
                self.conn.server.privmsg(self.channel, buffer.get_text(start, end).strip())
            except irclib.ServerNotConnectedError:
                print 'Not connected to server, reconnecting'
                self.conn.reconnect()
                self.conn.server.join(self.channel)
                print 'Sending message'
                self.conn.server.privmsg(self.channel, buffer.get_text(start, end).strip())
            self.render_message(self.convert_irc_name_to_pms(self.conn.username), buffer.get_text(start, end).strip())
            buffer.delete(start, end)
            
    def on_chat_window_destroy(self, widget):
        self.conn.server.part(self.channel, message="Bye")

    def parse_for_changes(self, text):
        """splits a string into sections and returns a list of strings, emotes and urls"""
        # looks for these chars and does emote conversion if necessary
        # : ) ( /
        search_list = "\)|\||\(|:|;|\\|\/"
        match = re.search(search_list, text)
        if not match:
            return [text]
        string_list = text.split(" ")
        for i in range(0, len(string_list)):
            if re.match("http:\/\/", string_list[i]):
                string_list[i] = URLLink(string_list[i])
                continue
            elif string_list[i] == "":
                continue
            else:
                #check db for matching emotes
                try:
                    image = gtk.Image()
                    image.set_from_file(os.path.join(Settings.IMAGES, "emotes",
                                                     self.emoticons[string_list[i]]))
                    string_list[i] = image
                except KeyError:
                    continue
        return string_list
    
    def create_emote_dict(self, container):
        """Creates and returns a dictionary containing emoticon responses
        eg. dic[':)'] = smile.png"""
        f = open(os.path.join(Settings.IMAGES, "emotes", "theme"), "r")
        emote_dic = {}
        button_box = gtk.HBox()
        button_box.set_spacing(5)
        count = 0
        for line in f:
            if re.match("^#|\[", line):
                continue
            emotes = [x for x in line.split(" ") if x != ""]
            for i in range(1, len(emotes)):
                emote_dic[emotes[i].strip()] = emotes[0].strip()
            if count < 60:
                im = gtk.Image()
                im.set_from_file(os.path.join(Settings.IMAGES, "emotes", emotes[0].strip()))
                button = gtk.EventBox()
                
                try:
                    button.connect("button-press-event", self.smiley_clicked, emotes[1].strip())
                    button.add(im)
                except IndexError:
                    pass
                if count % 5 == 0:
                    container.pack_start(button_box)
                    container.child_set_property(button_box, "expand", False)
                    if count != 60:
                        button_box = gtk.HBox()
                        button_box.set_spacing(5)
                button_box.pack_start(button, False, False, 0)
                count += 1
        return emote_dic
    
    def smiley_clicked(self, eventbox, event, png):
        self.wTree.get_widget("entry").get_buffer().insert_at_cursor(" " + png + " ")
        self.wTree.get_widget("entry").grab_focus()

    def on_smile_toggled(self, toggle_button):
        if toggle_button.get_active():
            self.wTree.get_widget("user_cont").show_all()
        else:
            self.wTree.get_widget("user_cont").hide()


    def main_quit(self, *args):
        gtk.main_quit()

#at the moment urls arent done correctly this will be fixed in a later version
class URLLink(object):
    def __init__(self, url):
        self.url = url
        
if __name__ == "__main__":
    client = IRCGlobal("wodemoneke")
    room = IRCRoom(client, "#pms-Debugging")
    gtk.main()