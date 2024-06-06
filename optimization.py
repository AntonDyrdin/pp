import pandas as pd
import numpy as np
from hyperopt import fmin, tpe, hp, Trials
from trader import Trader

class TradingTest:
    def __init__(self, trader, exmo_file, moex_file):
        self.trader = trader
        self.exmo_file = exmo_file
        self.moex_file = exmo_file
        self.exmo_data = None
        self.moex_data = None
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

    def run_backtest(self):
        profit_series = []

        for idx, row in self.data.iterrows():
            timestamp = row['datetime'].timestamp()
            exmo_bid = row['<CLOSE>_x']
            exmo_ask = row['<CLOSE>_x'] + 0.60
            moex_usdrub_tod = row['<CLOSE>_y']

            self.trader.minute_ticker(exmo_bid, exmo_ask, moex_usdrub_tod, row['moex_open'], timestamp)
            result = self.trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod, row['moex_open'], timestamp)
            if result is None:
                continue

            profit_series.append(self.trader.get_profit(exmo_bid))

        return profit_series

def calculate_sharpe_ratio(profit_series):
    returns = np.diff(profit_series) / profit_series[:-1]  # доходность в процентах
    mean_return = np.mean(returns)
    std_return = np.std(returns)

    # Коэффициент Шарпа (предполагаем безрисковую ставку равную 0)
    sharpe_ratio = mean_return / std_return if std_return != 0 else 0
    return sharpe_ratio

def optimize_hyperparameters(exmo_file, moex_file, start_date):
    global best_hyperparams
    global best_result
    best_hyperparams = None
    best_result = 0

    def objective(params):
        hyperparameters = {
            'window_size': int(params['window_size']),
            'ema_alfa1': params['ema_alfa1'],
            'ema_alfa2': params['ema_alfa2'],
            'indicator_buy_edge': params['indicator_buy_edge'],
            'take_profit': params['take_profit'],
            'trade_amount': 2,
            'open_positions_delay': params['open_positions_delay'],
        }

        start_balance_rub = 300.0
        trader = Trader(balance_rub=start_balance_rub, buy_limit=start_balance_rub, balance_usdt=0, hyperparameters=hyperparameters)
        test = TradingTest(trader, exmo_file, moex_file)
        test.load_data(start_date)
        profit_series = test.run_backtest()

        if len(profit_series) < 2:  # Проверка, чтобы избежать деления на ноль при вычислении коэффициента Шарпа
            return 0

        sharpe_ratio = calculate_sharpe_ratio(profit_series)
        result = profit_series[-1]
        
        global best_result
        global best_hyperparams

        if best_result < result:
          best_result = result
          best_hyperparams = hyperparameters
          print(best_result)
          print(best_hyperparams)

        return -result

    space = {
        'window_size': hp.quniform('window_size', 10, 350, 1),
        'ema_alfa1': hp.uniform('ema_alfa1', 0.0001, 0.1),
        'ema_alfa2': hp.uniform('ema_alfa2', 0.01, 0.5),
        'indicator_buy_edge': hp.uniform('indicator_buy_edge', 0.3, 1.5),
        'take_profit': hp.uniform('take_profit', 0.01, 0.5),
        'open_positions_delay': hp.quniform('open_positions_delay', 0, 30, 1)
    }
    
    best = None

    trials = Trials()
    best = fmin(fn=objective,
                space=space,
                algo=tpe.suggest,
                max_evals=50,
                trials=trials)

    print("Best hyperparameters found:")
    print(best)

optimize_hyperparameters('exmo_USDT_RUB_2024.csv', 'mmvb_USDRUB_TOD_2024.csv', '03.05.2024')
