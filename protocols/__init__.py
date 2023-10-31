from protocols.element_market.buy import ElementMarketAgent
from protocols.punkswap import PunkSwapAgent
from protocols.scrollswap import ScrollSwapAgent


PROTOCOLS = {
    'PunkSwap': PunkSwapAgent,
    'ScrollSwap': ScrollSwapAgent,
    'ElementMarket': ElementMarketAgent,
}
