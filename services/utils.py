from datetime import datetime, timedelta


def eth_to_wei(amount):
    return int(amount * 10**18)


def wei_to_eth(amount):
    return amount / 10**18


def get_timestamp() -> int:
    now = datetime.now()
    delta = timedelta(minutes=10)
    result = now + delta
    return int(result.timestamp())
