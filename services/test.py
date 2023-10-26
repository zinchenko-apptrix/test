import requests

from services.token import Token, TokenCreator
from settings.config import ETH_RPC
from settings.types import NormAmount


# url = https://api.geckoterminal.com/api/v2/networks/linea/pools/0x5Ec5b1E9b1Bd5198343ABB6E55Fb695d2F7Bb308


class GeckoExchanger:
    POOLS = {
        'USDCETH': '0x5Ec5b1E9b1Bd5198343ABB6E55Fb695d2F7Bb308'
    }

    def exchange(self, src_token, dst_token, amount: int):
        pair, pair_address = self.get_pair(src_token.name, dst_token.name)
        rate = self.get_rate(pair_address)
        if pair.startswith(src_token.name):
            dst_amount = amount * rate
        else:
            dst_amount = amount / rate
        return dst_token.to_wei(dst_amount)

    def get_pair(self, token_a: str, token_b: str) -> tuple[str, str]:
        """Returns pair's symbol and address"""
        filtered_pairs = list(
            filter(lambda x: token_a in x and token_b in x, self.POOLS.keys())
        )
        if filtered_pairs:
            symbol = filtered_pairs[0]
            return symbol, self.POOLS[symbol]
        raise ValueError(f'Pair not found with tokens: {token_b} {token_a}')

    @staticmethod
    def get_rate(pool_addr: str) -> float:
        """Returns price of the base token in a pair"""
        url = f'https://api.geckoterminal.com/api/v2/networks/linea/pools/{pool_addr}'
        response = requests.get(url)
        result = response.json()
        price_native = float(result['pairs'][0]['priceNative'])
        return price_native


if __name__ == '__main__':
    print('hello')

