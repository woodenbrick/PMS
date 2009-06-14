#libpms.py
"""A library to connect to the server and parse its responses"""
#Copyright 2009 Daniel Woodhouse
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
import gtk
import cPickle
import threading
import Queue

from xml.etree import ElementTree as ET
from settings import Settings
from misc import new_logger
log = new_logger("libpms.py", Settings.LOGGING_LEVEL)

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers


class ThreadedAppEngineRequest(threading.Thread):
    """
    Creates a new thread for a request to the server
    """
    def __init__(self, gae_conn_obj, data, mapping, auto_now, get_avatar, queue):
        self.gae_conn_obj = gae_conn_obj
        self.data = data
        self.mapping = mapping
        self.auto_now = auto_now
        self.queue = queue
        self.get_avatar = get_avatar
        threading.Thread.__init__(self)

        
    def run(self):
        response = self.gae_conn_obj._app_engine_request(self.data, self.mapping,
                                                         self.auto_now, self.get_avatar)
        self.queue.put(response)



class AppEngineConnection(object):
    """Creates a new connection to the GAE"""
    
    def __init__(self):
        self.default_values = {}
        self.error = ""
        self.queue = Queue.Queue()
        
    def check_xml_response(self, doc):
        """Returns the status string of the servers response and sets
        an error message if there was a problem"""
        self.xtree = ET.parse(doc)
        self.iter = self.xtree.getiterator()
        status = self.iter[0].attrib['status']
        if status != "OK":
            self.error = self.iter[0].text
            log.error(self.error)
        return status

    
    def get_tag(self, tag):
        """Returns the first text from a tag"""
        return self.xtree.find(tag).text
        
    def get_tags(self, tag):
        """Returns a list of texts with given tag"""
        l = []
        for i in self.iter:
            if i.tag == tag:
                l.append(i.text.strip())
        return l
    
    def set_password(self, password):
        self.password = password
    
    def app_engine_request(self, data, mapping, auto_now=False, get_avatar=False):
        """
        A wrapper to start a new thread for pms.client.libpms._app_engine_request
         :Parameters:
          - data: A dictionary of data to be sent to the server or none for a GET request
          - mapping: A valid mapping (see `pms.server.server.application` for all valid mappings)
          - auto_now: True if the current time should be included in the request
          - get_avatar: True if the request is to download an image
        """
        request = ThreadedAppEngineRequest(self, data, mapping, auto_now,
                                           get_avatar, self.queue)
        request.daemon = True
        request.start()
        while request.isAlive():
            gtk.main_iteration()
        response = self.queue.get()
        return response
    
    def _app_engine_request(self, data, mapping, auto_now=False, get_avatar=False):
        """
        `pms.client.libpms.app_engine_request` should be used if you want a threaded request
        """
        if data is None:
            log.debug("GET request: %s" % mapping)
            if get_avatar:
                log.debug("%s %s %s" % (Settings.SERVER, mapping, get_avatar))
                try:
                    req = urllib.urlretrieve(Settings.SERVER + mapping, get_avatar)
                    return True
                except:
                    return False
                
            try:
                request = urllib2.urlopen(Settings.SERVER + mapping)
            except urllib2.URLError, e:
                log.error(e)
                self.error = str(e)
                return "URLError"
            return self.check_xml_response(request)
        if auto_now:
            data['time'] = time.time()
        try:
            data['name']
        except KeyError:
            data['name'] = self.default_values['name']
        try:
            data['session_key'] = self.default_values['session_key']
        except KeyError:
            pass
        encoded_values = urllib.urlencode(data)
        log.debug("POST request: %s" % mapping)
        log.debug("POST DATA %s" % data)
        try:
            request = urllib2.urlopen(Settings.SERVER + mapping, encoded_values)
        except urllib2.URLError, e:
            log.error(e)
            self.error = str(e)
            return "URLError"
        response = self.check_xml_response(request)
        if response == "BADAUTH":
            log.info("Outdated sessionkey, attempting renewal")
            #outdated sessionkey, get a newone then redo the request
            sess_data = {"name" : self.default_values['name'],
                         "password" : self.password}
            new_response = self._app_engine_request(sess_data, "/getsessionkey", auto_now=True)
            if new_response == "OK":
                log.info("Redoing defered call")
                self.default_values["session_key"] = self.get_tag("key")
                self.expires = int(self.get_tag("expires"))
                self.dump_session_key()
                response = self._app_engine_request(data, mapping)
        return response
    
    def dump_session_key(self):
        """
        Pickles the downloaded session key
        """
        f = open(Settings.HOME + "sessionkey_" + self.default_values['name'], "w")
        log.info("Saving session key")
        cPickle.dump([self.default_values['session_key'], self.expires], f)
        f.close()
        
        
    def check_for_session_key(self, username):
        """
        Check if there is a pickled session key
        return sessionkey or False if the key doesn't exist or is outdated"""
        try:
            f = open(Settings.HOME + "sessionkey_" + username, "r")
        except IOError:
            log.info("No session key available")
            return False
        self.default_values['session_key'], self.expires = cPickle.load(f)
        f.close()
        if self.expires <= time.time():
            log.info("Outdated session key")
            return False
        log.info("Session key available, expires in %s minutes" % ((self.expires - time.time()) / 60))
        return self.default_values['session_key']

    def send_avatar(self, filename):
        """
        Send an image to the server
         :Parameters:
          - filename: The path to the filename that is to be uploaded
        """
        register_openers()
        data = {"avatar": open(filename)}
        data.update(self.default_values)
        datagen, headers = multipart_encode(data)
        request = urllib2.Request(Settings.SERVER + "/usr/changeavatar", datagen, headers)
        return self.check_xml_response(urllib2.urlopen(request))
        
import facebook       
class ThreadedFBConnection(threading.Thread):
    
    def __init__(self, fblib_call, data, queue):
        self.fblib_call = fblib_call
        self.data = data
        self.queue = queue
        threading.Thread.__init__(self)

        
    def run(self):
        try:
            response = self.fblib_call(self.data)
            self.queue.put(response)
        except facebook.FacebookError, e:
            self.queue.put(False)
            log.debug(e)
        