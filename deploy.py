import argparse
from random import randint
from time import sleep
from typing import List

from starknet_py.net.gateway_client import GatewayClient
from starknet_py.net.signer.stark_curve_signer import KeyPair

from database.models import StarknetAccountDeploy
from services import (
    CLASS_HASH_PROXY,
    CLIENT,
    CHAIN,
    CLASS_HASH_ACCOUNT,
    IMPLEMENT_FUNC,
    logger,
)
from starknet_py.net.account.account import Account as StarkAccount


def parse_args():
    """Парсинг параметров переданных в терминале в скрипт"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--max-fee-deploy',
        help='Максимальная комиссия за деплой аккаунта starknet, wei',
        default=2000000000000000,
        type=int,
    )
    parser.add_argument(
        '--min-delay',
        help='Минимальная задержка между переводами, с',
        type=int,
        default=1,
    )
    parser.add_argument(
        '--max-delay',
        help='Максимальная задержка между переводами, с',
        type=int,
        default=5,
    )
    args = parser.parse_args()
    return (
        args.max_fee_deploy,
        args.min_delay,
        args.max_delay,
    )


class Deployer:
    def __init__(self, address: int, private_key: int, max_fee: int):
        self.address = address
        self.max_fee = max_fee
        self.key_pair = KeyPair.from_private_key(private_key)

    def deploy(self):
        logger.info(f'{self.address} Deploying account')
        call_data = self.get_call_data()
        result = StarkAccount.deploy_account_sync(
            address=self.address,
            class_hash=CLASS_HASH_PROXY,
            salt=self.key_pair.public_key,
            key_pair=self.key_pair,
            client=GatewayClient(CLIENT),
            chain=CHAIN,
            constructor_calldata=call_data,
            max_fee=self.max_fee,
        )
        result.wait_for_acceptance_sync()
        logger.info(f'{self.address} || Account deployed')
        self.save_db()

    def save_db(self):
        StarknetAccountDeploy.update(
            address_stark=hex(self.address),
            deployed=True
        )

    def get_call_data(self) -> List:
        return [
            int(CLASS_HASH_ACCOUNT),
            IMPLEMENT_FUNC,
            2,
            self.key_pair.public_key,
            0,
        ]


def deploy_stark_account(address: str, stark_key: str, max_fee_deploy: int):
    try:
        deployer = Deployer(
            address=int(address, 16),
            private_key=int(stark_key, 16),
            max_fee=max_fee_deploy
        )
        deployer.deploy()
        return True
    except BaseException as error:
        logger.error(f'{address} deploy error: {error}')


if __name__ == '__main__':
    max_fee_deploy, min_delay, max_delay = parse_args()
    accounts = StarknetAccountDeploy.get_not_deployed()
    for acc in accounts:
        result = deploy_stark_account(
            acc.addressStark,
            acc.privateKey,
            max_fee_deploy,
        )
        if result:
            sleep(randint(min_delay, max_delay))
