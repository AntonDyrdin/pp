from agent import Agent
import time
import asyncio
import numpy as np

class Genetic:
  def __init__(self, population_size, mutation_coefficient):
    self.ask_history = []
    self.timestamps_history = []
    self.population = []
    self.mutation_coefficient = mutation_coefficient
    
    for i in range(0, population_size):
      self.population.append(Agent(window_size=5, features_count=2, id=i))
    
  async def test_individ(self, individ, dataset, dataframe, curves):
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

      individ.process_tick(action, dataset[i][-1][0], dataset[i][-1][0] + 0.5, dataframe.iloc[i].name)
      
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
 
  async def crossover_weights(self):
    half_population = len(self.population) // 2  # половина популяции

    # Проход по парным элементам в первой половине популяции
    for i in range(0, half_population, 2):
      net1_weights = self.population[i].neural_net.get_weights()
      net2_weights = self.population[i + 1].neural_net.get_weights()

      # Для каждого слоя (или набора весов) в нейросетях
      for j in range(len(net1_weights)):
          # Для каждого веса внутри слоя
          for k in np.ndindex(net1_weights[j].shape):
              # Рекомбинация: обмен весами по вероятности 0.5
              if np.random.rand() > 0.5:
                  net1_weights[j][k], net2_weights[j][k] = net2_weights[j][k], net1_weights[j][k]

              # Мутация для веса net1_weights[j][k]
              if np.random.rand() < self.mutation_coefficient:
                  net1_weights[j][k] += np.random.normal(0, 0.1)  # небольшое случайное отклонение

              # Мутация для веса net2_weights[j][k]
              if np.random.rand() < self.mutation_coefficient:
                  net2_weights[j][k] += np.random.normal(0, 0.1)  # небольшое случайное отклонение


      # Устанавливаем новые веса в нейросети отстающих индивидов
      self.population[half_population + i].neural_net.set_weights(net1_weights)
      self.population[half_population + i + 1].neural_net.set_weights(net2_weights)

  async def run(self, dataset, dataframe, curves):
    print(f"Выборка: {dataset.shape} {dataset}")
    while True:
      # высчитать критерий оптимальности
      for individ in self.population:
        await self.test_individ(individ, dataset, dataframe, curves)
      
      # сортировка по критерию оптимальности (по убыванию поля profit)
      self.population.sort(key=lambda individ: individ.profit, reverse=True)

      # Перекомбинация весов нейросетей
      await self.crossover_weights()

