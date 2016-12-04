# -*- coding: utf-8 -*-
import unittest
from ..btcc.btcc_http_client import BtccHttpClient
from .btcc_exchange import BtccExchange, BtccWebsocketClient
import btcc_model as bm
import common
import btcc_model_db
from peewee import *
import utils

class BtccTestCase(unittest.TestCase):

    def testWebSocket(self):
        btcc = BtccExchange(duration=10)
        btcc.start_websocket_client()

    def socket_handler(self, *args):
        """
        测试 exchange 的订阅回调
        :return:
        """
        common.logger.debug('receive socket data, args = %s' % args[0])

    def testBtccExchange(self):
        btcc = BtccExchange(duration=10)
        btcc.start_websocket_client()
        btcc.subscribe_event(BtccWebsocketClient.Event.ON_TICKER, self.socket_handler)


    def testAccountInfo(self):
        btcc = BtccHttpClient()

        btcc.get_account_info()
        btcc.get_account_info(BtccHttpClient.AccountParams.Balance)
        btcc.get_account_info(BtccHttpClient.AccountParams.Frozen)
        btcc.get_account_info(BtccHttpClient.AccountParams.Profile)
        btcc.get_account_info(BtccHttpClient.AccountParams.Loan)

    def testTicker(self):
        btcc = BtccHttpClient()
        bm.Ticker(**btcc.get_ticker()['ticker'])

    def testUtils(self):
        time2stamp = utils.time_to_stamp('2016-01-01 00:00:00')
        stamp2time = utils.stamp_to_time(1480847339)
        common.logger.debug(time2stamp)
        common.logger.debug(stamp2time)

    def testDB(self):
        common.logger.debug(btcc_model_db.DB_HISTORY_DATA_FILE)






