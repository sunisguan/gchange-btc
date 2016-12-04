# -*- coding: utf-8 -*-
from peewee import *
import datetime
import time

import btcc_model_db
import common
import btcc_http_client
from btcc_model import HistoryData

db = btcc_model_db.DB_HISTORY_DATA

http_client = btcc_http_client.BtccHttpClient()

def _write_data():
    if not btcc_model_db.HistoryDataForDb.table_exists():
        btcc_model_db.HistoryDataForDb.create_table()
    
    # btcc timestamp = 2011-06-13 13:13:24, id = 1, price = 150, amount = 1, type = buy
    
    while True:
        limit = 5000
        if btcc_model_db.HistoryDataForDb.select().count():
            # 从上次获取地方继续获取
            last_data = btcc_model_db.HistoryDataForDb.select(btcc_model_db.HistoryDataForDb, fn.Max(btcc_model_db.HistoryDataForDb.tid)).get()
            history_datas = http_client.get_history_data(limit=limit, since=last_data.tid, sincetype='id')
        else:
            # 从第一条还是获取
            t = time.mktime(datetime.datetime.strptime('2016-01-01 00:00:00', "%Y-%m-%d %H:%M:%S").timetuple())
            history_datas = http_client.get_history_data(limit=limit, sincetype='time', since=t)
        with db.atomic():  # Opens new transaction.
            try:
                for d in history_datas:
                    data = HistoryData(**d).to_historydata()
                    common.logger.info(d)
                    data.save()
            except Exception as e:
                # Because this block of code is wrapped with "atomic", a
                # new transaction will begin automatically after the call
                # to rollback().
                common.logger.error('db rollback, e = %s' % e)
                db.rollback()
                break
        common.logger.info('get history data len = %s' % len(history_datas))
        if len(history_datas) < limit:
            break


def write():
    try:
        db.connect()
        common.logger.info('[START WRITE HISTORY DATA]')
        _write_data()
        common.logger.info('[WRITE HISTORY DATA COMPLETE]')
    except Exception as e:
        common.logger.error(e)
    finally:
        db.close()


def delete():
    try:
        db.connect()
        common.logger.info('[START DELETE HISTORY DATA]')
        btcc_model_db.HistoryDataForDb.delete().execute()
        common.logger.info('[DELETE HISTORY DATA SUCCESS]')
    except Exception as e:
        common.logger.error(e)
    finally:
        db.close()


def main():
    write()
    #delete()

if __name__ == "__main__":
    main()

