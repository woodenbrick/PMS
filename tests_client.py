#!/usr/bin/env python
import hashlib
import unittest
import time
from client.misc import nicetime
from client import libpms
from client import ircclient
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
            


class IRCNickTest(unittest.TestCase):
    def setUp(self):
        self.known_nicks = (
            ("Daniel", "pms_Daniel!n=pms_Dani@79-100-88-231.btc-net.bg"),
            ("hamish", "pms_hamish!n=pms_Dani@79-100-88-231.btc-net.bg"),
            ("some_one", "pms_some_one!n=pms_Dani@79-100-88-231.btc-net.bg"),
            ("Dangus", "pms_Dangus")
        )
        
    def test_irc_to_pms(self):
        for pms, irc in self.known_nicks:
            self.assertEqual(ircclient.convert_irc_name_to_pms(irc), pms)

if __name__ == "__main__":
    #testcase = NiceTimeCorrectTime()
    unittest.main()

