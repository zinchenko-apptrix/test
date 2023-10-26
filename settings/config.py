import os

from dotenv import load_dotenv

load_dotenv()

PROJECT = os.getenv('PROJECT', 'Linea')
ETH_RPC = os.getenv('ETH_RPC', 'https://eth.llamarpc.com')
MAIN_RPC = os.getenv('MAIN_RPC', 'https://rpc.scroll.io')
MAIN_SCAN = 'https://scrollscan.com/tx/'

GAS_WAITING = 30
GAS_UP_RATE = 1.1
GAS_PRICE_UP_RATE = 1.1

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
