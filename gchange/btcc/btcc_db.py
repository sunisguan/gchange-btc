# -*- coding: utf-8 -*-
from peewee import *


class DBHelper(object):
    def select(self):
        db = SqliteDatabase('/Users/Sun/Documents/btcc-db/btcc_tmp.db')
        db.execute_sql(sql='SELECT * FROM ? WHERE tid > ? LIMIT ? ORDER BY tid' , params=(table))
