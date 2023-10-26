from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base, session


class MethodManager:
    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj


class ScrollCombine(Base, MethodManager):
    __tablename__ = 'ScrollCombine'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(index=True)
    protocol: Mapped[str]
    srcCurrency: Mapped[str] = mapped_column(nullable=True)
    dstCurrency: Mapped[str] = mapped_column(nullable=True)
    srcAmount: Mapped[float] = mapped_column(nullable=True)
    dstAmount: Mapped[float] = mapped_column(nullable=True)
    txnHash: Mapped[str] = mapped_column(nullable=True)
    fee: Mapped[float] = mapped_column(nullable=True)
    approvedFor: Mapped[str] = mapped_column(nullable=True)
    creationDate = mapped_column(
        DateTime(timezone=True), default=datetime.now, server_default=func.now()
    )

    def __repr__(self):
        return f"Активность {self.address} на {self.protocol}"
