# -*- coding: utf-8 -*-
import time
import datetime

def time_to_stamp(datetime_, format_type='%Y-%m-%d %H:%M:%S'):
    d = datetime.datetime.strptime(datetime_, format_type)
    t = d.timetuple()
    return int(time.mktime(t))


def stamp_to_time(stamp, format_type='%Y-%m-%d %H:%M:%S'):
    stamp = float(stamp)
    d = datetime.datetime.fromtimestamp(stamp)
    return d.strftime(format_type)