import pandas as pd

from genetic import Genetic
import numpy as np
from PyQt5 import QtWidgets
import pyqtgraph as pg

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

# Объединение DataFrame и создание массива данных
merged_df = pd.merge(df1_close, df3_close, left_index=True, right_index=True, how='outer', suffixes=('_file1', '_file3')).fillna(0)
dataset = merged_df.values

# Создание входного набора с использованием окон
window_size = 5
inputs_set = np.lib.stride_tricks.sliding_window_view(dataset, window_shape=(window_size, dataset.shape[1]))

# Преобразование к нужной форме
inputs_set = inputs_set[:, 0, :, :]

print(inputs_set.shape)

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

# инициализировать популяцию
genetic = Genetic(population_size=2)
genetic.test_individ(genetic.population[0], inputs_set[700000:,:,:], merged_df[700000:])
print(genetic.population[0].balance_usdt)
print(genetic.population[0].balance_rub)

# запустить генетический алгоритм
