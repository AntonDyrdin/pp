import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from trader import Trader

class TradingTest:
    def __init__(self, trader, exmo_file, moex_file):
        self.trader = trader
        self.exmo_file = exmo_file
        self.moex_file = moex_file
        self.exmo_data = None
        self.moex_data = None
        self.ema_diffs = []
        self.trades = []  # Список для хранения точек сделок
        self.data = None

    # Метод для загрузки данных с заданной стартовой даты
    def load_data(self, start_date):
        # Чтение данных EXMO
        self.exmo_data = pd.read_csv(self.exmo_file, delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
        self.exmo_data['datetime'] = pd.to_datetime(self.exmo_data['<DATE>'] + ' ' + self.exmo_data['<TIME>'], format='%d%m%y %H%M%S')
        self.exmo_data.set_index('datetime', inplace=True)

        # Чтение данных MOEX
        self.moex_data = pd.read_csv(self.moex_file, delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
        self.moex_data['datetime'] = pd.to_datetime(self.moex_data['<DATE>'] + ' ' + self.moex_data['<TIME>'], format='%d%m%y %H%M%S')
        self.moex_data.set_index('datetime', inplace=True)

        # Применение фильтра по стартовой дате
        start_datetime = pd.to_datetime(start_date, format='%d.%m.%Y')
        self.exmo_data = self.exmo_data[self.exmo_data.index >= start_datetime]
        self.moex_data = self.moex_data[self.moex_data.index >= start_datetime]

        # Синхронизация данных
        self.data = pd.merge_asof(self.exmo_data, self.moex_data, on='datetime', direction='forward')

    def run_backtest(self):
        for idx, row in self.data.iterrows():
            if pd.isna(row['<CLOSE>_y']):
                continue  # Пропускаем, если MOEX не работает

            exmo_bid = row['<CLOSE>_x']
            exmo_ask = row['<CLOSE>_x'] + 0.60
            moex_usdrub_tod = row['<CLOSE>_y']

            self.trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod)

            if self.trader.tick_count > self.trader.window_size + self.trader.ignore_last:
                ema_exmo_bid = self.trader.calculate_ema(self.trader.exmo_bid_window[:-self.trader.ignore_last], self.trader.ema_alfa1)
                ema_moex_usdrub = self.trader.calculate_ema(self.trader.moex_usdrub_tod_window[:-self.trader.ignore_last], self.trader.ema_alfa2)
                ema_diff = ema_moex_usdrub - ema_exmo_bid
                self.ema_diffs.append((idx, ema_diff))

                # Логика торговли
                if ema_diff - exmo_bid > self.trader.ema_diff_buy:
                    self.trades.append((idx, 'buy', exmo_ask))
                elif ema_moex_usdrub > exmo_ask:
                    self.trades.append((idx, 'sell', exmo_bid))

    def plot_results(self):
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, subplot_titles=("EMA Diff", "Profit", "Prices"))

        ema_diff_series = pd.Series({x: y for x, y in self.ema_diffs})
        profit_series = pd.Series({x: self.trader.get_profit(row['<CLOSE>_x']) for x, row in self.data.iterrows() if row.name <= row.name})
        exmo_bid_series = self.data['<CLOSE>_x']
        exmo_ask_series = self.data['<CLOSE>_x'] + 0.60
        moex_usdrub_tod_series = self.data['<CLOSE>_y']

        fig.add_trace(go.Scatter(x=ema_diff_series.index, y=ema_diff_series.values, mode='lines', name='EMA Diff'), row=1, col=1)
        fig.add_trace(go.Scatter(x=profit_series.index, y=profit_series.values, mode='lines', name='Profit'), row=2, col=1)
        fig.add_trace(go.Scatter(x=exmo_bid_series.index, y=exmo_bid_series.values, mode='lines', name='Exmo Bid'), row=3, col=1)
        fig.add_trace(go.Scatter(x=exmo_ask_series.index, y=exmo_ask_series.values, mode='lines', name='Exmo Ask'), row=3, col=1)
        fig.add_trace(go.Scatter(x=moex_usdrub_tod_series.index, y=moex_usdrub_tod_series.values, mode='lines', name='MOEX USD/RUB TOD'), row=3, col=1)

        for idx, trade_type, price in self.trades:
            color = 'green' if trade_type == 'buy' else 'red'
            fig.add_trace(go.Scatter(x=[idx], y=[price], mode='markers', marker=dict(color=color, size=10), name=trade_type.capitalize()), row=3, col=1)

        fig.update_layout(height=900, width=1200, title_text="Trading Backtest Results")
        fig.show()


# Пример использования
hyperparameters = {
    'window_size': 10,
    'ignore_last': 2,
    'ema_alfa1': 0.1,
    'ema_alfa2': 0.1,
    'ema_diff_buy': 0.1,
    'take_profit': 0.8,
    'trade_amount': 1
}

trader = Trader(balance_rub=1000, balance_usdt=0, hyperparameters=hyperparameters)
test = TradingTest(trader, 'exmo_USDT_RUB_2024.csv', 'mmvb_USDRUB_TOD_2024.csv')
test.load_data('21.05.2024')
test.run_backtest()
test.plot_results()
