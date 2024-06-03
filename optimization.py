import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import time
from hyperopt import fmin, tpe, hp, Trials
from trader import Trader

class TradingTest:
    def __init__(self, trader, exmo_file, moex_file):
        self.trader = trader
        self.exmo_file = exmo_file
        self.moex_file = moex_file
        self.exmo_data = None
        self.moex_data = None
        self.ema_diffs = []
        self.trades = []
        self.data = None

    def load_data(self, start_date):
        self.exmo_data = pd.read_csv(self.exmo_file, delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
        self.exmo_data['datetime'] = pd.to_datetime(self.exmo_data['<DATE>'] + ' ' + self.exmo_data['<TIME>'], format='%d%m%y %H%M%S')
        self.exmo_data.set_index('datetime', inplace=True)

        self.moex_data = pd.read_csv(self.moex_file, delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
        self.moex_data['datetime'] = pd.to_datetime(self.moex_data['<DATE>'] + ' ' + self.moex_data['<TIME>'], format='%d%m%y %H%M%S')
        self.moex_data.set_index('datetime', inplace=True)

        self.moex_data = self.moex_data[~self.moex_data.index.duplicated(keep='first')]
        moex_data_clone = self.moex_data.copy()

        self.moex_data = self.moex_data.resample('1min').ffill()
        self.moex_data['moex_open'] = self.moex_data.index.isin(moex_data_clone.index)

        start_datetime = pd.to_datetime(start_date, format='%d.%m.%Y')
        self.exmo_data = self.exmo_data[self.exmo_data.index >= start_datetime]
        self.moex_data = self.moex_data[self.moex_data.index >= start_datetime]

        self.data = pd.merge_asof(self.exmo_data, self.moex_data, on='datetime', direction='forward')
        self.data.to_csv('moex_data_filled.csv', sep=';')

    def run_backtest(self):
        profit_series = []

        for idx, row in self.data.iterrows():
            timestamp = row['datetime'].timestamp()
            exmo_bid = row['<CLOSE>_x']
            exmo_ask = row['<CLOSE>_x'] + 0.60
            moex_usdrub_tod = row['<CLOSE>_y']

            result = self.trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod, True)
            if result is None:
                continue

            trades, ema_diff, indicator = result
            # self.ema_diffs.append((timestamp, ema_diff))
            profit_series.append(self.trader.get_profit(exmo_bid))

            # for trade_type, price in trades:
            #     if trade_type == 'buy':
            #         self.trades.append((timestamp, 'buy', price))
            #     elif trade_type == 'sell':
            #         self.trades.append((timestamp, 'sell', price))

        return profit_series[-1]

def optimize_hyperparameters(exmo_file, moex_file, start_date):

    def objective(params):
        hyperparameters = {
            'window_size': int(params['window_size']),
            'ignore_last': int(params['ignore_last']),
            'ema_alfa1': params['ema_alfa1'],
            'ema_alfa2': params['ema_alfa2'],
            'ema_diff_buy': params['ema_diff_buy'],
            'take_profit': params['take_profit'],
            'trade_amount': params['trade_amount']
        }
        trader = Trader(balance_rub=1000, balance_usdt=0, hyperparameters=hyperparameters)
        test = TradingTest(trader, exmo_file, moex_file)
        test.load_data(start_date)
        profit = test.run_backtest()
        return -profit

    space = {
        'window_size': hp.quniform('window_size', 20, 100, 1),
        'ignore_last': hp.quniform('ignore_last', 0, 10, 1),
        'ema_alfa1': hp.uniform('ema_alfa1', 0.01, 0.5),
        'ema_alfa2': hp.uniform('ema_alfa2', 0.01, 0.5),
        'ema_diff_buy': hp.uniform('ema_diff_buy', 0.1, 1.5),
        'take_profit': hp.uniform('take_profit', 0.1, 1.0),
        'trade_amount': hp.uniform('trade_amount', 0.1, 5.0)
    }

    trials = Trials()
    best = fmin(fn=objective,
                space=space,
                algo=tpe.suggest,
                max_evals=50,
                trials=trials)

    print("Best hyperparameters found:")
    print(best)

optimize_hyperparameters('exmo_USDT_RUB_2024.csv', 'mmvb_USDRUB_TOD_2024.csv', '11.01.2024')
