## Importing modules

import MetaTrader5 as mt5
from datetime import datetime
from time import sleep
import pandas as pd
import numpy as np
from itertools import product
from statistics import mode
import time
from opt_function import optimize

## Get Moving Averages, RSI, Close and SD

def get_close_sd(SYMBOL, TIMEFRAME, RSI_PERIOD):
    df = pd.DataFrame(mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, RSI_PERIOD))
    last_close = df['close'].iloc[-1]
    sd = pd.DataFrame(mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, RSI_PERIOD))['close'].std()
    
    return last_close, sd

def get_ma(SYMBOL, TIMEFRAME, LONG_MA_PERIOD):
    df = pd.DataFrame(mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, LONG_MA_PERIOD))
    df['ma_21'] = df['close'].rolling(21).mean()
    ma_21 = df['ma_21'].iloc[-1]
    df['ma_50'] = df['close'].rolling(50).mean()
    ma_50 = df['ma_50'].iloc[-1]
    df['ma_100'] = df['close'].mean()
    ma_100 = df['ma_100'].iloc[-1]

    return ma_21, ma_50, ma_100

def get_rsi(SYMBOL, TIMEFRAME, LONG_MA_PERIOD):
    bars = mt5.copy_rates_from_pos(SYMBOL, TIMEFRAME, 1, LONG_MA_PERIOD)
    bars_df = pd.DataFrame(bars)

    bars_df['gain'] = (bars_df['close'] - bars_df['open']).apply(lambda x: x if x > 0 else 0)
    bars_df['loss'] = (bars_df['close'] - bars_df['open']).apply(lambda x: -x if x < 0 else 0)

    bars_df['ema_gain'] = bars_df['gain'].ewm(span=14, min_periods=14).mean()
    bars_df['ema_loss'] = bars_df['loss'].ewm(span=14, min_periods=14).mean()

    bars_df['rs'] = bars_df['ema_gain'] / bars_df['ema_loss']

    bars_df['rsi_14'] = 100 - (100 / (bars_df['rs'] + 1))

    ## Moving Average 10 of the RSI 

    bars_df['ma_rsi_14'] = bars_df['rsi_14'].rolling(10).mean()

    rsi_14 = bars_df['rsi_14'].iloc[-1]
    
    ma_rsi_14 = bars_df['ma_rsi_14'].iloc[-1]

    return rsi_14, ma_rsi_14

## Function to send a market order

def market_order(SYMBOL, VOLUME, order_type, stoploss, takeprofit, deviation=20, magic=12345):

    order_type_dict = {
        'buy': mt5.ORDER_TYPE_BUY,
        'sell': mt5.ORDER_TYPE_SELL
    }

    price_dict = {
        'buy': mt5.symbol_info_tick(SYMBOL).ask,
        'sell': mt5.symbol_info_tick(SYMBOL).bid
    }

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": SYMBOL,
        "volume": VOLUME,  # FLOAT
        "type": order_type_dict[order_type],
        "price": price_dict[order_type],
        "sl": stoploss,  # FLOAT
        "tp": takeprofit,  # FLOAT
        "deviation": deviation,  # INTERGER
        "magic": magic,  # INTERGER
        "comment": 'scalp_open',
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    order_result = mt5.order_send(request)
    return(order_result)

## Function to close an order based on ticket id

def close_position(position, deviation=20, magic=12345):

    order_type_dict = {
        0: mt5.ORDER_TYPE_SELL,
        1: mt5.ORDER_TYPE_BUY
    }

    price_dict = {
        0: mt5.symbol_info_tick(SYMBOL).bid,
        1: mt5.symbol_info_tick(SYMBOL).ask
    }

    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "position": position['ticket'],  # select the position you want to close
        "symbol": SYMBOL,
        "volume": VOLUME,  # FLOAT
        "type": order_type_dict[position['type']],
        "price": price_dict[position['type']],
        "deviation": deviation,  # INTERGER
        "magic": magic,  # INTERGER
        "comment": 'scalp_close',
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": mt5.ORDER_FILLING_IOC,
    }

    order_result = mt5.order_send(request)
    return(order_result)

def close_positions(order_type):
    order_type_dict = {
        'buy': 0,
        'sell': 1
    }

    if mt5.positions_total() > 0:
        positions = mt5.positions_get()

        positions_df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())

        if order_type != 'all':
            positions_df = positions_df[(positions_df['type'] == order_type_dict[order_type])]

        for i, position in positions_df.iterrows():
            order_result = close_position(position)

            print('order_result: ', order_result)

def check_allowed_trading_hours():
    if 9 < datetime.now().hour < 17:
        return True
    else:
        return False

## Function to get the exposure of a symbol

