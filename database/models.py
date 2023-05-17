from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base, session


class PolygonAptosBridge(Base):
    __tablename__ = 'PolygonAptosBridge'
    id: Mapped[int] = mapped_column(primary_key=True)
    addressPolygon: Mapped[str] = mapped_column(index=True)
    privateKeyPolygon: Mapped[str] = mapped_column(nullable=True)
    addressAptos: Mapped[str] = mapped_column(index=True)
    privateKeyAptos: Mapped[str]
    currency: Mapped[str] = mapped_column(default='USDC')
    amount: Mapped[float] = mapped_column(default=0)
    claimed: Mapped[bool] = mapped_column(default=False)
    polygon_txn: Mapped[str] = mapped_column(nullable=True)
    creationDate = mapped_column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return f"Bridge MATIC > APT {self.currency}: {self.addressPolygon} -> {self.addressAptos}"

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj

    def set_polygon_txn(self, txn):
        self.polygon_txn = txn
        session.commit()

    def set_amount(self, amount):
        self.amount = amount
        session.commit()

    def claim(self):
        self.claimed = True
        session.commit()

    @classmethod
    def get_by_polygon_address(cls, address, claimed=False, amount=None):
        if amount:
            return session.query(cls) \
                .filter(func.lower(cls.addressPolygon) == func.lower(address),
                        cls.claimed == claimed, cls.amount != 0).first()
        else:
            return session.query(cls) \
                .filter(func.lower(cls.addressPolygon) == func.lower(address),
                    cls.claimed == claimed).first()


class AptosPolygonBridge(Base):
    __tablename__ = 'AptosPolygonBridge'
    id: Mapped[int] = mapped_column(primary_key=True)
    addressAptos: Mapped[str] = mapped_column(index=True)
    privateKeyAptos: Mapped[str] = mapped_column(nullable=True)
    addressPolygon: Mapped[str] = mapped_column(index=True)
    privateKeyPolygon: Mapped[str]
    currency: Mapped[str] = mapped_column(default='USDC')
    amount: Mapped[float] = mapped_column(default=0)
    aptos_txn: Mapped[str] = mapped_column(nullable=True)
    creationDate = mapped_column(DateTime, default=datetime.utcnow())

    def __repr__(self):
        return f"Bridge APT > MATIC. {self.currency}: {self.addressAptos} -> {self.addressPolygon}"

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj
