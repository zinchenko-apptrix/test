from aptos_sdk.account import Account
from aptos_sdk.client import RestClient
from eth_abi.packed import encode_packed
from database.models import PolygonAptosBridge, AptosPolygonBridge

NODE_URL = 'https://fullnode.mainnet.aptoslabs.com/v1'
EXPLORER = 'https://explorer.aptoslabs.com/txn/'
USDC_RESOURCE = '0x1::coin::CoinStore<0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC>'
USDC_MODULE = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::asset::USDC"
BRIDGE_FUNCTION = "0xf22bede237a07e121b56d91a491eb7bcdfd1f5907926a9e58338f964a01b17fa::coin_bridge::send_coin_from"
MIN_NATIVE_FEE = 0.04


def get_adapter_params():
    """Второй аргумент это fee второй стороны моста (MATIC)"""
    adapter_param3 = encode_packed(["uint16", "uint64"], [1, 150000])
    return '0x' + adapter_param3.hex()


def get_balance(address):
    try:
        balance = client.account_resource(address, USDC_RESOURCE)
        return balance['data']['coin']['value']
    except KeyError:
        print(f'{address} | на счету нет USDC')


def get_fee_steps(min_fee: float, max_fee: float):
    if min_fee < MIN_NATIVE_FEE:
        raise ValueError('Минимальная сумма fee - 0.04')
    return [
        int(min_fee * 10**8),
        int((min_fee * 10 ** 8 + max_fee * 10**8) / 2),
        int(max_fee * 10**8)
    ]


def create_transact(pa_bridge, amount, native_fee, sender_account):
    payload = {
        "type": "entry_function_payload",
        "arguments": [
            "109",
            pa_bridge.addressPolygon.replace('0x', '0x000000000000000000000000').lower(),
            str(amount),
            '133',  # 5519591  3207835 0.03207835
            '0',
            False,
            get_adapter_params(),
            '',
        ],
        "function": BRIDGE_FUNCTION,
        "type_arguments": [USDC_MODULE]
    }
    txn = client.submit_transaction(sender=sender_account, payload=payload)
    # client.wait_for_transaction(txn)
    AptosPolygonBridge.create(
        addressAptos=pa_bridge.addressAptos,
        privateKeyAptos=pa_bridge.privateKeyAptos,
        addressPolygon=pa_bridge.addressPolygon,
        privateKeyPolygon=pa_bridge.privateKeyPolygon,
        aptos_txn=txn,
        amount=amount / 10**6,
    )
    print(f'{pa_bridge.addressAptos} | SUCCESS txn: {EXPLORER}{txn}')


def bridge(key, percent, fee_steps):
    for fee in fee_steps:
        pa_bridge = PolygonAptosBridge.get_by_key_from(key=key, claimed=True)
        sender_account = Account.load_key(pa_bridge.privateKeyAptos)
        balance_usdc = get_balance(pa_bridge.addressAptos)
        amount = int(int(balance_usdc) * percent / 100)
        print(f'{pa_bridge.addressAptos} | amount: {amount / 10**6} USDC, fee: {fee / 10**8} APT')
        try:
            create_transact(pa_bridge, amount, fee, sender_account)
            return
        except AssertionError as error:
            if "ELAYERZERO_INSUFFICIENT_FEE(0x10000)" not in error.args[0]:
                print(f'{pa_bridge.addressAptos} | {error}')
                break
            print(f'{pa_bridge.addressAptos} | слишком низкое FEE, повышаю')
    else:
        print(f'{pa_bridge.addressAptos} | FEE достигла предела')


if __name__ == '__main__':
    file = 'accounts.tsv'
    network = 'MATIC'
    percent = 10
    min_native_fee = 0.004
    max_native_fee = 0.006
    fee_steps = get_fee_steps(0.04, 0.06)
    client = RestClient(NODE_URL)
    client.client_config.max_gas_amount = 250
    with open(file, "r") as f:
        keys_list = [row.strip() for row in f]
    for private_key in keys_list:
        bridge(private_key, percent, fee_steps)
