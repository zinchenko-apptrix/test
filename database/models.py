from datetime import datetime

from sqlalchemy import DateTime, update
from sqlalchemy.orm import Mapped, mapped_column

from database.db import Base, session


class StarknetAccountDeploy(Base):
    __tablename__ = 'StarknetAccountDeploy'
    id: Mapped[int] = mapped_column(primary_key=True)
    addressETH: Mapped[str] = mapped_column(nullable=True)
    amount: Mapped[float] = mapped_column(default=0)
    addressStark: Mapped[str]
    privateKey: Mapped[str]
    phrase: Mapped[str]
    deployed: Mapped[bool] = mapped_column(default=False)
    creationDate = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"Деплой Starknet аккаунта {self.address}"

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj

    @classmethod
    def update(cls, address_stark, **kwargs):
        query = update(cls).where(cls.addressStark == address_stark)
        query = query.values(**kwargs)
        session.execute(query)
        session.commit()
