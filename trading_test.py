import pandas as pd
import pyqtgraph as pg
from pyqtgraph.Qt import QtCore, QtGui, QtWidgets
import time

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
        
        # Удаление дубликатов по индексу
        self.moex_data = self.moex_data[~self.moex_data.index.duplicated(keep='first')]
        # Клонирование DataFrame до ресемплинга
        moex_data_clone = self.moex_data.copy()
        
        # Ресемплинг данных с шагом в 1 минуту и заполнение пропусков последними известными значениями
        self.moex_data = self.moex_data.resample('1min').ffill()
        
        # Создание столбца "moex_open" и заполнение его на основе клона
        self.moex_data['moex_open'] = self.moex_data.index.isin(moex_data_clone.index)
    
        # Применение фильтра по стартовой дате
        start_datetime = pd.to_datetime(start_date, format='%d.%m.%Y')
        self.exmo_data = self.exmo_data[self.exmo_data.index >= start_datetime]
        self.moex_data = self.moex_data[self.moex_data.index >= start_datetime]

        # Объединение данных с использованием merge_asof
        self.data = pd.merge_asof(self.exmo_data, self.moex_data, on='datetime', direction='forward')
        self.data.to_csv('moex_data_filled.csv', sep=';')
        
    def run_backtest(self):
        app = QtWidgets.QApplication([])

        win = pg.GraphicsLayoutWidget(show=True, title="Trading Backtest")
        win.showMaximized()
        win.setWindowTitle('Trading Backtest with PyQtGraph')

        pg.setConfigOptions(antialias=True)
        
        # Создание осей для отображения времени
        axis1 = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
        axis2 = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
        axis3 = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')
        axis4 = pg.graphicsItems.DateAxisItem.DateAxisItem(orientation='bottom')

        # Создание графиков
        # indicator_plot = win.addPlot(title="Indicator", axisItems={'bottom': axis1})
        # win.nextRow()
        # plot1 = win.addPlot(title="EMA Diff", axisItems={'bottom': axis2})
        # win.nextRow()
        plot2 = win.addPlot(title="Profit", axisItems={'bottom': axis3})
        win.nextRow()
        plot3 = win.addPlot(title="Prices", axisItems={'bottom': axis4})
        
        # Связка осей для синхронной прокрутки
        # indicator_plot.setXLink(plot3)
        plot2.setXLink(plot3)
        # plot1.setXLink(plot3)

        # indicator_curve = indicator_plot.plot(pen='cyan')
        # ema_diff_curve = plot1.plot(pen='y')
        profit_curve = plot2.plot(pen='g')
        exmo_bid_curve = plot3.plot(pen='r')
        exmo_ask_curve = plot3.plot(pen='b')
        moex_usdrub_tod_curve = plot3.plot(pen='g')
        buy_scatter = pg.ScatterPlotItem(symbol='o', size=10, pen=pg.mkPen(None), brush=pg.mkBrush(0, 255, 0, 255))
        sell_scatter = pg.ScatterPlotItem(symbol='x', size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 50, 50, 255))

        plot3.addItem(buy_scatter)
        plot3.addItem(sell_scatter)
        
        profit_series = []
        indicator_series = []
        exmo_bid_series = []
        exmo_ask_series = []
        moex_series = []

        for idx, row in self.data.iterrows():
            timestamp = row['datetime'].timestamp()  # Преобразование индекса в timestamp
            exmo_bid = row['<CLOSE>_x']
            exmo_ask = row['<CLOSE>_x'] + 0.60
            moex_usdrub_tod = row['<CLOSE>_y']

            # почему-то если торговать при закрытой MOEX, то прибиль получается больше
            result = self.trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod, True)
            # result = self.trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod, row['moex_open'])
            if result is None:
                continue
            
            trades, ema_diff, indicator = result
            self.ema_diffs.append((timestamp, ema_diff))
            profit_series.append((timestamp, self.trader.get_profit(exmo_bid)))
            indicator_series.append((timestamp, indicator))
            exmo_bid_series.append((timestamp, exmo_bid))
            exmo_ask_series.append((timestamp, exmo_ask))
            moex_series.append((timestamp, moex_usdrub_tod))

            for trade_type, price in trades:
                if trade_type == 'buy':
                    self.trades.append((timestamp, 'buy', price))
                elif trade_type == 'sell':
                    self.trades.append((timestamp, 'sell', price))

        # ema_diff_curve.setData([x for x, y in self.ema_diffs], [y for x, y in self.ema_diffs])
        # indicator_curve.setData([x for x, y in indicator_series], [y for x, y in indicator_series])
        profit_curve.setData([x for x, y in profit_series], [y for x, y in profit_series])
        exmo_bid_curve.setData([x for x, y in exmo_bid_series], [y for x, y in exmo_bid_series])
        exmo_ask_curve.setData([x for x, y in exmo_ask_series], [y for x, y in exmo_ask_series])
        moex_usdrub_tod_curve.setData([x for x, y in moex_series], [y for x, y in moex_series])
        
        buy_scatter.setData([x for x, trade_type, y in self.trades if trade_type == 'buy'], [y for x, trade_type, y in self.trades if trade_type == 'buy'])
        sell_scatter.setData([x for x, trade_type, y in self.trades if trade_type == 'sell'], [y for x, trade_type, y in self.trades if trade_type == 'sell'])
        QtWidgets.QApplication.processEvents()

        QtWidgets.QApplication.exec_()

hyperparameters = {
    'window_size': 40,
    'ignore_last': 1,
    'ema_alfa1': 0.1,
    'ema_alfa2': 0.1,
    'ema_diff_buy': 0.9,
    'take_profit': 0.3,
    'trade_amount': 1
}

trader = Trader(balance_rub=1000, balance_usdt=0, hyperparameters=hyperparameters)
test = TradingTest(trader, 'exmo_USDT_RUB_2024.csv', 'mmvb_USDRUB_TOD_2024.csv')
test.load_data('22.03.2024')
test.run_backtest()
