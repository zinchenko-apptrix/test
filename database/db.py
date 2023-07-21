import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

user = os.getenv("POSTGRES_USER")
password = os.getenv("POSTGRES_PASSWORD")
host = os.getenv("POSTGRES_HOST")
port = os.getenv("POSTGRES_PORT")
db = os.getenv("POSTGRES_DB")
ssl_cert = os.getenv("SSL_CERT")
ssl_key = os.getenv("SSL_KEY")

engine = create_engine(
    f'postgresql+psycopg2://{user}:{password}@{host}/{db}',
    connect_args={'sslcert': ssl_cert, 'sslkey': ssl_key}
)
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()
