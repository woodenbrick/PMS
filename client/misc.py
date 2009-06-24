# misc.py
#
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
import time
import datetime
import logging
from settings import Settings

def new_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(Settings.LOGGING_LEVEL)
    ch = logging.StreamHandler()
    ch.setLevel(Settings.LOGGING_LEVEL)
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch.setFormatter(formatter)
    logger.addHandler(ch)
    filelog = logging.FileHandler(Settings.HOME + "debug.log")
    logger.addHandler(filelog)
    return logger

def nicetime(past_time, fuzzy=False, length=1):
    """Takes a unix timestamp and returns a nicely formatted string
    3 days, 2 hours ago...etc. fuzzy will leave todays times as Today <time>"""

    past_time = time.localtime(past_time)[0:6]
    current_time = time.localtime(time.time())[0:6]
    strings = ["year", "month", "day", "hour", "minute", "second"]

    
    sentence = []
    for i in range(0, len(strings)):
        diff = current_time[i] - past_time[i]
        #generate weeks
        if strings[i] == "day":
            weeks, diff = get_weeks(diff)
            if weeks > 0:
                plural = "" if weeks == 1 else "s"
                sentence.append(str(weeks) + " week" + plural)
        if diff <= 0:
            continue
        plural = "" if diff == 1 else "s"
        sentence.append(str(diff) + " " + strings[i] + plural)
    if len(sentence) > 0:
        return ", ".join(sentence[0:length]) + " ago."
    else:
        return "a few moments ago."

def get_weeks(days):
    weeks = int(days / 7)
    days = days % 7
    return weeks, days
