# -*- coding: utf-8 -*-
from pyalgotrade import broker
from pyalgotrade.broker import backtesting
import common
from btcc_exchange import BtccWebsocketClient


class LiveBroker(broker.Broker):
    QUEUE_TIMEOUT = 0.01

    def __init__(self, exchange):
        super(LiveBroker, self).__init__()
        self.__stop = False
        self.__cash = 0
        self.__shares = {}
        self.__activeOrders = {}
        self.__exchange = exchange

        # 注册监听事件
        self.__exchange.subscribe_event(BtccWebsocketClient.Event.ON_ORDER_BOOK_UPDATE, self.__on_order_book_update)

    def __on_order_book_update(self, order):
        common.logger.info('收到订单状态回调 id = %s' % order.get_id())
        active_order = self.__activeOrders.get(order.get_id())
        if active_order.getState() == broker.Order.State.SUBMITTED:
            active_order.switchState(broker.Order.State.ACCEPTED)

        status = order.get_status()
        if status == common.OrderStatus.CANCELED:
            common.logger.info('__on_order_book_update, CANCELED, %s' % order.get_id())
            active_order.switchState(broker.Order.State.CANCELED)
            self.__unregisterOrder(active_order)
            self.notifyOrderEvent(active_order, broker.OrderEvent.Type.CANCELED, "挂单取消")
        elif status == common.OrderStatus.CLOSED:
            common.logger.info('__on_order_book_update, CLOSED, %s' % order.get_id())
            fee = float(order.get_fee())
            # 获取成交价
            price = float(order.get_avg_price())
            # 获取成交量
            amount = float(order.get_amount_original())
            # 获取交易时间
            datetime_ = order.get_datetime()

            exe_info = broker.OrderExecutionInfo(price, abs(amount), fee, datetime_)
            active_order.addExecutionInfo(exe_info)
            event_type = broker.OrderEvent.Type.FILLED

            if not active_order.isActive():
                self.__unregisterOrder(active_order)
            self.notifyOrderEvent(broker.OrderEvent(active_order, event_type, exe_info))

        elif status == common.OrderStatus.PENDING:
            common.logger.info('__on_order_book_update, PENDING, %s' % order.get_id())
            pass
        elif status == common.OrderStatus.OPEN:
            common.logger.info('__on_order_book_update, OPEN, %s' % order.get_id())
            pass

    def __registerOrder(self, order):
        if order.getId() is not None and order.getId() not in self.__activeOrders:
            self.__activeOrders[order.getId()] = order

    def __unregisterOrder(self, order):
        if order.getId() in self.__activeOrders and order.getId() is not None:
            del self.__activeOrders[order.getId()]

    def __refresh_account_info(self):
        """
        刷新用户账户信息
        :return:
        """
        # 防止获取中发生错误
        self.__stop = True

        # 获取用户现金
        self.__cash = self.__exchange.get_cash()
        common.logger.info("可用现金 = %s" % str(self.__cash))

        # 获取用户可用的BTC
        btc = self.__exchange.get_avaliable_btc()
        if btc:
            self.__shares = {common.CoinSymbol.BTC: btc}
            common.logger.info('可用 BTC = %s' % str(btc))
        else:
            self.__shares = {}

        # 没有错误发生，继续轮询
        self.__stop = False

    def __refresh_open_order(self):
        orders = self.__exchange.get_orders(open_only=True)
        common.logger.info('获取到 %s 个挂单' % len(orders))
        for order in orders:
            if order.is_buy():
                action = broker.Order.Action.BUY
            elif order.is_sell():
                action = broker.Order.Action.SELL
            else:
                raise Exception('不支持的订单类型')

            ret = broker.LimitOrder(action, common.CoinSymbol.BTC, order.get_price(), order.get_amount(), common.BTCTraits())
            ret.setSubmitted(order.get_id(), order.get_datetime())
            ret.setState(broker.Order.State.ACCEPTED)

            self.__registerOrder(ret)

    # BEGIN observer.Subject interface
    def start(self):
        common.logger.info('[BROKER START]')
        super(LiveBroker, self).start()
        self.__refresh_account_info()
        self.__refresh_open_order()

    def stop(self):
        self.__stop = True

    def join(self):
        pass

    def eof(self):
        return self.__stop

    def peekDateTime(self):
        # return None since this is a realtime subject
        return None

    def dispatch(self):
        pass

    # END observer.Subject interface

    # BEGIN broker.Broker interface

    def getCash(self, includeShort=True):
        return self.__cash

    def getInstrumentTraits(self, instrument):
        return common.BTCTraits()

    def getShares(self, instrument):
        return self.__shares.get(instrument, 0)

    def getPositions(self):
        return self.__shares

    def getActiveOrders(self, instrument=None):
        return self.__activeOrders.values()

    def submitOrder(self, order):
        if order.isInitial():
            order.setAllOrNone(True)
            order.setGoodTillCanceled(True)

            if order.isBuy():
                if order.getType() == broker.Order.Type.MARKET:
                    btccOrder = self.__exchange.buy(amount=order.getQuantity())
                elif order.getType() == broker.Order.Type.LIMIT:
                    btccOrder = self.__exchange.buy(amount=order.getQuantity(), price=order.getLimitPrice())
                else:
                    raise Exception('仅支持 市价/限价 交易')
                common.logger.info('买入订单 %s' % btccOrder)
            else:
                if order.getType() == broker.Order.Type.MARKET:
                    btccOrder = self.__exchange.sell(amount=order.getQuantity())
                elif order.getType() == broker.Order.Type.LIMIT:
                    btccOrder = self.__exchange.sell(amount=order.getQuantity(), price=order.getLimitPrice())
                else:
                    raise Exception('仅支持 市价/限价 交易')
                common.logger.info('卖出订单 %s' % btccOrder)

            order.setSubmitted(btccOrder.get_id(), btccOrder.get_datetime())
            self.__registerOrder(order)
            # Switch from INITIAL -> SUBMITTED
            # IMPORTANT: Do not emit an event for this switch because when using the position interface
            # the order is not yet mapped to the position and Position.onOrderUpdated will get called.
            order.switchState(broker.Order.State.SUBMITTED)

            """
            if btccOrder.get_status() == common.OrderStatus.CLOSED:
                order.switchState(broker.Order.State.ACCEPTED)
                self.__on_order_book_update(btccOrder)
            """

        else:
            raise Exception('The order was already processed')

    def createMarketOrder(self, action, instrument, quantity, onClose=False):
        if instrument != common.CoinSymbol.BTC:
            raise Exception('仅支持 BTC 交易')

        if action == broker.Order.Action.BUY_TO_COVER:
            action = broker.Order.Action.BUY
        elif action == broker.Order.Action.SELL_SHORT:
            action = broker.Order.Action.SELL

        if action not in [broker.Order.Action.BUY, broker.Order.Action.SELL]:
            raise Exception('仅支持 买/卖 交易')

        return broker.MarketOrder(action, instrument, quantity, False, common.BTCTraits())

    def createLimitOrder(self, action, instrument, limitPrice, quantity):
        if instrument != common.CoinSymbol.BTC:
            raise Exception('仅支持 BTC 交易')

        if action == broker.Order.Action.BUY_TO_COVER:
            action = broker.Order.Action.BUY
        elif action == broker.Order.Action.SELL_SHORT:
            action = broker.Order.Action.SELL

        if action not in [broker.Order.Action.BUY, broker.Order.Action.SELL]:
            raise Exception('仅支持 买/卖 交易')

        limitPrice = round(limitPrice, 2)
        return broker.LimitOrder(action, instrument, limitPrice, quantity, common.BTCTraits())

    def createStopOrder(self, action, instrument, stopPrice, quantity):
        raise Exception('Stop orders are not supported')

    def createStopLimitOrder(self, action, instrument, stopPrice, limitPrice, quantity):
        raise Exception('Stop limit orders are not supported')

    def cancelOrder(self, order):
        __id = order.getId()
        activeOrder = self.__activeOrders.get(__id)
        if activeOrder is None:
            raise Exception('The order is not active anymore')
        if activeOrder.isFilled():
            raise Exception('Can not cancel order that has already been filled')

        ret = self.__exchange.cancel(order_id=__id)
        closed_order = self.__exchange.get_order(order_id=__id)
        self.__on_order_book_update(closed_order)
        self.__refresh_account_info()

    # END broker.Broker interface

