import MetaTrader5 as mt5
from datetime import datetime
import pandas as pd
import numpy as np
import random as rd
from itertools import product
from statistics import mode
from datetime import datetime


def find_signal(close, ma_10, ma_20, ma_100, rsi_14, ma_rsi_14, fdi):
    if close > ma_10 and close > ma_20 and close > ma_100:
        if rsi_14 > ma_rsi_14 and fdi < 1.5 :
            return 'buy'
        elif rsi_14 > ma_rsi_14 and fdi >=1.5 :
            alea = rd.random()
            if alea > 0.5 :
                return 'buy'
        else:
            return None
    elif close < ma_10 and close < ma_20 and close < ma_100:
        if rsi_14 < ma_rsi_14:
            return 'sell'
        else:
            return None

def optimize(SYMBOL, TIMEFRAME, YEAR_FIRST, YEAR_LAST, MONTH_FIRST, MONTH_LAST, DAY_FIRST, DAY_LAST, HOUR_FIRST,
             HOUR_LAST):
    
    bars = mt5.copy_rates_range(SYMBOL, TIMEFRAME, datetime(YEAR_FIRST, MONTH_FIRST, DAY_FIRST, HOUR_FIRST+2), 
                                        datetime(YEAR_LAST, MONTH_LAST, DAY_LAST, HOUR_LAST+2))

    df_m5 = pd.DataFrame(bars)

    print(type(df_m5))

    ## Different Moving Averages on the M5 : 21, 50, 100
     
    df_m5['ma_21'] = df_m5['close'].rolling(21).mean()
    df_m5['ma_50'] = df_m5['close'].rolling(50).mean()
    df_m5['ma_100'] = df_m5['close'].rolling(100).mean()

    ## Previous Moving Average 100

    df_m5['prev_ma_100'] = df_m5['ma_100'].shift(1)

    df_m5['sd'] = df_m5['close'].rolling(20).std()

    ## RSI

    df_m5['gain'] = (df_m5['close'] - df_m5['open']).apply(lambda x: x if x > 0 else 0)
    df_m5['loss'] = (df_m5['close'] - df_m5['open']).apply(lambda x: -x if x < 0 else 0)

    df_m5['ema_gain'] = df_m5['gain'].ewm(span=14, min_periods=14).mean()
    df_m5['ema_loss'] = df_m5['loss'].ewm(span=14, min_periods=14).mean()

    df_m5['rs'] = df_m5['ema_gain'] / df_m5['ema_loss']

    df_m5['rsi_14'] = 100 - (100 / (df_m5['rs'] + 1))

    ## Moving Average 10 of the RSI 

    df_m5['ma_rsi_14'] = df_m5['rsi_14'].rolling(10).mean()

    ## Drop missing values

    df_m5.dropna(inplace = True)

    ## Find signal
                    
    df_m5['signal'] = np.vectorize(find_signal)(df_m5['close'], df_m5['ma_21'], df_m5['ma_50'], df_m5['ma_100'], df_m5['rsi_14'], df_m5['ma_rsi_14'])

    buy_signal = df_m5[df_m5['signal']=='buy'].copy()
    sell_signal = df_m5[df_m5['signal']=='sell'].copy()

    ## Opti

    val_sl_buy = [1, 2, 3, 4, 5]
    val_sl_sell = [1, 2, 3, 4, 5]
    val_tp_buy = [1, 2, 3, 4, 5]
    val_tp_sell = [1, 2, 3, 4, 5]

    combs = list(product(val_sl_buy, val_sl_sell, val_tp_buy, val_tp_sell))

    pnls_test = []
    combs_used = []

    for comb in combs:
        class Position:
            def __init__(self, open_datetime, open_price, order_type, volume, sl, tp):
                self.open_datetime = open_datetime
                self.open_price = open_price
                self.order_type = order_type
                self.volume = volume
                self.sl = sl
                self.tp = tp
                self.close_datetime = None
                self.close_price = None
                self.profit = None
                self.status = 'open'
                                            
            def close_position(self, close_datetime, close_price):
                self.close_datetime = close_datetime
                self.close_price = close_price
                self.profit = (self.close_price - self.open_price) * self.volume if self.order_type == 'buy' \
                                                                                else (self.open_price - self.close_price) * self.volume
                self.status = 'closed'
                                        
            def _asdict(self):
                return {
                        'open_datetime' : self.open_datetime,
                        'open_price' : self.open_price,
                        'order_type' : self.order_type,
                        'volume' : self.volume,
                        'sl' : self.sl,
                        'tp' : self.tp,
                        'close_datetime' : self.close_datetime,
                        'close_price': self.close_price,
                        'profit' : self.profit,
                        'status' : self.status
                    }
                                                    
        class Strategy:
            def __init__(self, df, starting_balance, volume):
                    self.starting_balance = starting_balance
                    self.volume = volume
                    self.positions = []
                    self.data = df
                            
            def get_positions_df(self):
                    df = pd.DataFrame([position._asdict() for position in self.positions])
                    df['pnl'] = df['profit'].cumsum() + self.starting_balance
                    return df
                        
            def add_position(self, position):
                    self.positions.append(position)
                            
            def trading_allowed(self):
                    for pos in self.positions:
                         if pos.status == 'open':
                            return False
                                
                    return True
                        
            def run(self):
                    for i, data in self.data.iterrows():
                                
                        if data.signal == 'buy' and self.trading_allowed():
                            sl = data.close - comb[0] * data.sd
                            tp = data.close + comb[1] * data.sd
                            self.add_position(Position(data.time, data.close, data.signal, self.volume, sl, tp))
                                    
                        elif data.signal == 'sell' and self.trading_allowed():
                            sl = data.close + comb[2] * data.sd
                            tp = data.close - comb[3] * data.sd
                            self.add_position(Position(data.time, data.close, data.signal, self.volume, sl, tp))
                                            
                        for pos in self.positions:
                           if pos.status == 'open':
                                if (pos.sl >= data.close and pos.order_type == 'buy'):
                                    pos.close_position(data.time, pos.sl)
                                elif (pos.sl <= data.close and pos.order_type == 'sell'):
                                    pos.close_position(data.time, pos.sl)
                                elif (pos.tp <= data.close and pos.order_type == 'buy'):
                                    pos.close_position(data.time, pos.tp)
                                elif (pos.tp >= data.close and pos.order_type == 'sell'):
                                     pos.close_position(data.time, pos.tp)
                                            
                    return self.get_positions_df()
                        
        strategy_test = Strategy(df_m5, 100, 3)
                    
        result_test = strategy_test.run()


        final_profit = result_test['pnl'].iloc[-2]
        pnls_test.append(final_profit)
        combs_used.append(comb)

        print(comb, ':', final_profit)

    df_pnls_test = pd.DataFrame(pnls_test)
    df_combs_used = pd.DataFrame(combs_used)

    df_result_test = pd.concat([df_pnls_test, df_combs_used], axis=1)
    df_result_test.columns = ['final_profit', 'sl_buy', 'tp_buy', 'sl_sell', 'tp_sell']

    best_sl_tp = df_result_test[df_result_test['final_profit'] == df_result_test['final_profit'].max()]

    if len(best_sl_tp) > 1:
        best_sl_buy = mode(best_sl_tp['sl_buy'])
        best_tp_buy = mode(best_sl_tp['tp_buy'])
        best_sl_sell = mode(best_sl_tp['sl_sell'])
        best_tp_sell = mode(best_sl_tp['tp_sell'])
    else:
        best_sl_buy = best_sl_tp['sl_buy']
        best_tp_buy = best_sl_tp['tp_buy']
        best_sl_sell = best_sl_tp['sl_sell']
        best_tp_sell = best_sl_tp['tp_sell']

    best_profit = best_sl_tp['final_profit'].unique()

    return best_sl_buy, best_tp_buy, best_sl_sell, best_tp_sell, best_profit


