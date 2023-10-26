import csv
import os
import typing
from dataclasses import dataclass, field

from database.other.models import Account

if typing.TYPE_CHECKING:
    from services.steps import Step


@dataclass
class Wallet:
    address: str
    private_key: str
    steps: list['Step'] = field(default_factory=list)
    used_protocols: list = field(default_factory=list)


class AccountParser:
    """
    Credential parsing from file and Account table
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def get_wallets(self):
        self.validate_file()
        with open(self.file_path) as f:
            reader = csv.reader(f, delimiter='\t')
            lines = [a for a in reader]
        return [Wallet(a[0], Account.get_private_key(a[0])) for a in lines]

    def validate_file(self):
        f = self.file_path
        if not os.path.isfile(f):
            raise ValueError(f'Файл не найден. {f}')
        if not f.endswith('.tsv') and not f.endswith('.csv'):
            raise ValueError(f'Формат файла должен быть tsv или csv {f}')
