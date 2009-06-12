import facebook
import webbrowser
import cPickle
import time
import logger
import libpms
import Queue
import gtk
log = logger.new_logger("facebookstatus.py")

class FaceBookStatus(object):
    def __init__(self, parent):
        self.parent = parent
        self.db = self.parent.login.db
        self.queue = Queue.Queue()
        self.program_details = parent.PROGRAM_DETAILS
        self.api_key = "26d3226223a91268db2a4915cd7e0b69"
        self.secret_key = open(self.program_details['home'] + "facebook_secret", "r").readline().strip()
        self.fb = facebook.Facebook(self.api_key, self.secret_key)
        self.new_session()
        #self.add_permission("offline_access")
        #self.add_permission("publish_stream")

    def new_session(self, update=False):
        auth_values = self.db.cursor.execute("""select session_key, uid, expiry,
                                                          last_time from
                                                        facebook where username=?""",
                                                        (self.parent.login.username,)).fetchone()
        log.info(auth_values)
        if auth_values is not None and update is False:
            log.debug("Authorised user")
            self.fb.session_key = auth_values[0]
            self.fb.uid = auth_values[1]
            self.fb.session_key_expires = auth_values[2]
            self.last_time = auth_values[3]
            log.info("sesskey: %s uid: %s expires: %s" % (self.fb.session_key, self.fb.uid,
                                                          self.fb.session_key_expires))
        else:
            self.db.cursor.execute("""delete from facebook where username=?""",
                                                        (self.parent.login.username,))
            self.db.db.commit()
            log.debug("No auth or expired session key")
            self.fb.auth.createToken()
            self.fb.login()
            self.last_time = 0
            raw_input("Allow the app access in your browser then press any key to continue")
            auth_values = self.fb.auth.getSession()
            log.info(auth_values)
            self.db.cursor.execute("""insert into facebook (username, session_key,
                                                uid, expiry, last_time) values (?, ?, ?, ?, ?)""",
                                                (self.parent.login.username,
                                                 auth_values['session_key'], auth_values['uid'],
                                                 self.fb.session_key_expires, 0))
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
            return True
        elif _recursive:
            return False
        #request permission
        url = "http://www.facebook.com/authorize.php?api_key=%s&v=1.0&ext_perm=%s" % (self.api_key, ext_perm)
        webbrowser.open_new_tab(url)
        raw_input("You must grant xompzz additional permissions to edit your status stream. Press enter when done")
        #check again, see if it is granted
        self.add_permission(ext_perm, True)
    
            
    def change_status(self, new_status):
        """Returns True if changing status was successful"""
        try:
            result = self.fb.users.setStatus(new_status, clear=False)
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

        


