from agent import Agent


class Genetic:
  def __init__(self, population_size):
    self.population = []
    
    for i in range(1, population_size):
      self.population.append(Agent(window_size=5, features_count=2, id=i))
    
  def test_individ(self, individ, dataset, dataframe):
    outputs = individ.neural_net.predict(dataset)

    for i in range(0, dataset.shape[0]):
      sell = outputs[i, 0]
      buy = outputs[i, 1]
      hold = outputs[i, 2]

      action = 'HOLD'
      if sell > buy and sell > hold:
        action = 'SELL' 
      elif buy > sell and buy > hold:
        action = 'BUY' 

      individ.process_tick(action, dataset[i][-1][0], dataset[i][-1][0] + 0.5, dataframe.iloc[i].name)
      
  def run(self, inputs_set, dataframe):
    while True:
      # высчитать критерий оптимальности
      for individ in self.population:
        self.test_individ(individ, inputs_set, dataframe)
      
      # отсортировать по критерию оптимальности
      
      
      # 
