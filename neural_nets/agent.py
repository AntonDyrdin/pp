from keras.models import Sequential
from keras.layers import Dense, LSTM, Input
import numpy as np

class Agent:
  def __init__(self, window_size, features_count, id):
    self.id = id
    self.tick_counter = 0
    self.positions = []  # Список для хранения позиций { price: float, time: timestamp}
    self.buy_limit = 5
    self.balance_usdt = 0
    self.balance_rub = 1000
    self.trade_amount = 1
    self.trades = []

    self.neural_net = Sequential()
    self.neural_net.add(Input((window_size, features_count)))
    self.neural_net.add(LSTM(10, return_sequences=False))
    self.neural_net.add(Dense(10))
    self.neural_net.add(Dense(3))
    
    self.neural_net.compile(optimizer='rmsprop', loss='categorical_crossentropy')
  
  # Возвращает 'SELL', 'BUY', 'HOLD'
  def run_neural_net(self, input):
    output = self.neural_net.predict(np.expand_dims(input, axis=0))
    sell = output[0, 0]
    buy = output[0, 1]
    hold = output[0, 2]
    print(input, output)

    if sell > buy and sell > hold:
      return 'SELL' 
    elif buy > sell and buy > hold:
      return 'BUY' 
    elif hold > buy and hold > sell:
      return 'HOLD' 
    
  def process_tick(self, action, bid, ask, current_time):
        # Логика торговли
        if action == 'BUY':
          if (sum(map(lambda p: p['price'] * p['amount'], self.positions)) + self.trade_amount * ask) < self.buy_limit:
            order_id = self.execute_trade('buy', self.trade_amount, ask)
            self.balance_rub -= self.trade_amount * ask
            self.balance_usdt += self.trade_amount
            self.positions.append({'price': ask, 'time': current_time, 'amount': self.trade_amount, 'order_id': order_id})
            self.trades.append(('buy', ask))

        positions_to_remove = []
        if action == 'SELL':
          if len(self.positions) > 0:
            self.balance_rub += self.positions[-1]['amount'] * bid
            self.balance_usdt -= self.positions[-1]['amount']
            self.trades.append(('sell', bid))
            positions_to_remove.append(self.positions[-1])
        #     # Выставление ордера на продажу
        #     sell_price = ask + self.take_profit
        #     order_id = self.execute_trade('sell', self.trade_amount, sell_price)
        #     self.trades.append(('sell_order', sell_price, order_id))

        # # Проверка ордеров на продажу
        # positions_to_remove = []
        # for position in self.positions:
        #     sell_price = position['price'] + self.take_profit
        #     if bid >= sell_price:
        #         order_id = self.execute_trade('sell', position['amount'], bid)
        #         self.balance_rub += position['amount'] * bid
        #         self.balance_usdt -= position['amount']
        #         self.trades.append(('sell', bid))
        #         positions_to_remove.append(position)

        # # Удаление реализованных позиций
        for position in positions_to_remove:
            self.positions.remove(position)
        
  def execute_trade(self, trade_type, amount, price):
    # order = api_query(self.api_key, self.api_secret, self.rest_base_url, '/order_create', {
    #     'pair': 'USDT_RUB',
    #     'quantity': amount,
    #     'price': price,
    #     'type': trade_type
    # })
    # return order.get('order_id')
    return -1