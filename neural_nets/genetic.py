from agent import Agent
import time
import asyncio

class Genetic:
  def __init__(self, population_size):
    self.profit_history = []
    self.ask_history = []
    self.timestamps_history = []
    self.population = []
    
    for i in range(1, population_size):
      self.population.append(Agent(window_size=5, features_count=2, id=i))
    
  async def test_individ(self, individ, dataset, dataframe, curves):
    outputs = individ.neural_net.predict(dataset)

    self.profit_history = []
    self.ask_history = []
    self.timestamps_history = []

    update_plots_each = 20
    update_counter = 0

    for i in range(0, dataset.shape[0]):
      sell = outputs[i, 0]
      buy = outputs[i, 1]
      hold = outputs[i, 2]

      action = 'HOLD'
      if sell > buy and sell > hold:
        action = 'SELL' 
      elif buy > sell and buy > hold:
        action = 'BUY' 
        
      # print(input, outputs[i])

      individ.process_tick(action, dataset[i][-1][0], dataset[i][-1][0] + 0.5, dataframe.iloc[i].name)
      
      if update_counter == update_plots_each:
        update_counter = 0
        self.profit_history.append(individ.balance_rub)
        self.timestamps_history.append(int(dataframe.iloc[i].name.timestamp()))
        self.ask_history.append(dataset[i][-1][0] + 0.5)
        
        await asyncio.sleep(0)  # Разрешаем основному потоку обрабатывать события
        
      update_counter += 1
 
  def run(self, dataset, dataframe, curves):
    while True:
      # высчитать критерий оптимальности
      for individ in self.population:
        self.test_individ(individ, dataset, dataframe, curves)
      
      # отсортировать по критерию оптимальности
      
      
      # 
