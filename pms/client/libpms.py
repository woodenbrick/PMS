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

import os
import sys
import urllib, urllib2
import random
import string
import hashlib
import time
import cPickle
from xml.etree import ElementTree as ET

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers


class AppEngineConnection(object):
    def __init__(self, server):
        self.url = server
        self.HOMEDIR = os.path.join(os.environ['HOME'], ".eventnotify") + os.sep
        if not os.path.exists(self.HOMEDIR):
            os.mkdir(self.HOMEDIR)
        self.default_values = {}
        
    def check_xml_response(self, doc):
        """Check if our request was valid"""
        self.xtree = ET.parse(doc)
        self.iter = self.xtree.getiterator()
        status = self.iter[0].attrib['status']
        if status != "OK":
            self.error = self.iter[0].text
            print "error", self.error
        return status

    
    def get_tag(self, tag):
        """returns the first text from a tag"""
        return self.xtree.find(tag).text
        
    def get_tags(self, tag):
        """returns a list of texts with tag"""
        l = []
        for i in self.iter:
            if i.tag == tag:
                l.append(i.text.strip())
        return l

    def app_engine_request(self, data, mapping, auto_now=False):
        """For get requests, set data to None"""
        if data is None:
            try:
                request = urllib2.urlopen(self.url + mapping)
            except urllib2.URLError:
                return "Server not found"
            return self.check_xml_response(request)
        if auto_now:
            data['time'] = time.time()
        data.update(self.default_values)
        encoded_values = urllib.urlencode(data)
        try:
            request = urllib2.urlopen(self.url + mapping, encoded_values)
        except urllib2.URLError, e:
            return e
        return self.check_xml_response(request)
        
    def send_avatar(self, filename):
        """A special function for this, since it requires images to be sent which
        cannot be done in an easy way"""
        register_openers()
        data = {"avatar": open(filename)}
        data.update(self.default_values)
        datagen, headers = multipart_encode(data)
        request = urllib2.Request(self.url + "/usr/changeavatar", datagen, headers)
        return self.check_xml_response(urllib2.urlopen(request))
        
    
def get_values(*args):
    """A simple commandline raw input parser to get values to send to the server
    special values: password hashes the input, salt creates a salt automatically"""
    vals = {}
    for arg in args:
        vals[arg] = raw_input("Enter value for %s: " % arg)
        if arg == "password":
            if vals["password"] != "":
                vals[arg] = hashlib.sha1(vals[arg]).hexdigest()
                vals["passreq"] = 1
            else:
                vals["passreq"] = 0
    return vals




def run():
    user = raw_input("Login as: (blank for new user) ")
    conn = AppEngineConnection(username=user)
    if not conn.load_session_key():
        sys.exit(conn.error)
    #all_groups = conn.app_engine_request({}, "/group/list")
    #print all_groups
    #msgs = OldMessages(conn.username)
    #groups = conn.app_engine_request({}, "/usr/groups")
    #print "groups:", groups
    #while True:
    #    print "Checking for new messages:"
    #    values = { "time" : msgs.last_time, "groups" : groups}
    #    new_messages =  conn.app_engine_request(values, "/msg/check")
    #    for line in new_messages:
    #        print line
            #msgs.last_time = time.time()
    #    time.sleep(4)
    ##print "join group"
    #values = get_values("group", "password")
    #print conn.app_engine_request(values, "/group/join")
    print "create group"
    values = get_values("group", "password")
    print conn.app_engine_request(values, "/group/add", auto_now=True)
    print "adding message"
    values = get_values("message", "group")
    print conn.app_engine_request(values, "/msg/add", auto_now=True)
    return conn.app_engine_request({"time" : time.time() - 500,
                                "groups" : "danielgroup"}, "/msg/check")
