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

errors = {
    "MISSINGVALUES" : "This request is missing some required data",
    "NOUSER" : "No user with that name exists",
    "NOTGROUP" : "This group doesn't exist",
    "USEREXISTS" : "A user with this name already exists",
    "GROUPEXISTS" : "A group with this name already exists",
    "BADAUTH" : "Incorrect session key",
    "BADPASS" : "Incorrect username or password",
    "NONMEMBER" : "User is not a member of this group",
    "HASMEMBERS" : "This group has more than 1 member",
    "ISOWNER" : "Owner cannot leave a group they created",
    "NOTOWNER" : "Your request requires group ownership privledges",
    "OUTDATED" : "The link you have followed is outdated",
    "ERROR" : "", #general error, has its own message
}
    