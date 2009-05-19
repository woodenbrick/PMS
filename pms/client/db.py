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
                `session_key` varchar(200),
                `expiry` int(20)
            )"""
        ]
        self.create_tables(tables)
        
    def add_user(self, username, password):
        self.cursor.execute("""INSERT INTO users (username, password) VALUES (?, ?)""",
                            (username, password))
        self.db.commit()
    
    def remove_user(self, username):
        self.cursor.execute("""DELETE FROM users WHERE username = ?""",
                            (username,))
        self.db.commit()
        
    def update_user(self, details):
        self.cursor.execute("""UPDATE users SET last_login=:last_login,
                            session_key=:session_key, expiry=:expires
                            WHERE username=:user""", details)
        self.db.commit()
    
    def return_user_details(self, username=None):
        """If username is blank, get the last user"""
        if username is None:
            query = """SELECT * FROM users ORDER BY last_login DESC LIMIT 1"""
        else:
            query = """SELECT * FROM users WHERE username=%s""" % username
        self.cursor.execute(query)
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
            self.cursor.execute("SELECT * FROM messages ORDER BY date LIMIT 30")
        else:
            self.cursor.execute("""SELECT * FROM messages WHERE _group=? ORDER BY date LIMIT 30""",
                                (group,))
        return self.cursor
    
    
    def add_new(self, record_dict):
        self.cursor.execute("""INSERT INTO messages (username, _group, message, date)
                            VALUES (:user, :group, :data, :date)""", record_dict)
        self.db.commit()
        
    def last_date(self):
        """Return date of last recieved message"""
        self.cursor.execute("SELECT date FROM messages ORDER by date DESC LIMIT 1")
        t = self.cursor.fetchone()
        if t is None:
            #if the user doesnt have any messages locally
            #we will allow messages from the last 2 weeks
            t = [time.time() - 1209600]
        return t[0]



if __name__ == "__main__":
    db = DB("pmsDB")
    conn = libpms.AppEngineConnection("daniel")
    if not conn.load_session_key():
        sys.exit(conn.error)
    
    print "adding message"
    values = libpms.get_values("message", "group")
    print conn.app_engine_request(values, "/msg/add", auto_now=True)
    conn.app_engine_request({"time" : time.time() - 500,
                                "groups" : "danielgroup"}, "/msg/check")
    record = {}
    for item in conn.iter:
        record[item.tag] = item.text.strip()
        if item.tag == "date":
            db.add_new(record)
        
    #db.add_new(conn.xtree)
    ls = db.message_list()
    print 'messages'
    for l in ls:
        print l