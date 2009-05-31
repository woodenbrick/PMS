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
import logger

log = logger.new_logger("DATABASE")

class DB(object):
    
    def __init__(self, db_name):
        self.db = sqlite3.Connection(db_name)
        self.cursor = self.db.cursor()

        
    def close_connection(self):
        self.db.close()
        
    def create_tables(self, table_list):
        log.info("Creating tables")
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
            )"""
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
        
        
    def auto_login_user(self, username, auto_login):
        """Sets a user to be autologged in.
        caveats: the user will only be autologged in if they were the last person
        logged in with a saved password"""
        log.info("Setting user to autologin: %s" % auto_login)
        self.cursor.execute("""UPDATE users SET auto_login=? WHERE username=?""", (auto_login, username))
        self.db.commit()
    
    def return_user_details(self, username=None):
        """If username is blank, get the last user"""
        if username is None:
            log.info("Retrieving last user")
            self.cursor.execute("""SELECT * FROM users ORDER BY last_login DESC LIMIT 1""")
        else:
            log.info("Retrieving specific user: %s" % username)
            self.cursor.execute("""SELECT * FROM users WHERE username=?""", (username,))
        return self.cursor.fetchone()
        


class MessageDB(DB):
    
    def __init__(self, db_name):
        DB.__init__(self, db_name)
        tables = [
            """CREATE TABLE IF NOT EXISTS `messages` (
                `username` varchar(50) NOT NULL,
                `_group` varchar(50) NOT NULL,
                `message` blob,
                `date` integer(12)
            )"""
            ]
        self.create_tables(tables)


    def message_list(self, group=None):
        """Returns a cursor containing the last 30 messages. If group is None
        then messages from all groups are returned"""
        if group is None:
            log.info("Retrieving messages for all groups")
            self.cursor.execute("SELECT * FROM messages ORDER BY date DESC LIMIT 30")
        else:
            log.info("Retrieving messages for group %s" % group)
            self.cursor.execute("""SELECT * FROM messages WHERE _group=? ORDER BY date DESC LIMIT 30""",
                                (group,))
        return self.cursor
    
    
    def add_new(self, record_dict):
        log.info("Adding new message")
        self.cursor.execute("""INSERT INTO messages (username, _group, message, date)
                            VALUES (:user, :group, :data, :date)""", record_dict)
        self.db.commit()
        
    def last_date(self):
        """Return date of last recieved message"""
        log.info("Retrieving date of last message")
        self.cursor.execute("SELECT date FROM messages ORDER by date DESC LIMIT 1")
        t = self.cursor.fetchone()
        
        if t is None:
            log.info("No messages, using default date of 2 weeks ago")
            #if the user doesnt have any messages locally
            #we will allow messages from the last 2 weeks
            t = [time.time() - 1209600]
        else:
            log.debug("Last message sent at: %s" % t[0])
        return t[0]
