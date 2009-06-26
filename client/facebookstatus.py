from libs import facebook
import webbrowser
import cPickle
import time
import libpms
import Queue
import gtk
from settings import Settings
from misc import new_logger
log = new_logger("facebookstatus.py")

class FaceBookStatus(object):
    
    def __init__(self, parent):
        self.parent = parent
        self.db = self.parent.user_db
        self.queue = Queue.Queue()
        self.api_key = "26d3226223a91268db2a4915cd7e0b69"
        self.secret_key = "d5077b8ef8ca5b1e948ec16ed3fc7e0c"
        self.fb = facebook.Facebook(self.api_key, self.secret_key)
        self.new_session()
        self.permission_offline_access = 0
        self.permission_publish_stream = 0

    def new_session(self, update=False):
        auth_values = self.db.cursor.execute("""select session_key, uid, expiry,
                                                          last_time, offline_access,
                                                          publish_stream from
                                                        facebook where username=?""",
                                                        (Settings.USERNAME,)).fetchone()
        if auth_values is not None and update is False:
            log.debug("Authorised user")
            self.fb.session_key = auth_values[0]
            self.fb.uid = auth_values[1]
            self.fb.session_key_expires = auth_values[2]
            self.last_time = auth_values[3]
            self.permission_offline_access = auth_values[4]
            self.permission_publish_stream = auth_values[5]
            log.debug("sesskey: %s uid: %s expires: %s" % (self.fb.session_key, self.fb.uid,
                                                          self.fb.session_key_expires))
            if not self.permission_offline_access:
                self.add_permission("offline_access")
            if not self.permission_publish_stream:
                self.add_permission("publish_stream")
            return
        elif update is False:
            #lets check the PMS server for a key
            response, tree = self.parent.gae_conn.app_engine_request({}, "/usr/facebook/retrievesessionkey")
            #responses OK NOFBKEY
            if response == "OK":
                self.fb.session_key = tree.find("key").text
                self.fb.uid = tree.find("uid").text
                self.fb.session_key_expires = tree.find("expires").text
                self.last_time = 0
                self.add_to_db()
        else:
            #otherwise, get it direct from facebook
            self.db.cursor.execute("""delete from facebook where username=?""",
                                                        (Settings.USERNAME,))
            self.db.db.commit()
            log.debug("No auth or expired session key")
            self.fb.auth.createToken()
            self.fb.login()
            self.last_time = 0
            message = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                                        gtk.BUTTONS_NONE, "PMS needs authorisation from Facebook in order to access your friends status's. After you are done, click OK.")
            message.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
            resp = message.run()
            message.destroy()
            if resp == gtk.RESPONSE_OK:
                auth_values = self.fb.auth.getSession()
                log.debug(auth_values)
                self.last_time = 0
                self.add_to_db()
                self.parent.gae_conn.app_engine_request(
                    {"uid" : self.fb.uid,
                     "facebook_session_key" : self.fb.session_key,
                     "expires" : self.fb.session_key_expires },
                    "/usr/facebook/addsessionkey")
        self.add_permission("offline_access")
        self.add_permission("publish_stream")
        
                
    def add_to_db(self):
                self.db.cursor.execute("""insert into facebook (username, session_key,
                                                uid, expiry, last_time) values (?, ?, ?, ?, ?)""",
                                                (Settings.USERNAME,
                                                 self.fb.session_key, self.fb.uid,
                                                 self.fb.session_key_expires, self.last_time))
                self.db.db.commit()



    def add_permission(self, ext_perm, _recursive=False):
        """Pass params like offline_access, publish_stream to check if a user has the
        required permissions and request them if not"""
        try:
            permission = self.fb.users.hasAppPermission(ext_perm=ext_perm)
        except facebook.FacebookError:
            self.new_session(True)
            result = self.add_permission(ext_perm)
            return result
        if permission == 1:
            query = """update facebook set %s=%s where username='%s'""" % (ext_perm, 1, Settings.USERNAME)
            print query
            self.db.cursor.execute(query)
            self.db.db.commit()
            if ext_perm == "offline_access":
                self.permission_offline_access = 1
            else:
                self.permission_publish_stream = 1
            return True
        elif _recursive:
            return False
        #request permission
        url = "http://www.facebook.com/authorize.php?api_key=%s&v=1.0&ext_perm=%s" % (self.api_key, ext_perm)
        webbrowser.open(url)
        message = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_INFO,
                                    gtk.BUTTONS_NONE, "PMS needs permission %s from Facebook. After you are done, click OK." % ext_perm)
        message.add_button(gtk.STOCK_OK, gtk.RESPONSE_OK)
        resp = message.run()
        message.destroy()
        #check again, see if it is granted
        self.add_permission(ext_perm, True)
    
            
    def change_status(self, new_status):
        """Returns True if changing status was successful"""
        try:
            result = self.fb.users.setStatus(new_status,
                                             status_includes_verb=True, clear=False)
            return "HIGH FIVE!"
        except facebook.FacebookError:
            return "Permission was not granted"
    
    def get_friends_status(self):
        log.info("Requesting status of Facebook friends")
        query = "SELECT name, profile_url, status, pic_square FROM user WHERE uid in (SELECT uid2 FROM friend WHERE uid1 = "+str(self.fb.uid)+") AND status.message != '' AND status.time > " + str(self.last_time) +" ORDER BY status.time" # LIMIT 1,30"
        fb_conn = libpms.ThreadedFBConnection(self.fb.fql.query, [query], self.queue)
        fb_conn.daemon = True
        fb_conn.start()
        while fb_conn.isAlive():
            gtk.main_iteration()
        return self.queue.get()

        


