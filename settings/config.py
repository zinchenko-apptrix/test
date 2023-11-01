import os

from dotenv import load_dotenv

load_dotenv()

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PROJECT = os.getenv('PROJECT', 'Linea')
ETH_RPC = os.getenv('ETH_RPC', 'https://eth.llamarpc.com')
MAIN_RPC = os.getenv('MAIN_RPC', 'https://rpc.scroll.io')
MAIN_SCAN = 'https://scrollscan.com/tx/'

GAS_WAITING = 30
GAS_UP_RATE = 1.1
GAS_PRICE_UP_RATE = 1.1

# Element market
ELEMENT_MIN_PRICE = float(os.getenv('SHORT_SLEEP', 0.00000001))
ELEMENT_MAX_PRICE = float(os.getenv('SHORT_SLEEP', 0.00001))

# SELENIUM-METAMASK
SHORT_SLEEP = int(os.getenv('SHORT_SLEEP', 1))
SLEEP = int(os.getenv("SLEEP", 5))
LONG_SLEEP = int(os.getenv("LONG_SLEEP", 15))
VERY_LONG_SLEEP = int(os.getenv("VERY_LONG_SLEEP", 30))
RETRIES_BY_FEE = 10
PASSWORD = 'd3ja42ngo420'


# Arbitrum One
ARBITRUM_RPC = os.getenv('ARBITRUM_RPC', 'https://arb1.arbitrum.io/rpc')

# Binance
BINANCE_API_KEY = os.getenv('BINANCE_API_KEY')
BINANCE_SECRET = os.getenv('BINANCE_SECRET')

