# -*- coding: utf-8 -*-
from peewee import *
import datetime
import time

import btcc_model_db
import common
import btcc_http_client
from btcc_model import HistoryData

import utils


http_client = btcc_http_client.BtccHttpClient()

start_end = [
    ('2016-01-01 00:00:00', '2016-01-31 23:59:59'),
    ('2016-02-01 00:00:00', '2016-02-29 23:59:59'),
    ('2016-03-01 00:00:00', '2016-03-31 23:59:59'),
    ('2016-04-01 00:00:00', '2016-04-30 23:59:59'),
    ('2016-05-01 00:00:00', '2016-05-31 23:59:59'),
    ('2016-06-01 00:00:00', '2016-06-30 23:59:59'),
    ('2016-07-01 00:00:00', '2016-07-31 23:59:59'),
    ('2016-08-01 00:00:00', '2016-08-31 23:59:59'),
    ('2016-09-01 00:00:00', '2016-09-30 23:59:59'),
    ('2016-10-01 00:00:00', '2016-10-31 23:59:59'),
    ('2016-11-01 00:00:00', '2016-11-30 23:59:59'),
    ('2016-12-01 00:00:00', '2016-12-31 23:59:59'),
]

db = SqliteDatabase('/Users/Sun/Documents/btcc-db/btcc_tmp.db')

def _write_data():

    if 'historydatafordb' not in db.get_tables():
        db.create_table(btcc_model_db.HistoryDataForDb)
    
    # btcc timestamp = 2011-06-13 13:13:24, id = 1, price = 150, amount = 1, type = buy

    while True:
        limit = 5000
        try:
            cursor = db.execute_sql(sql='SELECT MAX(tid) FROM historydatafordb')
            data = cursor.fetchall()
            if len(data) != 0 and data[0][0] is not None:
                # 从上次获取地方继续获取
                history_datas = http_client.get_history_data(limit=limit, sincetype='id', since=data[0][0])
            else:
                history_datas = http_client.get_history_data(limit=limit, sincetype='time', since=utils.time_to_stamp(start_end[2][0]))
            with db.atomic():  # Opens new transaction.
                try:
                    for d in history_datas:
                        db.execute_sql(
                            sql='INSERT INTO historydatafordb(tid, timestamp, amount, type, price) VALUES(?,?,?,?,?)',
                            params=(d['tid'], d['date'], d['amount'], d['type'], d['price']))
                        common.logger.info(d)
                except Exception as e:
                    # Because this block of code is wrapped with "atomic", a
                    # new transaction will begin automatically after the call
                    # to rollback().
                    common.logger.error('db rollback, e = %s' % e)
                    db.rollback()
                    db.close()
                    break
            common.logger.info('获取到历史数据 %s 条，最后时间 %s' % (len(history_datas), utils.stamp_to_time(history_datas[-1]['date'])))
            if len(history_datas) < limit:
                break
        except Exception as e:
            common.logger.error(e)
        finally:
            db.close()


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


def delete(month=None):
    db = None
    try:
        if month is None:
            db_file = btcc_model_db.DB_HISTORY_DATA_FILE
        else:
            db_file = [btcc_model_db.DB_HISTORY_DATA_FILE[month]]

        for f in db_file:
            db = SqliteDatabase(f)
            db.connect()
            common.logger.info('[START DELETE HISTORY DATA]')
            db.drop_table(btcc_model_db.HistoryDataForDb)
            common.logger.info('[DELETE HISTORY DATA SUCCESS]')
    except Exception as e:
        common.logger.error(e)
    finally:
        if db is not None:
            db.close()

def separation():
    large_db = SqliteDatabase('/Users/Sun/Documents/btcc-db/btcc.db')

    db = None

    try:
        for i, db_file in enumerate(btcc_model_db.DB_HISTORY_DATA_FILE):
            # 当前月的DB
            db = SqliteDatabase(db_file)
            if 'historydatafordb' not in db.get_tables():
                db.create_table(btcc_model_db.HistoryDataForDb)

            start_timestamp = utils.time_to_stamp(start_end[i][0])
            end_timestamp = utils.time_to_stamp(start_end[i][1])
            cursor = large_db.execute_sql(sql='SELECT tid, timestamp, amount, type, price FROM historydatafordb '
                                          'WHERE timestamp >= ? and timestamp <= ? ORDER BY timestamp', params=(start_timestamp, end_timestamp))
            data = cursor.fetchall()

            with db.atomic():  # Opens new transaction.
                try:
                    for d in data:
                        db.execute_sql(sql='INSERT INTO historydatafordb(tid, timestamp, amount, type, price) VALUES(?,?,?,?,?)', params=(d[0], d[1], d[2], d[3], d[4]))
                except Exception as e:
                    # Because this block of code is wrapped with "atomic", a
                    # new transaction will begin automatically after the call
                    # to rollback().
                    common.logger.error('db rollback, e = %s' % e)
                    db.rollback()
                    break
            common.logger.info('%s月数据已插入完成，共 %s 条' % (i+1, len(data)))
    except Exception as e:
        common.logger.error(e)
    finally:
        if db is not None:
            db.close()
        large_db.close()


def main():
    write()
    #delete(3)
    #separation()

if __name__ == "__main__":
    main()

