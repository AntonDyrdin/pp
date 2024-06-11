import time
import json
import websocket
import threading
import requests
import logging
from utils import api_query, calculate_ema
from data_handler import save_tick_to_csv
from config import get_api_credentials
import datetime
from finam import FinamWebSocketClient
import pandas as pd
from dateutil import tz

class ExmoTrader:
    def __init__(self, config_path, balance_rub, buy_limit, balance_usdt, hyperparameters):
        self.api_key, self.api_secret = get_api_credentials(config_path)
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
        self.last_exmo_bid = None
        self.last_exmo_ask = None
        self.last_moex_open = None
        self.last_moex_usdrub_tod = None
        self.ema_diff = None
        self.profit_series = []
        self.indicator_series = []
        self.exmo_bid_series = []
        self.exmo_ask_series = []
        self.moex_series = []
        self.ema_diff_series = []
        self.trades = []

        self.load_initial_data()
        self.setup_websocket()

    def resample_data(self, data, from_time, current_time, timestamp_key, tz_localize):
        """Resample data to ensure it covers the entire required range."""
        # Convert data to DataFrame
        df = pd.DataFrame(data)
        df['timestamp'] = pd.to_datetime(df[timestamp_key], unit='ms')
        if tz_localize:
            df['timestamp'] = df['timestamp'].dt.tz_localize(datetime.timezone.utc)

        df.set_index('timestamp', inplace=True)
        
        # Resample data to 1-minute intervals, forward-filling missing values
        all_times = pd.date_range(
          start=datetime.datetime.fromtimestamp(from_time + 60, tz=datetime.timezone.utc),
          end=datetime.datetime.fromtimestamp(current_time, tz=datetime.timezone.utc),
          freq='1min'
        )
        df = df.reindex(all_times, method='ffill')
        
        return df

    def load_initial_data(self):
        current_time = int(datetime.datetime.now().timestamp())
        from_time = current_time - self.window_size * 60

        exmo_url = f"{self.rest_base_url}/candles_history?symbol=USDT_RUB&resolution=1&from={from_time}&to={current_time}"
        finam_client = FinamWebSocketClient()

        # Загрузка данных с Exmo
        exmo_response = requests.get(exmo_url)
        exmo_response.raise_for_status()
        exmo_data = exmo_response.json()

        # Загрузка данных с Moex
        moex_candles = finam_client.await_historical_data()
        moex_candles.reverse()

        # Приведение данных к общему временному ряду
        exmo_df = self.resample_data(exmo_data['candles'], from_time, current_time, 't', tz_localize=True)
        moex_df = self.resample_data(moex_candles, from_time, current_time, 'timestamp', tz_localize=False)

        # Добавление данных в окна
        self.exmo_bid_window = exmo_df['c'].tolist()
        self.moex_usdrub_tod_window = moex_df['close'].tolist()

        for idx, row in exmo_df.iterrows():
            self.exmo_bid_series.append((idx.timestamp(), row['c']))
        for idx, row in moex_df.iterrows():
            self.moex_series.append((idx.timestamp(), row['close']))

        print(len(self.exmo_bid_window), len(self.moex_usdrub_tod_window))

        self.calculate_initial_ema()

    def calculate_initial_ema(self):
        if len(self.exmo_bid_window) == self.window_size and len(self.moex_usdrub_tod_window) == self.window_size:
            ema_exmo_bid = calculate_ema(self.exmo_bid_window, self.ema_alfa1)
            ema_moex_usdrub = calculate_ema(self.moex_usdrub_tod_window, self.ema_alfa2)
            self.ema_diff = ema_moex_usdrub - ema_exmo_bid
            self.tick_counter = self.window_size

    def get_moex_usdrub_tod(self):
        url = "https://iss.moex.com/iss/engines/currency/markets/selt/boards/CETS/securities/USD000000TOD.json"
        try:
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            
            marketdata = data['marketdata']['data']
            headers = data['marketdata']['columns']
            
            last_price_index = headers.index('LAST')
            last_price = marketdata[0][last_price_index]
            state_index = headers.index('TRADINGSTATUS')
            
            self.last_moex_usdrub_tod = last_price
            self.last_moex_open = marketdata[0][state_index] == 'T'
        except requests.RequestException as e:
            logging.error(f"Ошибка при запросе данных ММВБ: {e}")
        except (IndexError, KeyError) as e:
            logging.error(f"Ошибка при извлечении данных ММВБ: {e}")

    def execute_trade(self, trade_type, amount, price):
        order = api_query(self.api_key, self.api_secret, self.rest_base_url, '/order_create', {
            'pair': 'USDT_RUB',
            'quantity': amount,
            'price': price,
            'type': trade_type
        })
        return order.get('order_id')

    def check_order_status(self, order_id):
        order_info = api_query(self.api_key, self.api_secret, self.rest_base_url, '/order_trades', {'order_id': order_id})
        return order_info.get('result') == 'true'

    def get_profit(self, bid_usdtrub):
        return self.balance_rub + (self.balance_usdt * bid_usdtrub)

    def on_message(self, ws, message):
        try:
            message = json.loads(message)
            if message['event'] == 'update' and 'data' in message:
                data = message['data']
                if message['topic'] == 'spot/order_book_snapshots:USDT_RUB':
                    exmo_bid = float(data['bid'][0][0])
                    exmo_ask = float(data['ask'][0][0])

                    current_time = time.time()
                    trades, indicator = self.process_tick(exmo_bid, exmo_ask, current_time)
                    if trades:
                        logging.info(f"Совершены сделки: {trades}")
                    save_tick_to_csv('history.csv', [datetime.datetime.utcnow().strftime("%d.%m.%Y %H:%M:%S.%f")[:-3], exmo_bid, exmo_ask])
            else:
                logging.info(message)
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
        except Exception as e:
            logging.error(f"Error in on_message: {e}")

    def on_error(self, ws, error):
        print(error)
        logging.error(f"EXMO WebSocket Error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logging.info(f"EXMO WebSocket Closed")

    def on_open(self, ws):
        logging.info(f"EXMO WebSocket Opened")
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
        ws_thread.daemon = True
        ws_thread.start()

    def process_tick(self, exmo_bid, exmo_ask, current_time):
        self.last_exmo_ask = exmo_ask
        self.last_exmo_bid = exmo_bid

        self.exmo_bid_series.append((current_time, exmo_bid))
        self.exmo_ask_series.append((current_time, exmo_ask))

        if self.ema_diff is not None:
            indicator = self.last_moex_usdrub_tod - exmo_bid - self.ema_diff
        else:
            indicator = 0

        self.ema_diff_series.append((current_time, self.ema_diff))
        self.profit_series.append((current_time, self.get_profit(exmo_bid)))
        self.indicator_series.append((current_time, indicator))
        self.moex_series.append((current_time, self.last_moex_usdrub_tod))

        if self.ema_diff is None:
            return [], indicator

        # Логика торговли
        if indicator > self.indicator_buy_edge:
            amount_multiplier = indicator / self.indicator_buy_edge
            if (sum(map(lambda p: p['price'] * p['amount'], self.positions)) + self.trade_amount * amount_multiplier * exmo_ask) < self.buy_limit:
                if (len(self.positions) == 0) or ((current_time - self.positions[-1]['time']) > self.open_positions_delay):
                    order_id = self.execute_trade('buy', self.trade_amount * amount_multiplier, exmo_ask)
                    self.balance_rub -= self.trade_amount * amount_multiplier * exmo_ask
                    self.balance_usdt += self.trade_amount * amount_multiplier
                    self.positions.append({'price': exmo_ask, 'time': current_time, 'amount': self.trade_amount * amount_multiplier, 'order_id': order_id})
                    self.trades.append(('buy', exmo_ask))

                    # Выставление ордера на продажу
                    sell_price = exmo_ask + self.take_profit
                    order_id = self.execute_trade('sell', self.trade_amount * amount_multiplier, sell_price)
                    self.trades.append(('sell_order', sell_price, order_id))

        # Проверка ордеров на продажу
        positions_to_remove = []
        for position in self.positions:
            sell_price = position['price'] + self.take_profit
            if exmo_bid >= sell_price:
                order_id = self.execute_trade('sell', position['amount'], exmo_bid)
                self.balance_rub += position['amount'] * exmo_bid
                self.balance_usdt -= position['amount']
                self.trades.append(('sell', exmo_bid))
                positions_to_remove.append(position)

        # Удаление реализованных позиций
        for position in positions_to_remove:
            self.positions.remove(position)

        return self.trades, indicator

    def minute_ticker(self):
        self.get_moex_usdrub_tod()
        if self.last_exmo_bid is None:
            return None
        self.exmo_bid_window.append(self.last_exmo_bid)
        self.moex_usdrub_tod_window.append(self.last_moex_usdrub_tod)
        self.tick_counter += 1

        # Удаление старых значений, если превышено окно
        if len(self.exmo_bid_window) >= self.window_size:
            self.exmo_bid_window.pop(0)
        if len(self.moex_usdrub_tod_window) >= self.window_size:
            self.moex_usdrub_tod_window.pop(0)

        # Если накоплено недостаточно данных, просто выходим
        if self.tick_counter < self.window_size:
            return None

        ema_exmo_bid = calculate_ema(self.exmo_bid_window, self.ema_alfa1)
        ema_moex_usdrub = calculate_ema(self.moex_usdrub_tod_window, self.ema_alfa2)
        self.ema_diff = ema_moex_usdrub - ema_exmo_bid

    def minute_ticker_loop(self):
        while True:
            self.minute_ticker()
            time.sleep(60)
