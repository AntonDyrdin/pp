import json
import websocket
import threading
import logging
import datetime
import time
import queue

logging.basicConfig(level=logging.INFO)

class FinamWebSocketClient:
    def __init__(self):
        self.ws_thread = None
        self.ws = None
        self.history_queue = queue.Queue()

    def on_message(self, ws, message):
        message = json.loads(message)
        # print(message)
        trades = []
        if '3' in message and '4' in message['3']:
            fragment = json.loads(message['3'])
            if '4' in fragment and isinstance(fragment['4'], list) and '4' in fragment['4'][0]:
                for item in fragment['4'][0]['4']:
                    if '5' in item:
                        timestamp = item['1']
                        open_price = item['2']
                        high_price = item['3']
                        low_price = item['4']
                        close_price = item['5']
                        volume = item['6']
                        trade_data = {
                            'timestamp': datetime.datetime.fromtimestamp(timestamp, tz=datetime.timezone.utc),
                            'open': open_price,
                            'high': high_price,
                            'low': low_price,
                            'close': close_price,
                            'volume': volume
                        }
                        trades.append(trade_data)
        self.history_queue.put(trades)
        logging.info(f"Received trade data: {len(trades)} items")

    def on_error(self, ws, error):
        logging.error(f"Finam WebSocket error: {error}")

    def on_close(self, ws, close_status_code, close_msg):
        logging.info("Finam WebSocket closed")

    def on_open(self, ws):
        logging.info("Finam WebSocket opened")
        time.sleep(1)
        ws.send(json.dumps({"1": [{"1": 237, "2": 1, "3": "{\"1\":\"finamru-online\",\"2\":\"bja7d923v63e\",\"3\":14}", "11": int(time.time()*1000)}]}))
        time.sleep(1)
        ws.send(json.dumps({"1": [{"1": 1000001, "2": 6, "3": "{\"1\":[{\"1\":182456,\"3\":1,\"4\":851,\"6\":false}]}", "11": int(time.time()*1000)}]}))

    def connect(self):
        websocket.enableTrace(False)
        self.ws = websocket.WebSocketApp(
            "wss://ta-streaming.finam.ru/ta/server/?command=start&protocol=5&version=j2t_lite-html5-0.0.1&locale=en",
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        self.ws.on_open = self.on_open
        self.ws_thread = threading.Thread(target=self.ws.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def await_historical_data(self):
        self.connect()
        historical_data = []
        while True:
            try:
                historical_data = self.history_queue.get(timeout=10)
                if len(historical_data) > 0:
                    break
            except queue.Empty:
                logging.error("Timeout waiting for trade data")
                break
        self.ws.close()
        return historical_data

# # Пример использования
# if __name__ == "__main__":
#     client = FinamWebSocketClient()
#     historical_data = client.await_historical_data()
#     for data in historical_data:
#         print(data)
