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

import sqlite3
from xml.etree import ElementTree as ET
import time
import libpms
import datetime
from misc import new_logger
from settings import Settings
log = new_logger("database.py")

class DB(object):
    
    def __init__(self, db_name):
        self.db = sqlite3.Connection(db_name)
        self.cursor = self.db.cursor()

        
    def close_connection(self):
        self.db.close()
        
    def create_tables(self, table_list):
        for query in table_list:
            self.cursor.execute(query)
        self.db.commit()



class UserDB(DB):
    
    def __init__(self, db_name):
        DB.__init__(self, db_name)
        tables = [
            """CREATE TABLE IF NOT EXISTS `users` (
                `username` varchar(50) NOT NULL,
                `password` varchar(200) NOT NULL,
                `last_login` int(20),
                `auto_login` boolean default 0
            )""",
            
            """CREATE TABLE IF NOT EXISTS `avatars` (
                `username` varchar(50),
                `avatar_time` int(20)
            )""",
            
            """CREATE TABLE IF NOT EXISTS `facebook` (
                `username` varchar(50),
                `session_key` varchar(255),
                `uid` int(20),
                `expiry` int(20),
                `last_time` int(20),
                `offline_access` boolean,
                `publish_stream` boolean
            )""",
            
            """CREATE TABLE IF NOT EXISTS `facebook_avatars` (
                `username` varchar(50),
                `path` text
            )""",
        ]
        self.create_tables(tables)
        
    def add_user(self, username, password):
        self.cursor.execute("""SELECT * FROM users WHERE username=?""", (username,))
        if self.cursor.fetchone() is None:
            log.info("Creating new user")
            self.cursor.execute("""INSERT INTO users (username, password) VALUES (?, ?)""",
                            (username, password))
        else:
            log.info("Updating previous user")
            self.cursor.execute("""UPDATE users set password=? WHERE username=?""",
                            (password, username))
            self.db.commit()
    
    def update_login_time(self, username):
        self.cursor.execute("""UPDATE users set last_login=? WHERE username=?""", (time.time(),
                                                                                    username))
        self.db.commit()
    
    def remove_user(self, username):
        log.info("Deleting user")
        self.cursor.execute("""DELETE FROM users WHERE username = ?""",
                            (username,))
        self.db.commit()
        
    
    def return_user_details(self, username=None):
        """If username is blank, get the last user"""
        if username is None:
            self.cursor.execute("""SELECT * FROM users ORDER BY last_login DESC LIMIT 1""")
        else:
            self.cursor.execute("""SELECT * FROM users WHERE username=?""", (username,))
        return self.cursor.fetchone()
        
    def update_avatar(self, username, upload_time):
        """At the moment we are storing the avatars seperatly in the future
        they will be stored here"""
        u = self.cursor.execute("""select * from avatars WHERE username=?""", (username,)).fetchone()
        if u is None:
            self.cursor.execute("""insert into avatars (username, avatar_time) VALUES
                                 (?, ?)""", (username, upload_time))
        else:
            self.cursor.execute("""update avatars set avatar_time=? WHERE username=?""",
                            (upload_time, username))
        self.db.commit()
        
    def get_avatar_time(self):
        """Returns the time of the last avatar downloaded"""
        self.cursor.execute("""SELECT avatar_time FROM avatars ORDER BY avatar_time LIMIT 1""")
        last_time = self.cursor.fetchone()
        if last_time is None:
            log.debug("No avatar time recorded, requesting all")
            return "all"
        return last_time[0]
    
        


class MessageDB(DB):
    
    def __init__(self, db_name):
        DB.__init__(self, db_name)
        tables = [
            """CREATE TABLE IF NOT EXISTS `messages` (
                `username` varchar(50) NOT NULL,
                `_group` varchar(50) NOT NULL,
                `message` blob,
                `date` integer(12)
            )""",
            ]
        self.create_tables(tables)


    def message_list(self, group=None):
        """Returns a cursor containing the last 30 messages. If group is None
        then messages from all groups are returned"""
        if group is None:
            self.cursor.execute("SELECT distinct * FROM messages ORDER BY date DESC LIMIT 30")
        else:
            self.cursor.execute("""SELECT distinct * FROM messages WHERE _group=? ORDER BY date DESC LIMIT 30""",
                                (group,))
        return self.cursor.fetchall()
    

    def add_new(self, data):
        self.cursor.execute("""INSERT INTO messages (username, _group, message, date)
                            VALUES (?, ?, ?, ?)""", (data[1], data[2], data[3], data[4]))
        self.db.commit()
        
    def last_date(self):
        """Return date of last recieved message"""
        self.cursor.execute("SELECT date, message FROM messages ORDER by date DESC LIMIT 1")
        t = self.cursor.fetchone()
        
        if t is None:
            log.info("No messages, using default date of 2 weeks ago")
            #if the user doesnt have any messages locally
            #we will allow messages from the last 2 weeks
            t = [time.time() - 1209600, None]
        else:
            log.debug("Last message sent at: %s" % t[0])
        return int(t[0]), t[1]