def get_exposure(symbol):
    positions = mt5.positions_get(symbol=symbol)
    if positions:
        pos_df = pd.DataFrame(positions, columns=positions[0]._asdict().keys())
        exposure = pos_df['volume'].sum()

        return exposure


## Run strategy 

if __name__ == '__main__':
    
    # strategy parameters
    SYMBOL = "[NQ100]"
    VOLUME = 3.0
    TIMEFRAME = mt5.TIMEFRAME_M5
    LONG_MA_PERIOD = 100
    RSI_PERIOD = 14

    initialized = mt5.initialize()

    if initialized:
        print('Connected to MetaTrader5')
        print('Login: ', mt5.account_info().login)
        print('Server: ', mt5.account_info().server)

    while True:

        ## Initial values for sl, tp

        SL_SD_BUY = 3
        TP_SD_BUY = 2
        SL_SD_SELL = 3
        TP_SD_SELL = 2

        # calculating account exposure
        exposure = get_exposure(SYMBOL)

        num_positions = mt5.positions_total()

        #if not check_allowed_trading_hours():  ## Set up if you want to trade during specific hours
        #    close_positions('all')

        ma_21, ma_50, ma_100 = get_ma(SYMBOL, TIMEFRAME, LONG_MA_PERIOD)
        rsi_14, ma_rsi_14 = get_rsi(SYMBOL, TIMEFRAME, LONG_MA_PERIOD)
        close, sd = get_close_sd(SYMBOL, TIMEFRAME, RSI_PERIOD)

        direction = 'flat'

        if close > ma_21 and close > ma_50 and close > ma_100: ## and check_allowed_trading_hours():
            if rsi_14 > ma_rsi_14:
                direction = 'buy'
                close_positions('sell')

                if num_positions == 0:
                    tick = mt5.symbol_info(SYMBOL)
                    order_result = market_order(SYMBOL, VOLUME, 'buy', tick.bid - SL_SD_BUY * sd, tick.bid + TP_SD_BUY * sd)
                    print(order_result)

        elif close < ma_21 and close < ma_50 and close < ma_100: ## and check_allowed_trading_hours():
            if rsi_14 < ma_rsi_14:
                close_positions('buy')
                direction = 'sell'
                
                if num_positions == 0:
                    tick = mt5.symbol_info(SYMBOL)
                    order_result = market_order(SYMBOL, VOLUME, 'sell', tick.bid + SL_SD_SELL * sd, tick.bid - TP_SD_SELL * sd)
                    print(order_result)

        today_date = datetime.today()

        deal_history = mt5.history_deals_get(datetime(today_date.year, today_date.month, today_date.day), datetime.now())

        if len(deal_history) in range(5, 100, 5):
            date_first = deal_history[-5][1]
            date_first_formated = pd.to_datetime(date_first, unit='s')
            hour_first = date_first_formated.hour
            day_first = date_first_formated.day
            month_first = date_first_formated.month
            year_first = date_first_formated.year
            date_last = deal_history[-1][1]
            date_last_formated = pd.to_datetime(date_last, unit='s')
            hour_last = date_last_formated.hour
            day_last = date_last_formated.day
            month_last = date_last_formated.month
            year_last = date_last_formated.year

            ## Optimize past five trades

            best_sl_buy, best_tp_buy, best_sl_sell, best_tp_sell, best_profit = optimize(SYMBOL, TIMEFRAME, year_first, year_last, 
                                                                month_first, month_last, day_first, day_last, hour_first, hour_last)

            ## Assign best values to sl and tp

            SL_SD_BUY = best_sl_buy
            TP_SD_BUY = best_tp_buy
            SL_SD_SELL = best_sl_sell
            TP_SD_SELL = best_tp_sell

            print('best possible profits 5 past trades :', best_profit)

        else:
            SL_SD_BUY = SL_SD_BUY
            TP_SD_BUY = TP_SD_BUY
            SL_SD_SELL = SL_SD_SELL
            TP_SD_SELL = TP_SD_SELL

        print('time: ', datetime.now())
        print('exposure: ', exposure)
        print('last_close: ', close)
        print('ma_21: ', ma_21)
        print('ma_50: ', ma_50)
        print('ma_100: ', ma_100)
        print('rsi_14: ', rsi_14)
        print('ma_rsi_14: ', ma_rsi_14)
        print('signal: ', direction)
        print('Best value for sl_buy: ', SL_SD_BUY)
        print('Best value for tp_buy: ', TP_SD_BUY)
        print('Best value for sl_sell: ', SL_SD_SELL)
        print('Best value for tp_sell: ', TP_SD_SELL)
        print('-------\n')

        # update every 1 second
        time.sleep(1)
