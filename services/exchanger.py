import requests
from web3.types import Wei

from services.tokens import Token
from settings.types import NormAmount


class GeckoExchanger:
    POOLS = {
        'USDCETH': '0x5Ec5b1E9b1Bd5198343ABB6E55Fb695d2F7Bb308',
        'USDTETH': '0x5Ec5b1E9b1Bd5198343ABB6E55Fb695d2F7Bb308',
        'USDCUSDT': '0x258d5f860b11ec73ee200eb14f1b60a3b7a536a2',
    }

    @classmethod
    def exchange(
        cls,
        src_token: Token,
        dst_token: Token,
        amount: NormAmount,
    ) -> NormAmount:
        pair, pair_address = cls.get_pair(src_token.name, dst_token.name)
        rate = cls.get_rate(pair_address)
        if pair.startswith(src_token.name):
            dst_amount = amount / rate
        else:
            dst_amount = amount * rate
        return dst_amount

    @classmethod
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
        url = f'https://api.geckoterminal.com/api/v2/networks/scroll/pools/{pool_addr}'
        response = requests.get(url)
        result = response.json()
        price_native = float(result['data']['attributes']['quote_token_price_base_token'])
        return price_native


def exchange(src_token: Token, dst_token: Token, amount: Wei) -> int:
    amount_dst = GeckoExchanger.exchange(
        src_token,
        dst_token,
        src_token.from_wei(amount),
    )
    wei_amount = dst_token.to_wei(amount_dst)
    if dst_token.decimals == 6:
        return wei_amount // 10 ** 4 * 10 ** 4
    return wei_amount


# if __name__ == '__main__':
#     src_token = TokenCreator.get('ETH', ETH_RPC)
#     dst_token = TokenCreator.get('USDC', ETH_RPC)
#     dst_amount = GeckoExchanger.exchange(src_token, dst_token, 1)
#     print(dst_amount)

