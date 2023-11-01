from datetime import datetime

from sqlalchemy import DateTime, select, func, ForeignKey, desc
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models import MethodManager
from settings.config import PROJECT
from database.db import Base, session


class Account(Base):
    __tablename__ = 'Accounts'

    address: Mapped[str] = mapped_column(primary_key=True, nullable=False)
    private_key: Mapped[str] = mapped_column(nullable=False)
    seed_phrase: Mapped[str] = mapped_column(nullable=True)
    okxERC20: Mapped[str]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        default=datetime.utcnow
    )

    @classmethod
    def get_private_key(cls, address):
        stmt = select(cls).filter(func.lower(cls.address) == address.lower())
        result = session.scalars(stmt).first()
        if not result:
            raise ValueError(f'Private key for {address} is not found')
        return session.scalars(stmt).first().private_key


class ProxySettings(Base):
    __tablename__ = 'ProxySettings'
    id: Mapped[int] = mapped_column(primary_key=True)
    project: Mapped[str] = mapped_column(unique=True, nullable=True)
    retries: Mapped[int]
    retry_delay: Mapped[int]
    max_addresses_per_proxy: Mapped[int] = mapped_column(default=1, server_default='1')

    def __repr__(self):
        return f'Попыток: {self.retries}, Задержка: {self.retry_delay}'

    @classmethod
    def get_last(cls):
        stmt = select(cls).filter_by(project=PROJECT)
        result = session.scalars(stmt).first()
        if not result:
            raise ValueError(f'Proxy Settings is not found for project {PROJECT}')
        return result


class Proxy(Base):
    __tablename__ = 'Proxy'
    id: Mapped[int] = mapped_column(primary_key=True)
    host: Mapped[str]
    port: Mapped[str]
    username: Mapped[str]
    password: Mapped[str]
    alive: Mapped[bool] = mapped_column(default=True)
    lastUsing = mapped_column(DateTime, onupdate=datetime.utcnow)
    creationDate = mapped_column(DateTime, default=datetime.utcnow,
                                 server_default=func.now())

    def __repr__(self):
        return self.address

    @property
    def address(self):
        return f'http://{self.username}:{self.password}@{self.host}:{self.port}'

    @classmethod
    def get_proxy(cls, address):
        # ищем прокси которые уже исопльзовались на этом аддрессе
        used_by_address_q = select(cls).distinct().join(cls.addressproxies).filter(
            AddressProxy.address == address
        ).order_by(desc(cls.alive))
        used_by_address = session.execute(used_by_address_q).scalars().all()
        # ищем прокси которые ниразу в проекте не использовались
        address_proxy = select(AddressProxy.proxy_id).filter_by(settings_project=PROJECT)
        not_used_in_project_q = (
            select(cls).filter(cls.id.not_in(address_proxy), cls.alive == True)
        )
        not_used_in_project = session.execute(
            not_used_in_project_q).scalars().all()
        # ищем прокси которые использовались меньше раз на проекте, чем задано в настройках
        max_count = (select(ProxySettings.max_addresses_per_proxy)
                     .filter_by(project=PROJECT).scalar_subquery())
        used_by_another_address_q = (
            select(cls)
            .outerjoin(cls.addressproxies)
            .filter(
                AddressProxy.settings_project == PROJECT,
                cls.alive == True,
            )
            .group_by(cls.id).having(func.count() < max_count)
            .order_by(func.count())
        )
        used_by_another_address = session.execute(used_by_another_address_q).scalars().all()
        used_by_another_address = [
            p for p in used_by_another_address if p not in used_by_address
        ]
        # объединяем все запросы по порядку вызова
        used_by_address.extend(not_used_in_project)
        used_by_address.extend(used_by_another_address)
        return used_by_address

    def update_success_proxy(self, address: str):
        self.lastUsing = datetime.utcnow()
        if not list(filter(
            lambda x: x.settings_project == PROJECT
                and x.proxy_id == self.id
                and x.address == address,
                self.addressproxies
        )):
            AddressProxy.create(
                address=address,
                proxy_id=self.id,
                settings_project=PROJECT
            )
        session.commit()

    def update_last_using(self):
        self.lastUsing = datetime.utcnow()
        session.commit()


class Project(Base):
    __tablename__ = 'Project'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    maxProxyPerAddress: Mapped[int] = mapped_column(default=1)

    def __repr__(self):
        return self.name


class AddressProxy(Base):
    __tablename__ = 'AddressProxy'
    id: Mapped[int] = mapped_column(primary_key=True)
    address: Mapped[str] = mapped_column(index=True, nullable=True)
    proxy_id: Mapped[int] = mapped_column(ForeignKey('Proxy.id'))
    proxy: Mapped[Proxy] = relationship(backref='addressproxies')
    settings_project: Mapped[int] = mapped_column(ForeignKey('ProxySettings.project'))
    settings: Mapped[ProxySettings] = relationship(backref='addressproxies')

    def __repr__(self):
        return f'{self.id}. {self.address} - {self.proxy}'

    @classmethod
    def create(cls, **kwargs):
        obj = cls(**kwargs)
        session.add(obj)
        session.commit()
        return obj


class BinanceWithdrawal(MethodManager):
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
