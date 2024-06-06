import hmac
import hashlib
import time
import json
import requests
import websocket
import threading
import signal
import json

def read_config(file_path):
    with open(file_path, 'r') as file:
        config = json.load(file)
    return config

class ExmoTrader:
    def __init__(self, config_path, balance_rub, buy_limit, balance_usdt, hyperparameters):
        config = read_config(config_path)
        self.api_key = config['api_key']
        self.api_secret = config['api_secret']
        self.balance_rub = balance_rub
        self.balance_usdt = balance_usdt
        self.hyperparameters = hyperparameters
        self.window_size = int(hyperparameters.get('window_size', 10))
        self.ema_alfa1 = hyperparameters.get('ema_alfa1', 0.1)
        self.ema_alfa2 = hyperparameters.get('ema_alfa2', 0.1)
        self.indicator_buy_edge = hyperparameters.get('indicator_buy_edge', 0.1)
        self.take_profit = hyperparameters.get('take_profit', 1.0)
        self.trade_amount = hyperparameters.get('trade_amount', 1)
        self.open_positions_delay = hyperparameters.get('open_positions_delay', 5*60)
        self.exmo_bid_window = []
        self.moex_usdrub_tod_window = []
        self.tick_counter = 0
        self.positions = []  # Список для хранения позиций { price: float, time: timestamp}
        self.buy_limit = buy_limit
        self.ws = None
        self.rest_base_url = "https://api.exmo.me/v1.1"
        self.setup_websocket()
        self.last_exmo_bid = None
        self.last_exmo_ask = None
        self.last_moex_open = None
        self.last_moex_usdrub_tod = None
        self.ema_diff = None

    def get_moex_usdrub_tod(self):
        url = "https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS/securities/USD000000TOD.json"
        response = requests.get(url)
        data = response.json()
        
        try:
            marketdata = data['marketdata']['data']
            headers = data['marketdata']['columns']
            
            last_price_index = headers.index('LAST')
            last_price = marketdata[0][last_price_index]
            state_index = headers.index('HIGHBID')
            current_state = marketdata[0][state_index] is not None
            
            # Состояние "normal" означает, что торги ведутся
            is_open = current_state == 'normal'
            
            self.last_moex_usdrub_tod = last_price
            self.last_moex_open = is_open
        except (IndexError, KeyError):
            print("Ошибка при извлечении данных ММВБ", data)
            return None

    def get_signature(self, data):
        return hmac.new(
            self.api_secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha512
        ).hexdigest()

    def api_query(self, api_method, params={}):
        params['nonce'] = int(round(time.time() * 1000))
        params = json.dumps(params)

        headers = {
            'Content-Type': 'application/json',
            'Key': self.api_key,
            'Sign': self.get_signature(params)
        }

        response = requests.post(self.rest_base_url + api_method, headers=headers, data=params)
        return response.json()

    def execute_trade(self, trade_type, amount, price):
        if trade_type == 'buy':
            order = self.api_query('/order_create', {
                'pair': 'USDT_RUB',
                'quantity': amount,
                'price': price,
                'type': 'buy'
            })
            return order['order_id']
        elif trade_type == 'sell':
            order = self.api_query('/order_create', {
                'pair': 'USDT_RUB',
                'quantity': amount,
                'price': price,
                'type': 'sell'
            })
            return order['order_id']

    def check_order_status(self, order_id):
        order_info = self.api_query('/order_trades', {'order_id': order_id})
        return order_info['result'] == 'true'

    def calculate_ema(self, prices, alpha=0.1):
        ema = [prices[0]]  # начальное значение EMA равно первому значению цены
        for price in prices[1:]:
            ema.append(ema[-1] + alpha * (price - ema[-1]))
        return ema[-1]

    def get_profit(self, bid_usdtrub):
        return self.balance_rub + (self.balance_usdt * bid_usdtrub)

    def on_message(self, ws, message):
        try:
            message = json.loads(message)
            if message['event'] == 'update' and 'data' in message:
              data = message['data']
              if  message['topic'] == 'spot/order_book_snapshots:USDT_RUB':
                  exmo_bid = float(data['bid'][0][0])
                  exmo_ask = float(data['ask'][0][0])

                  current_time = time.time()
                  trades, indicator = self.process_tick(exmo_bid, exmo_ask, current_time)
                  if trades:
                      print("Совершены сделки:", trades)
            else:
                print(message)
        except json.JSONDecodeError as e:
            print("JSON decode error:", e)
        except Exception as e:
            print("Error in on_message:", e)

    def on_error(self, ws, error):
        print("WebSocket Error:", error)

    def on_close(self, ws, close_status_code, close_msg):
        print("WebSocket Closed")

    def on_open(self, ws):
        print("WebSocket Opened")
        subscribe_message = json.dumps({
            "method": "subscribe",
            "topics": ["spot/order_book_snapshots:USDT_RUB"]
        })
        ws.send(subscribe_message)

    def setup_websocket(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            "wss://ws-api.exmo.me/v1/public",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        ws_thread = threading.Thread(target=self.ws.run_forever)
        ws_thread.start()

    def process_tick(self, exmo_bid, exmo_ask, current_time):
        self.last_exmo_ask = exmo_ask
        self.last_exmo_bid = exmo_bid
        if self.ema_diff is None:
          return [], 0

        indicator = self.last_moex_usdrub_tod - exmo_bid - self.ema_diff

        # Логика торговли
        trades = []
        if indicator > self.indicator_buy_edge:
            amount_multiplier = indicator / self.indicator_buy_edge
            if (sum(map(lambda p: p['price'] * p['amount'], self.positions)) + self.trade_amount * amount_multiplier * exmo_ask) < self.buy_limit:
                if (len(self.positions) == 0) or ((current_time - self.positions[-1]['time']) > self.open_positions_delay):
                    order_id = self.execute_trade('buy', self.trade_amount * amount_multiplier, exmo_ask)
                    self.balance_rub -= self.trade_amount * amount_multiplier * exmo_ask
                    self.balance_usdt += self.trade_amount * amount_multiplier
                    self.positions.append({'price': exmo_ask, 'time': current_time, 'amount': self.trade_amount * amount_multiplier, 'order_id': order_id})
                    trades.append(('buy', exmo_ask))

                    # Выставление ордера на продажу
                    sell_price = exmo_ask + self.take_profit
                    order_id = self.execute_trade('sell', self.trade_amount * amount_multiplier, sell_price)
                    trades.append(('sell_order', sell_price, order_id))

        # Проверка ордеров на продажу
        positions_to_remove = []
        for position in self.positions:
            sell_price = position['price'] + self.take_profit
            if exmo_bid >= sell_price:
                order_id = self.execute_trade('sell', position['amount'], exmo_bid)
                self.balance_rub += position['amount'] * exmo_bid
                self.balance_usdt -= position['amount']
                trades.append(('sell', exmo_bid))
                positions_to_remove.append(position)

        # Удаление реализованных позиций
        for position in positions_to_remove:
            self.positions.remove(position)

        return trades, indicator

    def minute_ticker(self):
        self.get_moex_usdrub_tod()
        if self.last_exmo_bid is None:
            return None
        self.exmo_bid_window.append(self.last_exmo_bid)
        self.moex_usdrub_tod_window.append(self.last_moex_usdrub_tod)
        self.tick_counter += 1

        # Удаление старых значений, если превышено окно
        if len(self.exmo_bid_window) > self.window_size:
            self.exmo_bid_window.pop(0)
        if len(self.moex_usdrub_tod_window) > self.window_size:
            self.moex_usdrub_tod_window.pop(0)

        # Если накоплено недостаточно данных, просто выходим
        if self.tick_counter <= self.window_size:
            return None

        ema_exmo_bid = self.calculate_ema(self.exmo_bid_window, self.ema_alfa1)
        ema_moex_usdrub = self.calculate_ema(self.moex_usdrub_tod_window, self.ema_alfa2)
        self.ema_diff = ema_moex_usdrub - ema_exmo_bid

    def minute_ticker_loop(self):
      while True:
        self.minute_ticker()

        time.sleep(60)

# Параметры
hyperparameters = {'window_size': 323, 'ema_alfa1': 0.01903373699962808, 'ema_alfa2': 0.3737415716707692, 'indicator_buy_edge': 0.9671520166825177, 'take_profit': 0.2594676630862253, 'trade_amount': 1, 'open_positions_delay': 9.0}

# Инициализация трейдера
trader = ExmoTrader('secret.json', balance_rub=300, buy_limit=1000, balance_usdt=0, hyperparameters=hyperparameters)

def signal_handler(sig, frame):
    print('Stopping WebSocket...')
    if trader.ws:
        trader.ws.close()
    print('Exiting.')
    exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

trader.minute_ticker_loop()
