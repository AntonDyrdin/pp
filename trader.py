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
        self.take_profit = hyperparameters.get('take_profit', 1.0)
        self.trade_amount = hyperparameters.get('trade_amount', 1)
        self.exmo_bid_window = []
        self.moex_usdrub_tod_window = []
        self.tick_count = 0
        self.positions = []  # Список для хранения позиций (цены покупки)

    def get_profit(self, bid_usdtrub):
        return self.balance_rub + (self.balance_usdt * bid_usdtrub)

    def calculate_ema(self, prices, alpha=0.1):
        ema = [prices[0]]  # начальное значение EMA равно первому значению цены
        for price in prices[1:]:
            ema.append(ema[-1] + alpha * (price - ema[-1]))
        return ema[-1]

    def process_tick(self, exmo_bid, exmo_ask, moex_usdrub_tod, moex_open):
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
            return None
        

        ema_exmo_bid = self.calculate_ema(self.exmo_bid_window[:-self.ignore_last] if self.ignore_last > 0 else self.exmo_bid_window, self.ema_alfa1)
        ema_moex_usdrub = self.calculate_ema(self.moex_usdrub_tod_window[:-self.ignore_last] if self.ignore_last > 0 else self.moex_usdrub_tod_window, self.ema_alfa2)
        ema_diff = ema_moex_usdrub - ema_exmo_bid
        indicator = moex_usdrub_tod - exmo_bid - ema_diff

        if not moex_open:
            # Пропускаем, если MOEX не работает
            return [], ema_diff, indicator

        # Логика торговли
        trades = []
        if indicator > self.ema_diff_buy:
            self.balance_rub -= self.trade_amount * exmo_ask
            self.balance_usdt += self.trade_amount
            self.positions.append(exmo_ask)
            trades.append(('buy', exmo_ask))

            # Выставление ордера на продажу
            sell_price = exmo_ask + self.take_profit
            trades.append(('sell_order', sell_price))

        # Проверка ордеров на продажу
        positions_to_remove = []
        for buy_price in self.positions:
            sell_price = buy_price + self.take_profit
            if exmo_bid >= sell_price:
                self.balance_rub += self.trade_amount * exmo_bid
                self.balance_usdt -= self.trade_amount
                trades.append(('sell', exmo_bid))
                positions_to_remove.append(buy_price)

        # Удаление реализованных позиций
        for position in positions_to_remove:
            self.positions.remove(position)

        return trades, ema_diff, indicator
