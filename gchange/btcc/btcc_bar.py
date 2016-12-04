# -*- coding: utf-8 -*-
from pyalgotrade import bar
import common


class TickerBar(bar.Bar):
    def __init__(self, datetime_, ticker):
        self.__datetime = datetime_
        self.__ticker = ticker

    def setUseAdjustedValue(self, useAdjusted):
        pass

    def getUseAdjValue(self):
        return False

    def getDateTime(self):
        return self.__datetime

    def getOpen(self, adjusted=False):
        #return self.__ticker.get_open()
        return self.getPrice()

    def getHigh(self, adjusted=False):
        #return self.__ticker.get_high()
        return self.getPrice()

    def getLow(self, adjusted=False):
        #return self.__ticker.get_low()
        return self.getPrice()

    def getClose(self, adjusted=False):
        #return self.__ticker.get_close()
        return self.getPrice()

    def getVolume(self):
        return self.__ticker.get_volume()

    def getAdjClose(self):
        return self.getClose()

    def getFrequency(self):
        return bar.Frequency.SECOND

    def getPrice(self):
        return self.__ticker.get_last()

    def getExtraColumns(self):
        return {
            common.OrderType.ASK: self.__ticker.get_ask(),
            common.OrderType.BID: self.__ticker.get_bid()
        }

class HistoryTradeBar(bar.Bars):
    def __init__(self, datetime_, trade):
        self.__datetime = datetime_
        self.__trade = trade

    def setUseAdjustedValue(self, useAdjusted):
        pass

    def getUseAdjValue(self):
        return False

    def getDateTime(self):
        return self.__datetime

    def getOpen(self, adjusted=False):
        #return self.__ticker.get_open()
        return self.getPrice()

    def getHigh(self, adjusted=False):
        #return self.__ticker.get_high()
        return self.getPrice()

    def getLow(self, adjusted=False):
        #return self.__ticker.get_low()
        return self.getPrice()

    def getClose(self, adjusted=False):
        #return self.__ticker.get_close()
        return self.getPrice()

    def getVolume(self):
        return self.__trade.get_amount()

    def getAdjClose(self):
        return self.getClose()

    def getFrequency(self):
        return bar.Frequency.TRADE

    def getPrice(self):
        return self.__trade.get_price()

    def getExtraColumns(self):
        return {
            'type': common.OrderType.ASK if self.__trade.get_type() == 'sell' else common.OrderType.BID
        }