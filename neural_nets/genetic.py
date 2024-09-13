from agent import Agent
import time
import asyncio
import numpy as np
import concurrent.futures

class Genetic:
  def __init__(self, population_size, mutation_coefficient, scaler):
    self.ask_history = []
    self.timestamps_history = []
    self.population = []
    self.mutation_coefficient = mutation_coefficient
    self.scaler = scaler
    
    for i in range(0, population_size):
      self.population.append(Agent(window_size=5, features_count=2, id=i))

    self.best_part = 1
      
  def test_individ(self, individ, dataset, dataframe):
    if individ.profit != None:
      print('Лишние вычисления!')
      return individ.profit
    # self.profit_history = []
    # self.ask_history = []
    # self.timestamps_history = []
    individ.balance_usdt = 0
    individ.balance_rub = individ.start_balance_rub

    outputs = individ.neural_net.predict(dataset)

    # update_plots_each = 20
    # update_counter = 0

    for i in range(0, dataset.shape[0]):
      action = individ.decode_net_output(outputs[i])

      # SPREAD = 0.5
      SPREAD = 0
      individ.process_tick(action, self.scaler.inverse_transform(dataset[i][-1][0].reshape(-1, 1))[0,0], self.scaler.inverse_transform(dataset[i][-1][0].reshape(-1, 1))[0,0] + SPREAD, dataframe.iloc[i].name)
      
      # if update_counter == update_plots_each:
      #   update_counter = 0
      #   self.profit_history.append(individ.balance_rub)
      #   self.timestamps_history.append(int(dataframe.iloc[i].name.timestamp()))
      #   self.ask_history.append(dataset[i][-1][0] + 0.5)
        
      #   await asyncio.sleep(0)  # Разрешаем основному потоку обрабатывать события
        
      # update_counter += 1

    # USDT * USDT_bid + RUB - RUB_start
    individ.profit = float(individ.balance_usdt) * dataset[i][-1][0] + individ.balance_rub - individ.start_balance_rub

    print(f"Individ id={individ.id} profit: {individ.profit}")
    return individ.profit
 
  async def crossover_weights(self):
    positive_part_count = len(list(filter(lambda i : i.profit > 0, self.population)))
    self.best_part = int((len(self.population) / 2) if positive_part_count > (len(self.population) / 2) else positive_part_count)
    print(positive_part_count, self.best_part)
    net_weights = list(map(lambda i : i.neural_net.get_weights(), self.population))

    if positive_part_count == 0:
      for i in range(len(self.population)):
        self.population[i].reset_weights()
        self.population[i].profit = None
    else:
      for i in range(self.best_part, len(self.population)):
        # Для каждого слоя (или набора весов) в нейросетях
        for j in range(len(net_weights[i])):
            # Для каждого веса внутри слоя
            for k in np.ndindex(net_weights[i][j].shape):
                net_weights[i][j][k] = net_weights[np.random.randint(0, self.best_part)][j][k]

                # Мутация
                if np.random.rand() < self.mutation_coefficient:
                    net_weights[i][j][k] += np.random.normal(0, 0.1) - 0.05  # небольшое случайное отклонение

        # Устанавливаем новые веса
        self.population[i].neural_net.set_weights(net_weights[i])

        self.population[i].profit = None

  async def test_population(self, dataset, dataframe):
    # Используем ProcessPoolExecutor для распараллеливания по процессам
    with concurrent.futures.ProcessPoolExecutor() as executor:
      # Распределяем вычисления self.test_individ по процессам
      futures = []
      for individ in self.population:
        if individ.profit == None:
          futures.append(executor.submit(self.test_individ, individ, dataset, dataframe))
      
      # Ждем завершения всех задач и собираем результаты
      results = [future.result() for future in concurrent.futures.as_completed(futures)]
      for i in range(len(results)):
        self.population[-i - 1].profit = results[-i - 1]

  def test_population_single_core(self, dataset, dataframe):
      for individ in self.population:
        if individ.profit == None:
          self.test_individ(individ, dataset, dataframe)

  async def run(self, dataset, dataframe):
    print(f"Выборка: {dataset.shape} {dataset}")
    
    while True:
      await self.test_population(dataset, dataframe)
      # self.test_population_single_core(dataset, dataframe)
      
      print("-----")
      # сортировка по критерию оптимальности (по убыванию поля profit)
      self.population.sort(key=lambda individ: individ.profit, reverse=True)

      for individ in self.population:
        print(f"Individ id={individ.id} profit: {individ.profit}")
      # Перекомбинация весов нейросетей
      await self.crossover_weights()