#!/usr/bin/env python
import hashlib
import unittest
import time
from client.misc import nicetime
from client import libpms
class NiceTimeCorrectTime(unittest.TestCase):
    #known times
    def setUp(self):
        self.known_times = ( 
            ("10 seconds ago.", time.time() - 10),
            ("1 second ago.", time.time() - 1),
            ("a few moments ago.", time.time()),
            ("2 seconds ago.", time.time() - 2),
            ("3 seconds ago.", time.time() - 3),
            ("10 seconds ago.", time.time() - 10),
            ("1 minute ago.", time.time() - 60),
            ("2 minutes ago.", time.time() - 120),
            ("5 hours ago.", time.time() - 20000)
    )
    
    def test_check_times(self):
        for ntime, gtime in self.known_times:
            self.assertEqual(ntime, nicetime(gtime))
            

class AppEngineTest(unittest.TestCase):
    
    def setUp(self):
        self.conn = libpms.AppEngineConnection()
        self.conn.default_values['name'] = "Daniel"
        self.conn.check_for_session_key("Daniel")
        self.conn.password = hashlib.sha1("FReNZaL18").hexdigest()
    
    def test_msg_check(self):
        response = self.conn._app_engine_request({"time" : "1245147679"}, "/msg/check")
        self.assertEqual(response, "OK")
        
if __name__ == "__main__":
    #testcase = NiceTimeCorrectTime()
    unittest.main()

