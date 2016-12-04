# -*- coding: utf-8 -*-
from peewee import *


DB_HISTORY_DATA_PATH = '/Users/Sun/Documents/btcc-db/btcc_{}.db'
DB_HISTORY_DATA_FILE = [
    DB_HISTORY_DATA_PATH.format(i) for i in range(1, 12)
]


class HistoryDataForDb(Model):
    tid = IntegerField(unique=True)
    timestamp = CharField()
    amount = FloatField()
    type = CharField()
    price = FloatField()

    #class Meta:
        #database = DB_HISTORY_DATA
