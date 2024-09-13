if __name__ == "__main__":
  import pandas as pd
  import sys
  from genetic import Genetic
  import numpy as np
  from PyQt5 import QtWidgets, QtCore
  import pyqtgraph as pg
  import asyncio
  import qasync
  from sklearn.preprocessing import StandardScaler
  from agent import Agent
  import matplotlib.pyplot as plt

  # подгрузить датасеты
  # features_count = 0
  # df1 = pd.read_csv('datasets/exmo_USDT_RUB.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
  # df1['datetime'] = pd.to_datetime(df1['<DATE>'] + ' ' + df1['<TIME>'], format='%d%m%y %H%M%S')
  # df1.set_index('datetime', inplace=True)
  # features_count += 1

  # df3 = pd.read_csv('datasets/exmo_BTC_USDT.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
  # df3['datetime'] = pd.to_datetime(df3['<DATE>'] + ' ' + df3['<TIME>'], format='%d%m%y %H%M%S')
  # df3.set_index('datetime', inplace=True)
  # features_count += 1

  # merged_df = pd.merge(df1[['<CLOSE>']], df3[['<CLOSE>']], left_index=True, right_index=True, how='outer', suffixes=('_file1', '_file3'))

  # dataset = numpy.zeros((merged_df.shape[0], features_count),dtype=numpy.float32)
  # window_size = 60
  # for i in range(0, merged_df.shape[0]):
  #   dataset[i, 0] = (float)(merged_df['<CLOSE>_file1'].iloc[i])
  #   dataset[i, 1] = (float)(merged_df['<CLOSE>_file3'].iloc[i])

  # inputs_set = numpy.zeros((dataset.shape[0] - window_size, window_size, dataset.shape[1]), dtype=numpy.float32)
  # for i in range(0, dataset.shape[0] - window_size):
  #     for j in range(0, window_size):
  #         for k in range(0, dataset.shape[1]):
  #             inputs_set[i,j,k] = dataset[i + j][k]

  # Чтение и предобработка первого DataFrame
  df1 = pd.read_csv('datasets/exmo_USDT_RUB.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
  df1['datetime'] = pd.to_datetime(df1['<DATE>'] + ' ' + df1['<TIME>'], format='%d%m%y %H%M%S')
  df1.set_index('datetime', inplace=True)
  df1_close = df1['<CLOSE>'].astype(np.float32)

  # Чтение и предобработка второго DataFrame
  df3 = pd.read_csv('datasets/exmo_BTC_USDT.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
  df3['datetime'] = pd.to_datetime(df3['<DATE>'] + ' ' + df3['<TIME>'], format='%d%m%y %H%M%S')
  df3.set_index('datetime', inplace=True)
  df3_close = df3['<CLOSE>'].astype(np.float32)

  # Стандартизация данных
  scaler_USDT_RUB = StandardScaler()
  df1_standardized = scaler_USDT_RUB.fit_transform(df1_close.values.reshape(-1, 1))

  scaler_BTC_USDT = StandardScaler()
  df3_standardized = scaler_BTC_USDT.fit_transform(df3_close.values.reshape(-1, 1))

  # Преобразование обратно в DataFrame
  df1_standardized = pd.DataFrame(df1_standardized, index=df1.index, columns=['<CLOSE>'])
  df3_standardized = pd.DataFrame(df3_standardized, index=df3.index, columns=['<CLOSE>'])

  # Объединение DataFrame и создание массива данных
  merged_df = pd.merge(df1_standardized, df3_standardized, left_index=True, right_index=True, how='outer', suffixes=('_file1', '_file3')).ffill()
  dataset = merged_df.values

  # Создание входного набора с использованием окон
  window_size = 10
  inputs_set = np.lib.stride_tricks.sliding_window_view(dataset, window_shape=(window_size, dataset.shape[1]))
  inputs_set = inputs_set[:, 0, :, :]

  print(inputs_set.shape)

  # Инициализация PyQtGraph
  app = QtWidgets.QApplication([])
  loop = qasync.QEventLoop(app)
  asyncio.set_event_loop(loop)

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
  currency_plot = win.addPlot(title="Сurrency", axisItems={'bottom': axis2})
  currency_plot.showGrid(True, True)
  win.nextRow()
  profit_plot = win.addPlot(title="Profit", axisItems={'bottom': axis3})
  profit_plot.showGrid(True, True)
  win.nextRow()

  profit_plot.setXLink(currency_plot)

  # Таймер для обновления графиков
  timer = QtCore.QTimer()

  curves = {}

  curves['profit'] = profit_plot.plot([], [], pen=pg.mkPen('r', width=1))
  # curves['ask'] = currency_plot.plot(pen='r')
  # curves['bid'] = currency_plot.plot(pen='b')

  # curves['buy_scatter'] = pg.ScatterPlotItem(symbol='o', size=10, pen=pg.mkPen(None), brush=pg.mkBrush(0, 255, 0, 255))
  # curves['sell_scatter'] = pg.ScatterPlotItem(symbol='x', size=10, pen=pg.mkPen(None), brush=pg.mkBrush(255, 50, 50, 255))

  # currency_plot.addItem(curves['buy_scatter'])
  # currency_plot.addItem( curves['sell_scatter'])

  # Инициализировать популяцию
  genetic = Genetic(population_size=20, mutation_coefficient=0.05, scaler=scaler_USDT_RUB, window_size=window_size)

  def update_graphs_training():
    curves['profit'].setData(genetic.best_individ_profit_history)

  def update_graphs_testing():
    sell_trades = list(filter(lambda t: t[1] == 'sell', genetic.population[0].trades))
    buy_trades = list(filter(lambda t: t[1] == 'buy', genetic.population[0].trades))
    curves['buy_scatter'].setData(list(map(lambda t: t[0], sell_trades)), list(map(lambda t: t[2], sell_trades)))
    curves['sell_scatter'].setData(list(map(lambda t: t[0], buy_trades)), list(map(lambda t: t[2], buy_trades)))
    curves['profit'].setData(genetic.timestamps_history, genetic.population[0].profit_history)
    curves['ask'].setData(genetic.timestamps_history, genetic.ask_history)
    curves['bid'].setData(genetic.timestamps_history, genetic.bid_history)

  # # Привязка таймера к обновлению графиков
  timer.timeout.connect(update_graphs_training)
  timer.start(3000) 

  async def main():
      fig, ax1 = plt.subplots(figsize=(14, 7))
      ax2 = ax1.twinx()
      ax1.plot(merged_df[599900:600000].index, inputs_set[599900-window_size+1:600000-window_size+1,-1,0], label='inputs_set', color='green',linewidth=0.5)
      ax1.plot(merged_df[599900:600000].index, merged_df[599900:600000]['<CLOSE>_file1'], label='merged_df', color='cyan',linewidth=0.5)
      ax2.plot(merged_df[599900:600000].index, scaler_USDT_RUB.inverse_transform(inputs_set[599900-window_size+1:600000-window_size+1,-1,0].reshape(-1, 1)), label='inverse_transform', color='red',linewidth=0.5)
      plt.show()
      # await genetic.run(inputs_set[599900-window_size+1:600000-window_size+1,:,:], merged_df[595000+window_size:600000+window_size])
      # await genetic.test_individ(genetic.population[0], inputs_set[710000:,:,:], merged_df[710000:])

  if __name__ == "__main__":
      with loop:  # Запуск основного event loop-а
          asyncio.ensure_future(main())  # Запуск асинхронной задачи
          loop.run_forever()  # Запуск основного цикла приложения
