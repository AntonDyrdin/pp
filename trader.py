class Trader:
    def __init__(self, balance_rub, buy_limit, balance_usdt, hyperparameters):
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

    def get_profit(self, bid_usdtrub):
        return self.balance_rub + (self.balance_usdt * bid_usdtrub)

    def calculate_ema(self, prices, alpha=0.1):
        ema = [prices[0]]  # начальное значение EMA равно первому значению цены
        for price in prices[1:]:
            ema.append(ema[-1] + alpha * (price - ema[-1]))
        return ema[-1]

    def process_tick(self, exmo_bid, exmo_ask, moex_usdrub_tod, moex_open, current_time):
        self.exmo_bid_window.append(exmo_bid)
        self.moex_usdrub_tod_window.append(moex_usdrub_tod)
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
        ema_diff = ema_moex_usdrub - ema_exmo_bid
        indicator = moex_usdrub_tod - exmo_bid - ema_diff

        # Логика торговли
        trades = []
        if indicator > self.indicator_buy_edge:
            # # Не совершаем покупок, если MOEX не работает
            # if moex_open:
            # покупать пропорционально indicator
            amount_multiplier = indicator / self.indicator_buy_edge
            # Не тратим больше buy_limit одновременно
            if (sum(map(lambda p: p['price'] * p['amount'], self.positions)) + self.trade_amount * amount_multiplier * exmo_ask) < self.buy_limit:
              if (len(self.positions) == 0) or ((current_time - self.positions[-1]['time']) > self.open_positions_delay):
                self.balance_rub -= self.trade_amount * amount_multiplier * exmo_ask
                self.balance_usdt += self.trade_amount * amount_multiplier
                self.positions.append({ 'price': exmo_ask, 'time': current_time, 'amount': self.trade_amount * amount_multiplier})
                trades.append(('buy', exmo_ask))

                # Выставление ордера на продажу
                sell_price = exmo_ask + self.take_profit
                trades.append(('sell_order', sell_price))

        # Проверка ордеров на продажу
        positions_to_remove = []
        for position in self.positions:
            sell_price = position['price'] + self.take_profit
            if exmo_bid >= sell_price:
                self.balance_rub += position['amount'] * exmo_bid
                self.balance_usdt -= position['amount']
                trades.append(('sell', exmo_bid))
                positions_to_remove.append(position)

        # Удаление реализованных позиций
        for position in positions_to_remove:
            self.positions.remove(position)

        return trades, ema_diff, indicator
