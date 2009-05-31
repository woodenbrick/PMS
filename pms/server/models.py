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

from google.appengine.ext import db

class User(db.Model):
    name = db.StringProperty()
    password = db.StringProperty()
    salt = db.StringProperty()
    email = db.EmailProperty()
    timezone = db.StringProperty()

class UserAvatar(db.Model):
    user = db.ReferenceProperty(User)
    avatar = db.BlobProperty()
    upload_time = db.FloatProperty()
    
class Session(db.Model):
    user = db.ReferenceProperty(User)
    session_key = db.StringProperty()
    ip = db.StringProperty()
    expires = db.IntegerProperty()

class Group(db.Model):
    name = db.StringProperty(required=True)
    owner = db.ReferenceProperty(User)
    description = db.StringProperty()
    password_required = db.BooleanProperty()
    password = db.StringProperty()
    salt = db.StringProperty()
    
class Message(db.Model):
    group = db.ReferenceProperty(Group)
    user = db.ReferenceProperty(User)
    comment = db.TextProperty()
    date = db.FloatProperty()
    
class GroupMember(db.Model):
    group = db.ReferenceProperty(Group)
    user = db.ReferenceProperty(User)

class TempPassword(db.Model):
    user = db.ReferenceProperty(User)
    temp_pass = db.StringProperty()
    activation_link = db.StringProperty()
    time = db.FloatProperty()

#class Event(db.Model):
#    name = db.StringProperty()
#    group = db.ReferenceProperty(Group)
#    creator = db.ReferenceProperty(User)
#    date = db.DateTimeProperty()
#    status = db.StringProperty(choices=set(['Confirmed', 'Unconfirmed', 'Rejected']))
#
#class EventVotes(db.Model):
#    event = db.ReferenceProperty(Event)
#    user = db.ReferenceProperty(User)
#    vote = db.StringProperty(choices=set(['Yes', 'No', 'None']))