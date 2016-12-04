# -*- coding: utf-8 -*-
from peewee import *


DB_HISTORY_DATA = SqliteDatabase('btcc.db')


class HistoryDataForDb(Model):
    tid = IntegerField(unique=True)
    timestamp = CharField()
    amount = FloatField()
    type = CharField()
    price = FloatField()

    class Meta:
        database = DB_HISTORY_DATA
