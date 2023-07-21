from datetime import datetime

from sqlalchemy import DateTime, select, func, update
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base, session


class ZkSyncProxyLog(Base):
    __tablename__ = 'ZkSyncProxyLog'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(index=True)
    host: Mapped[str]
    port: Mapped[str]
    username: Mapped[str]
    password: Mapped[str]
    alive: Mapped[bool] = mapped_column(default=True)
    creationDate = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Прокси для {self.address}"

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj

    @classmethod
    def get_proxy(cls, address):
        query = select(cls).filter(
            func.lower(cls.address) == address.lower(),
            cls.alive == True,
        )
        result = session.execute(query).scalars().first()
        return result

    @classmethod
    def get_proxy_str(cls, address):
        proxy = cls.get_proxy(address)
        if proxy:
            return f'http://{proxy.username}:{proxy.password}@{proxy.host}:{proxy.port}'

    @classmethod
    def kill_proxy(cls, proxy_str: str):
        """
        Ставим alive = False для прокси.
        прокси должно быть вида: f'http://username:password@host:port'
        """
        start_index = proxy_str.find("@")
        host_and_port = proxy_str[start_index + 1:]
        delimiter_host_port = host_and_port.find(":")
        host = host_and_port[:delimiter_host_port]
        port = host_and_port[delimiter_host_port + 1:]

        query = update(cls).where(
            cls.host == host,
            cls.port == port,
            cls.alive == True,
        ).values(alive=False)
        session.execute(query)
        session.commit()


class BinanceWithdrawal(Base):
    __tablename__ = 'BinanceWithdrawals'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(index=True)
    privateKey: Mapped[str] = mapped_column(nullable=True)
    network: Mapped[str]
    currency: Mapped[str]
    amount: Mapped[float] = mapped_column(default=0)
    creationDate = mapped_column(DateTime, default=datetime.utcnow())
    binance_id: Mapped[str]

    def __repr__(self):
        return f"Кошелек {self.address}"

    @classmethod
    def get_by_addresses(cls, addresses):
        """
        Фильтруем строки по адресу, в которых есть приватный ключ. Адреса уникальные
        """
        query = select(BinanceWithdrawal).filter(
            BinanceWithdrawal.address.in_(addresses),
            BinanceWithdrawal.privateKey != None,
            BinanceWithdrawal.privateKey != '',
        ).distinct(BinanceWithdrawal.address)
        accounts = session.execute(query).scalars().all()
        return accounts
