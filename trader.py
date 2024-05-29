class Trader:
    def __init__(self, balance_rub, balance_usdt, hyperparameters):
        self.balance_rub = balance_rub
        self.balance_usdt = balance_usdt
        self.hyperparameters = hyperparameters
        self.window_size = hyperparameters.get('window_size', 10)
        self.ignore_last = hyperparameters.get('ignore_last', 2)
        self.ema_alfa1 = hyperparameters.get('ema_alfa1', 0.1)
        self.ema_alfa2 = hyperparameters.get('ema_alfa2', 0.1)
        self.ema_diff_buy = hyperparameters.get('ema_diff_buy', 0.1)
        self.take_profit = hyperparameters.get('take_profit', 0.8)
        self.exmo_bid_window = []
        self.moex_usdrub_tod_window = []
        self.tick_count = 0
        self.positions = []  # Список для хранения позиций (покупок)
        self.sell_orders = []  # Список для хранения ордеров на продажу

    def get_profit(self, bid_usdtrub):
        return self.balance_rub + (self.balance_usdt * bid_usdtrub)

    def calculate_ema(self, prices, alpha=0.1):
        if not prices:
            return 0
        ema = [prices[0]]  # начальное значение EMA равно первому значению цены
        for price in prices[1:]:
            ema.append(ema[-1] + alpha * (price - ema[-1]))
        return ema[-1]

    def place_buy_order(self, exmo_ask):
        amount_to_trade = self.hyperparameters.get('trade_amount', 1)
        if self.balance_rub >= amount_to_trade * exmo_ask:
            self.balance_rub -= amount_to_trade * exmo_ask
            self.balance_usdt += amount_to_trade
            self.positions.append((amount_to_trade, exmo_ask))
            print(f"Buy order placed: {amount_to_trade} USDT at {exmo_ask} RUB")

    def place_sell_order(self, amount, buy_price):
        sell_price = buy_price + self.take_profit
        self.sell_orders.append((amount, sell_price))
        print(f"Sell order placed: {amount} USDT at {sell_price} RUB")

    def process_tick(self, exmo_bid, exmo_ask, moex_usdrub_tod):
        self.exmo_bid_window.append(exmo_bid)
        self.moex_usdrub_tod_window.append(moex_usdrub_tod)
        self.tick_count += 1

        # Удаление старых значений, если превышено окно
        if len(self.exmo_bid_window) > self.window_size:
            self.exmo_bid_window.pop(0)
        if len(self.moex_usdrub_tod_window) > self.window_size:
            self.moex_usdrub_tod_window.pop(0)

        # Если накоплено недостаточно данных, просто выходим
        if self.tick_count <= self.window_size + self.ignore_last:
            return

        # Рассчет EMA с игнорированием последних L значений
        ema_exmo_bid = self.calculate_ema(self.exmo_bid_window[:-self.ignore_last], self.ema_alfa1)
        ema_moex_usdrub = self.calculate_ema(self.moex_usdrub_tod_window[:-self.ignore_last], self.ema_alfa2)
        
        # Медленно меняющаяся разница между биржами
        ema_diff = ema_moex_usdrub - ema_exmo_bid

        # Если цена на EXMO после корректировки на "постоянную" разницу ушла ниже, чем ema_diff_buy
        if ema_diff - exmo_bid > self.ema_diff_buy:
            # Покупка
            self.place_buy_order(exmo_ask)

        # Проверка на исполнение ордеров на продажу
        for order in self.sell_orders.copy():
            amount, sell_price = order
            if exmo_bid >= sell_price:
                self.balance_rub += amount * exmo_bid
                self.balance_usdt -= amount
                self.sell_orders.remove(order)
                print(f"Sell order executed: {amount} USDT at {sell_price} RUB")

        # Установка ордеров на продажу для новых покупок
        while self.positions:
            amount, buy_price = self.positions.pop(0)
            self.place_sell_order(amount, buy_price)


# Пример использования
hyperparameters = {'trade_amount': 10,
                   'window_size': 5,
                   'ignore_last': 2,
                   'ema_alfa1': 0.1,
                   'ema_alfa2': 0.1,
                   'ema_diff_buy': 0.1, 
                   'take_profit': 0.8}

trader = Trader(balance_rub=1000, balance_usdt=0, hyperparameters=hyperparameters)

# Пример тиков
ticks = [
    (76, 74, 75), (77, 75, 74), (78, 76, 73),
    (75, 73, 74), (74, 72, 73), (73, 71, 72)
]

for exmo_bid, exmo_ask, moex_usdrub_tod in ticks:
    trader.process_tick(exmo_bid, exmo_ask, moex_usdrub_tod)

# Обновленный баланс и профит после обработки тиков
print(f'Updated balance RUB: {trader.balance_rub}')
print(f'Updated balance USDT: {trader.balance_usdt}')
bid_usdtrub = 75
profit = trader.get_profit(bid_usdtrub)
print(f'Updated profit: {profit}')
