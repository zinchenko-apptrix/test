from datetime import datetime

from sqlalchemy import DateTime, select
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base, session


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
