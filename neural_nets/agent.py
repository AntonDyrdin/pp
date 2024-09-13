from keras.models import Sequential
from keras.layers import Dense, LSTM, Input
import numpy as np
from tensorflow.keras import initializers
from tensorflow.keras.layers import Dense, LSTM
from tensorflow.keras.models import load_model

class Agent:
  def __init__(self, window_size, features_count, id):
    self.id = id
    self.tick_counter = 0
    self.positions = []  # Список для хранения позиций { price: float, time: timestamp}
    self.buy_limit = 500
    self.balance_usdt = 0
    self.balance_rub = 0
    self.start_balance_rub = 1000
    self.trade_amount = 1
    self.trades = []
    self.profit_history = []
    self.profit = None

    self.neural_net = Sequential()
    self.neural_net.add(Input((window_size, features_count)))
    self.neural_net.add(LSTM(20, return_sequences=False))
    self.neural_net.add(Dense(10))
    self.neural_net.add(Dense(5))
    self.neural_net.add(Dense(3))
    
    self.neural_net.compile(optimizer='rmsprop', loss='categorical_crossentropy')
    # self.neural_net = load_model('saved_models//344_0.keras')

  # Возвращает output[ 1 x 3 ]
  def run_neural_net(self, input):
    return self.neural_net.predict(np.expand_dims(input, axis=0))
  
  # Возвращает 'SELL', 'BUY', 'HOLD'
  def decode_net_output(self, output):
    sell = output[0]
    buy = output[1]
    hold = output[2]

    if sell > buy and sell > hold:
      return 'SELL' 
    elif buy > sell and buy > hold:
      return 'BUY' 
    elif hold > buy and hold > sell:
      return 'HOLD' 

  def get_action(self, input):
    output = self.run_neural_net(input)
    decode_net_output(output[0])

  def process_tick(self, action, bid, ask, current_time):
    # Логика торговли
    if action == 'BUY':
      # if (sum(map(lambda p: p['price'] * p['amount'], self.positions)) + self.trade_amount * ask) < self.buy_limit:
      if self.balance_rub > self.trade_amount * ask:
        # order_id = self.execute_trade('buy', self.trade_amount, ask)
        self.balance_rub -= self.trade_amount * ask
        self.balance_usdt += self.trade_amount
        # self.positions.append({'price': ask, 'time': current_time, 'amount': self.trade_amount, 'order_id': order_id})
        # self.trades.append((current_time.timestamp(), 'buy', ask))

    positions_to_remove = []
    if action == 'SELL':
      # if len(self.positions) > 0:
      if self.balance_usdt > 0:
        self.balance_rub += self.trade_amount * bid
        self.balance_usdt -= self.trade_amount
        # self.balance_rub += self.positions[-1]['amount'] * bid
        # self.balance_usdt -= self.positions[-1]['amount']
        # self.trades.append((current_time.timestamp(), 'sell', bid))
        # positions_to_remove.append(self.positions[-1])
    #     # Выставление ордера на продажу
    #     sell_price = ask + self.take_profit
    #     order_id = self.execute_trade('sell', self.trade_amount, sell_price)
    #     self.trades.append((current_time.timestamp(), 'sell_order', sell_price, order_id))

    # # Проверка ордеров на продажу
    # positions_to_remove = []
    # for position in self.positions:
    #     sell_price = position['price'] + self.take_profit
    #     if bid >= sell_price:
    #         order_id = self.execute_trade('sell', position['amount'], bid)
    #         self.balance_rub += position['amount'] * bid
    #         self.balance_usdt -= position['amount']
    #         self.trades.append((current_time.timestamp(), 'sell', bid))
    #         positions_to_remove.append(position)

    # # Удаление реализованных позиций
    # for position in positions_to_remove:
    #     self.positions.remove(position)
        
  def execute_trade(self, trade_type, amount, price):
    # order = api_query(self.api_key, self.api_secret, self.rest_base_url, '/order_create', {
    #     'pair': 'USDT_RUB',
    #     'quantity': amount,
    #     'price': price,
    #     'type': trade_type
    # })
    # return order.get('order_id')
    return -1

  def reset_weights(self):
    for layer in self.neural_net.layers:
        if isinstance(layer, Dense):
            # Сброс весов для Dense слоев
            weight_shape = layer.kernel.shape
            bias_shape = layer.bias.shape
            layer.set_weights([
                initializers.get('glorot_uniform')(weight_shape),
                initializers.get('zeros')(bias_shape)
            ])
        elif isinstance(layer, LSTM):
            # Сброс весов для LSTM слоев
            weights = layer.get_weights()
            kernel_shape = weights[0].shape
            recurrent_kernel_shape = weights[1].shape
            bias_shape = weights[2].shape
            
            new_weights = [
                initializers.get('glorot_uniform')(kernel_shape),          # kernel
                initializers.get('orthogonal')(recurrent_kernel_shape),    # recurrent_kernel
                initializers.get('zeros')(bias_shape)                       # bias
            ]
            layer.set_weights(new_weights)