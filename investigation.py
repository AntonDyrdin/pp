import pandas as pd
import matplotlib.pyplot as plt
from statsmodels.tsa.seasonal import seasonal_decompose

# Чтение первого CSV файла
df1 = pd.read_csv('exmo_USDT_RUB_2024.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
df1['datetime'] = pd.to_datetime(df1['<DATE>'] + ' ' + df1['<TIME>'], format='%d%m%y %H%M%S')
df1.set_index('datetime', inplace=True)

# Чтение второго CSV файла
df2 = pd.read_csv('mmvb_USDRUB_TOD_2024.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
df2['datetime'] = pd.to_datetime(df2['<DATE>'] + ' ' + df2['<TIME>'], format='%d%m%y %H%M%S')
df2.set_index('datetime', inplace=True)

# Чтение файла c BTC
df3 = pd.read_csv('exmo_BTC_USDT_2024.csv', delimiter=';', dtype={'<DATE>': str, '<TIME>': str})
df3['datetime'] = pd.to_datetime(df3['<DATE>'] + ' ' + df3['<TIME>'], format='%d%m%y %H%M%S')
df3.set_index('datetime', inplace=True)

# Сглаживание данных шума скользящим средним
window_size = 10
# df1['<VOL>'] = df1['<VOL>'].rolling(window=window_size, min_periods=1).mean()
# df2['<VOL>'] = df2['<VOL>'].rolling(window=window_size, min_periods=1).mean()
# df1['<CLOSE>'] = df1['<CLOSE>'].rolling(window=window_size, min_periods=1).mean()
# df2['<CLOSE>'] = df2['<CLOSE>'].rolling(window=window_size, min_periods=1).mean()
# df3['<CLOSE>'] = df3['<CLOSE>'].rolling(window=window_size, min_periods=1).mean()


# df1['<CLOSE>'] = df1['<CLOSE>'] - 3
# Разложение временного ряда и удаление сезонности для первого файла
# decompose_result1 = seasonal_decompose(df1['<VOL>'], model='additive', period=1440)  # период 1440 минут (24 часа * 60 минут)
# df1['<VOL>_deseasonalized'] = df1['<VOL>'] - decompose_result1.seasonal
# df1['<VOL>_seasonal'] =  decompose_result1.seasonal

# Разложение временного ряда и удаление сезонности для второго файла
# decompose_result2 = seasonal_decompose(df2['<VOL>'], model='additive', period=1440)
# df2['<VOL>_deseasonalized'] = df2['<VOL>'] - decompose_result2.seasonal
# df2['<VOL>_seasonal'] =  decompose_result2.seasonal

# Объединение данных по 'datetime'
# merged_df = pd.merge(df1[['<VOL>_seasonal']], df2[['<VOL>_seasonal']], left_index=True, right_index=True, how='outer', suffixes=('_file1', '_file2'))
# merged_df = pd.merge(df1[['<VOL>_deseasonalized']], df2[['<VOL>_deseasonalized']], left_index=True, right_index=True, how='outer', suffixes=('_file1', '_file2'))
merged_df = pd.merge(df1[['<CLOSE>']], df2[['<CLOSE>']], left_index=True, right_index=True, how='outer', suffixes=('_file1', '_file2'))
merged_df = pd.merge(merged_df, df3[['<CLOSE>']], left_index=True, right_index=True, how='outer')
merged_df.rename(columns={'<CLOSE>': '<CLOSE>_file3'}, inplace=True)
merged_df = pd.merge(merged_df, df2[['<CLOSE>']], left_index=True, right_index=True, how='outer')

merged_df['diff'] = merged_df['<CLOSE>_file1'] - (merged_df['<CLOSE>_file1'] - merged_df['<CLOSE>_file2']).rolling(window=40, min_periods=1).mean()
merged_df['diff2'] = merged_df['<CLOSE>_file1'] - ((merged_df['<CLOSE>_file1']).rolling(window=40, min_periods=1).mean() - (merged_df['<CLOSE>_file2']).rolling(window=40, min_periods=1).mean())

# Построение графика с двумя шкалами оси Y для выбросов
fig, ax1 = plt.subplots(figsize=(14, 7))

# Выбросы из первого файла
# ax1.plot(merged_df.index, merged_df['<VOL>_smoothed_1'], label='Deseasonalized smoothed Data File 1')
# ax1.plot(merged_df.index, merged_df['<VOL>_seasonal_file1'], label='<VOL>_seasonal_file1')
# ax1.plot(merged_df.index, merged_df['<VOL>_deseasonalized_file1'], label='Deseasonalized Data File 1')
ax1.plot(merged_df.index, merged_df['<CLOSE>_file1'], label='USDT/RUB EXMO', color='green',linewidth=0.5)
ax1.plot(merged_df.index, merged_df['<CLOSE>_file2'], label='USD/RUB TOD MMVB', color='red',linewidth=0.5)
ax1.plot(merged_df.index, merged_df['diff'], label='diff', color='blue',linewidth=0.5)
ax1.plot(merged_df.index, merged_df['diff2'], label='diff2', color='black',linewidth=0.5)
ax1.set_xlabel('Date and Time')
ax1.tick_params(axis='y')
ax1.legend(loc='upper left')

# Создание второй оси Y
ax2 = ax1.twinx()
# ax2.plot(merged_df.index, merged_df['<VOL>_smoothed_2'], label='Deseasonalized smoothed Data File 2', color='red')
# ax2.plot(merged_df.index, merged_df['<VOL>_seasonal_file2'], label='<VOL>_seasonal_file2', color='pink')
ax2.plot(merged_df.index, merged_df['<CLOSE>_file3'], label='BTC/USDT EXMO', color='cyan',linewidth=0.5)
ax2.tick_params(axis='y')
ax2.legend(loc='upper right')

plt.xticks(rotation=45)
plt.tight_layout()

# Показываем график
plt.show()
