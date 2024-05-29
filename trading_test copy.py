import pandas as pd
import matplotlib.pyplot as plt

from trader import Trader

class TradingTest:
    def __init__(self, trader, exmo_file, moex_file):
        self.trader = trader
        self.exmo_file = exmo_file
        self.moex_file = moex_file
        self.exmo_data = None
        self.moex_data = None

    def load_data(self):
        # Чтение данных EXMO
        self.exmo_data = pd.read_csv(self.exmo_file, delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
        self.exmo_data['datetime'] = pd.to_datetime(self.exmo_data['<DATE>'] + ' ' + self.exmo_data['<TIME>'], format='%d%m%y %H%M%S')
        self.exmo_data.set_index('datetime', inplace=True)

        # Чтение данных MOEX
        self.moex_data = pd.read_csv(self.moex_file, delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
        self.moex_data['datetime'] = pd.to_datetime(self.moex_data['<DATE>'] + ' ' + self.moex_data['<TIME>'], format='%d%m%y %H%M%S')
        self.moex_data.set_index('datetime', inplace=True)

        # Синхронизация данных
        self.data = pd.merge_asof(self.exmo_data, self.moex_data, on='datetime', direction='forward')

    def run_backtest(self):
        ema_diffs = []
        trades = []  # Список для хранения точек сделок

        for idx, row in self.data.iterrows():
            if pd.isna(row['<CLOSE>_y']):
                continue  # Пропускаем, если MOEX не работает

            exmo_bid = row['<CLOSE>_x']
            exmo_ask = row['<CLOSE>_x'] + 0.60
            moex_usdrub_tod = row['<CLOSE>_y']

            # Запомнить текущие цены для визуализации
            self.trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod)

            if self.trader.tick_count > self.trader.window_size + self.trader.ignore_last:
                ema_exmo_bid = self.trader.calculate_ema(self.trader.exmo_bid_window[:-self.trader.ignore_last], self.trader.ema_alfa1)
                ema_moex_usdrub = self.trader.calculate_ema(self.trader.moex_usdrub_tod_window[:-self.trader.ignore_last], self.trader.ema_alfa2)
                ema_diff = ema_moex_usdrub - ema_exmo_bid
                ema_diffs.append((idx, ema_diff))

                # Логика торговли
                if ema_diff - exmo_bid > self.trader.ema_diff_buy:
                    # Покупка
                    trades.append((idx, 'buy', exmo_ask))
                elif ema_moex_usdrub > exmo_ask:
                    # Продажа
                    trades.append((idx, 'sell', exmo_bid))

        return ema_diffs, trades

    def plot_results(self, ema_diffs, trades):
        ema_diff_series = pd.Series({x: y for x, y in ema_diffs})
        profit_series = pd.Series({x: self.trader.get_profit(row['<CLOSE>_x']) for x, row in self.data.iterrows()})
        exmo_bid_series = self.data['<CLOSE>_x']
        exmo_ask_series = self.data['<CLOSE>_x'] + 0.60
        moex_usdrub_tod_series = self.data['<CLOSE>_y']

        fig, ax1 = plt.subplots()

        color = 'tab:blue'
        ax1.set_xlabel('Time')
        ax1.set_ylabel('EMA Diff', color=color)
        ax1.plot(ema_diff_series.index, ema_diff_series.values, color=color, label='EMA Diff')
        ax1.tick_params(axis='y', labelcolor=color)

        ax2 = ax1.twinx()
        color = 'tab:red'
        ax2.set_ylabel('Profit', color=color)
        ax2.plot(profit_series.index, profit_series.values, color=color, label='Profit')
        ax2.tick_params(axis='y', labelcolor=color)

        # Добавляем графики bid, ask и moex_usdrub_tod
        ax2.plot(exmo_bid_series.index, exmo_bid_series.values, label='Exmo Bid', color='green')
        ax2.plot(exmo_ask_series.index, exmo_ask_series.values, label='Exmo Ask', color='orange')
        ax2.plot(moex_usdrub_tod_series.index, moex_usdrub_tod_series.values, label='MOEX USDRUB TOD', color='purple')

        # Добавляем точки покупок и продаж
        for trade in trades:
            time, action, price = trade
            if action == 'buy':
                ax2.scatter(time, price, marker='^', color='green', s=100, label='Buy')
            elif action == 'sell':
                ax2.scatter(time, price, marker='v', color='red', s=100, label='Sell')

        fig.tight_layout()
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        plt.show()

# Пример использования
hyperparameters = {'trade_amount': 10, 'window_size': 5, 'ignore_last': 2, 'ema_alfa1': 0.1, 'ema_alfa2': 0.1, 'ema_diff_buy': 0.1}
trader = Trader(balance_rub=1000, balance_usdt=100, hyperparameters=hyperparameters)

test = TradingTest(trader, 'exmo_USDT_RUB_2024.csv', 'mmvb_USDRUB_TOD_2024.csv')
test.load_data()
ema_diffs, trades = test.run_backtest()
test.plot_results(ema_diffs, trades)