class BacktestingBroker(backtesting.Broker):
    # 最小交易金额
    MIN_TRADE_CNY = 1

    """
    btcc backtesting broker

    :param cash: 初始化资金
    :param barFeed: 数据源

    """
    def __init__(self, cash, barFeed):
        super(BacktestingBroker, self).__init__(cash, barFeed, backtesting.NoCommission())

    def getInstrumentTraits(self, instrument):
        return common.BTCTraits()

    def submitOrder(self, order):
        if order.isInitial():
            order.setAllOrNone(False)
            order.setGoodTillCanceled(True)
        return super(BacktestingBroker, self).submitOrder(order)

    def createMarketOrder(self, action, instrument, quantity, onClose=False):
        # TODO: 创建市价订单
        pass

    def createLimitOrder(self, action, instrument, limitPrice, quantity):
        if instrument not in [common.CoinSymbol.BTC, common.CoinSymbol.LTC]:
            raise Exception('只支持 BTC/LTC交易')

        if action == broker.Order.Action.BUY_TO_COVER:
            action = broker.Order.Action.BUY
        elif action == broker.Order.Action.SELL_SHORT:
            action = broker.Order.Action.SELL

        if limitPrice * quantity < BacktestingBroker.MIN_TRADE_CNY:
            raise Exception('交易必须 >= %s' % BacktestingBroker.MIN_TRADE_CNY)

        if action == broker.Order.Action.BUY:
            # 检查是否有足够的现金
            fee = self.getCommission().calculate(None, limitPrice, quantity)
            cashRequired = limitPrice * quantity + fee
            if cashRequired > self.getCash(False):
                raise Exception('没有足够现金进行交易')
        elif action == broker.Order.Action.SELL:
            # 检查是否有足够的币
            if quantity > self.getShares(common.CoinSymbol.BTC):
                raise Exception('没有足够的 %s 进行交易' % common.CoinSymbol.BTC)
        else:
            raise Exception('仅支持 买/卖 交易')

        return super(BacktestingBroker, self).createLimitOrder(action, instrument, limitPrice, quantity)

    def createStopOrder(self, action, instrument, stopPrice, quantity):
        raise Exception('不支持止损订单')

    def createStopLimitOrder(self, action, instrument, stopPrice, limitPrice, quantity):
        raise Exception('不支持限价止损订单')
