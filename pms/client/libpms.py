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
import logger
log = logger.new_logger("LIBPMS")

from poster.encode import multipart_encode
from poster.streaminghttp import register_openers


class AppEngineConnection(object):
    def __init__(self, server):
        self.url = server
        self.default_values = {}
        
    def check_xml_response(self, doc):
        """Check if our request was valid"""
        self.xtree = ET.parse(doc)
        self.iter = self.xtree.getiterator()
        status = self.iter[0].attrib['status']
        log.info("Request status: %s" % status)
        if status != "OK":
            self.error = self.iter[0].text
            log.error(self.error)
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
            log.info("GET request: %s" % mapping)
            try:
                request = urllib2.urlopen(self.url + mapping)
            except urllib2.URLError, e:
                log.error(e)
                self.error = str(e)
                return "URLError"
            return self.check_xml_response(request)
        if auto_now:
            data['time'] = time.time()
        data.update(self.default_values)
        encoded_values = urllib.urlencode(data)
        log.info("POST request: %s" % mapping)
        log.debug("POST DATA %s" % data)
        try:
            request = urllib2.urlopen(self.url + mapping, encoded_values)
        except urllib2.URLError, e:
            log.error(e)
            self.error = str(e)
            return "URLError"
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
