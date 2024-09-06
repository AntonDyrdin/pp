import sys
import signal
import logging
from PyQt5 import QtWidgets
import pyqtgraph as pg
from exmo_trader import ExmoTrader
from data_handler import setup_logging

# Установка логирования
setup_logging()

# Параметры
hyperparameters = {
    'window_size': 50,
    'ema_alfa1': 0.01903373699962808,
    'ema_alfa2': 0.3737415716707692,
    'indicator_buy_edge': 0.9671520166825177,
    'take_profit': 0.2594676630862253,
    'trade_amount': 1,
    'open_positions_delay': 9.0
}

# Инициализация трейдера
trader = ExmoTrader('secret.json', balance_rub=300, buy_limit=1000, balance_usdt=0, hyperparameters=hyperparameters)

# Запуск основного цикла в отдельном потоке
import threading
ticker_thread = threading.Thread(target=trader.minute_ticker_loop)
ticker_thread.start()

# Инициализация PyQtGraph
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
indicator_plot = win.addPlot(title="Indicator", axisItems={'bottom': axis2})
indicator_plot.showGrid(True, True)
win.nextRow()
plot2 = win.addPlot(title="Profit", axisItems={'bottom': axis3})
plot2.showGrid(True, True)
win.nextRow()
plot3 = win.addPlot(title="Prices", axisItems={'bottom': axis4})
plot3.showGrid(True, True)

# Связка осей для синхронной прокрутки
indicator_plot.setXLink(plot3)
plot2.setXLink(plot3)

indicator_curve = indicator_plot.plot(pen='cyan')

profit_curve = plot2.plot(pen='g')
exmo_bid_curve = plot3.plot(pen='r')
exmo_ask_curve = plot3.plot(pen='b')
moex_usdrub_tod_curve = plot3.plot(pen='g')
buy_scatter = pg.ScatterPlotItem(symbol='o', size=10, pen=pg.mkPen(None), brush=pg.mkBrush(0, 255, 0, 255))
sell_scatter = pg.ScatterPlotItem(symbol='x', size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 50, 50, 255))

plot3.addItem(buy_scatter)
plot3.addItem(sell_scatter)

# Обновление графиков
def update_graphs():
    indicator_curve.setData([x for x, y in trader.indicator_series], [y for x, y in trader.indicator_series])
    profit_curve.setData([x for x, y in trader.profit_series], [y for x, y in trader.profit_series])
    exmo_bid_curve.setData([x for x, y in trader.exmo_bid_series], [y for x, y in trader.exmo_bid_series])
    exmo_ask_curve.setData([x for x, y in trader.exmo_ask_series], [y for x, y in trader.exmo_ask_series])
    moex_usdrub_tod_curve.setData([x for x, y in trader.moex_series], [y for x, y in trader.moex_series])

    buy_scatter.setData([x for x, trade_type, y in trader.trades if trade_type == 'buy'], [y for x, trade_type, y in trader.trades if trade_type == 'buy'])
    sell_scatter.setData([x for x, trade_type, y in trader.trades if trade_type == 'sell'], [y for x, trade_type, y in trader.trades if trade_type == 'sell'])

    QtWidgets.QApplication.processEvents()

# Таймер для обновления графиков
graph_timer = pg.QtCore.QTimer()
graph_timer.timeout.connect(update_graphs)
graph_timer.start(1000)

def on_close():
    logging.info('Stopping WebSocket...')
    if trader.ws:
        trader.ws.close()
    logging.info('Exiting.')
    ticker_thread.stop()
    timer.stop()
    sys.exit(0)
    exit(0)

# Подписка на событие закрытия окна
win.closeEvent = lambda event: on_close()

signal.signal(signal.SIGINT, on_close)
signal.signal(signal.SIGTERM, on_close)

# Запуск приложения
sys.exit(app.exec_())