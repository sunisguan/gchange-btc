# -*- coding: utf-8 -*-
from pyalgotrade import barfeed
from pyalgotrade import bar
import common
import datetime
from btcc_exchange import BtccWebsocketClient
from btcc_bar import TickerBar, HistoryTradeBar
from peewee import *
from btcc_model import HistoryData


class LiveTickFeed(barfeed.BaseBarFeed):
    """
    A real-time BarFeed that builds bars from live trades
    """

    def __init__(self, exchange, maxLen=None):
        super(LiveTickFeed, self).__init__(bar.Frequency.TRADE, maxLen)
        self.__barDicts = []
        self.registerInstrument(common.CoinSymbol.BTC)
        self.__prevTradeDateTime = None
        self.__stopped = False
        self.__exchange = exchange
        # 注册监听事件
        self.__exchange.subscribe_event(BtccWebsocketClient.Event.ON_CONNECTED, self.__on_connected)
        self.__exchange.subscribe_event(BtccWebsocketClient.Event.ON_DISCONNECTED, self.__on_disconnected)
        self.__exchange.subscribe_event(BtccWebsocketClient.Event.ON_TICKER, self.__on_ticker)

        self.__exchange.start_websocket_client()

    def get_exchange(self):
        return self.__exchange

    def __initializeClient(self):
        return self.__exchange.start_websocket_client()

    def subscribe_ticker_event(self, handler):
        self.__exchange.subscribe_event(BtccWebsocketClient.Event.ON_TICKER, handler)

    def subscribe_disconnected_event(self, handler):
        self.__exchange.subscribe_event(BtccWebsocketClient.Event.ON_DISCONNECTED, handler)

    # 实现 web socket handler
    def __on_ticker(self, ticker):
        common.logger.debug('__on_ticker')
        barDict = {common.CoinSymbol.BTC: TickerBar(self.__get_ticker_datetime(ticker), ticker)}
        self.__barDicts.append(barDict)

    def __on_connected(self):
        common.logger.debug('__on_connected')

    def __on_disconnected(self):
        common.logger.debug('__on_disconected')

    def __get_ticker_datetime(self, tickr):
        ret = tickr.get_datetime()
        if ret == self.__prevTradeDateTime:
            ret += datetime.timedelta(microseconds=1)
        self.__prevTradeDateTime = ret
        return ret

    # 开始 override
    def getCurrentDateTime(self):
        return datetime.datetime.now()

    def barsHaveAdjClose(self):
        return False

    def getNextBars(self):
        ret = None
        if len(self.__barDicts):
            ret = bar.Bars(self.__barDicts.pop(0))
        return ret

    def peekDateTime(self):
        """
        Return None since this is a realtime subject
        :return: None
        """
        return None

    # This may raise
    def start(self):
        super(LiveTickFeed, self).start()

    # This should not raise
    def stop(self):
        if self.__exchange.stop_websocket_client():
            self.__stopped = True

    def join(self):
        self.__exchange.join_websocket_client()

    def eof(self):
        return self.__stopped

    # 结束 override


class BacktestHistoryFeed(barfeed.BaseBarFeed):
    def __init__(self, maxLen=None):
        super(BacktestHistoryFeed, self).__init__(bar.Frequency.TRADE, maxLen)
        self.__barDicts = []
        self.registerInstrument(common.CoinSymbol.BTC)
        self.__prevTradeDateTime = None
        self.__stopped = False
        self.__last_tid = -1

        self.__month = 1
        self.__limit = 1000000

        self.__microsecond_add = 1

        self.db_select()

    def __get_trade_datetime(self, trade):
        ret = trade.get_date()
        ret += datetime.timedelta(microseconds=self.__microsecond_add)
        self.__microsecond_add += 1
        if self.__microsecond_add >= 100000:
            self.__microsecond_add = 1
        return ret

    def db_select(self, tid=None):
        if self.__month not in range(1, 13):
            return
        db_file = '/Users/Sun/Documents/btcc-db/btcc_{}.db'.format(self.__month)
        db = SqliteDatabase(db_file)
        ret = []

        if tid is not None:
            sql = 'SELECT tid, timestamp, price, amount, type FROM historydatafordb WHERE tid > {} ORDER BY tid LIMIT {}'.format(self.__last_tid, self.__limit)
        else:
            sql = 'SELECT tid, timestamp, price, amount, type FROM historydatafordb ORDER BY tid LIMIT {}'.format(self.__limit)

        common.logger.info('正在查询 DB 文件 %s' % db_file)
        common.logger.info('SQL = %s' % sql)

        try:
            #cursor = db.execute_sql(sql=sql, params=(tid, self.__limit) if tid is not None else (self.__limit))
            cursor = db.execute_sql(sql=sql)
            data = cursor.fetchall()
            if len(data) == 0 or len(data) < self.__limit:
                self.__month += 1
            for i, d in enumerate(data):
                if i == len(data) - 1:
                    self.__last_tid = d[0]
                trade = HistoryData(d[0], d[1], d[2], d[3], d[4])
                barDict = {common.CoinSymbol.BTC: HistoryTradeBar(self.__get_trade_datetime(trade), trade)}
                self.__barDicts.append(barDict)
        except Exception as e:
            common.logger.error(e)
        finally:
            db.close()

    # 开始 override
    def getCurrentDateTime(self):
        return datetime.datetime.now()

    def barsHaveAdjClose(self):
        return False

    def getNextBars(self):
        ret = None
        if len(self.__barDicts):
            ret = bar.Bars(self.__barDicts.pop(0))
            if len(self.__barDicts) < 1000:
                self.db_select(tid=self.__last_tid)
        return ret

    def peekDateTime(self):
        """
        Return None since this is a realtime subject
        :return: None
        """
        return None

    # This may raise
    def start(self):
        super(BacktestHistoryFeed, self).start()

    # This should not raise
    def stop(self):
        self.__stopped = True

    def join(self):
        pass

    def eof(self):
        return self.__stopped

    # 结束 override


