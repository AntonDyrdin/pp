import os
import json

def read_config(file_path):
    with open(file_path, 'r') as file:
        config = json.load(file)
    return config

def get_api_credentials(config_path):
    config = read_config(config_path)
    api_key = os.getenv('EXMO_API_KEY', config['api_key'])
    api_secret = os.getenv('EXMO_API_SECRET', config['api_secret'])
    return api_key, api_secret
