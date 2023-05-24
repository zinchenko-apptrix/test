from datetime import datetime


from sqlalchemy import DateTime, select
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base, session


class TraderJoeSwap(Base):
    __tablename__ = 'BitcoinBridgeTraderJoeSwap'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(index=True)
    privateKey: Mapped[str] = mapped_column(nullable=True)
    currency_in: Mapped[str] = mapped_column(default='AVAX')
    currency_out: Mapped[str] = mapped_column(default='BTC.b')
    amount_in: Mapped[float] = mapped_column(nullable=True)
    amount_out: Mapped[float] = mapped_column(nullable=True)
    creationDate = mapped_column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return self.address

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj

    @classmethod
    def get_by_addresses(cls, addresses):
        """
        Фильтруем строки по адресу, в которых есть приватный ключ. Адреса уникальные
        """
        query = select(cls).filter(
            cls.address.in_(addresses),
            cls.privateKey != None,
            cls.privateKey != '',
        ).distinct(cls.address)
        accounts = session.execute(query).scalars().all()
        return accounts


class BitcoinBridgeSwap(Base):
    __tablename__ = 'BitcoinBridgeSwap'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(index=True)
    privateKey: Mapped[str] = mapped_column(nullable=True)
    src: Mapped[str] = mapped_column(nullable=True)
    dst: Mapped[str] = mapped_column(nullable=True)
    amount: Mapped[float] = mapped_column(nullable=True)
    creationDate = mapped_column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return f"Мост {self.address} {self.src} -> {self.dst} "

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj
