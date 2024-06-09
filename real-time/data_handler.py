import csv
import logging

def setup_logging():
    logging.basicConfig(level=logging.INFO, filename='trading_bot.log',
                        format='%(asctime)s:%(levelname)s:%(message)s')

def save_tick_to_csv(file_name, data):
    with open(file_name, mode='a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(data)
