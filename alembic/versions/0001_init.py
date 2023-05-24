"""init

Revision ID: 0001
Revises: 
Create Date: 2023-05-24 12:43:14.556199

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table('BitcoinBridgeTraderJoeSwap',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('address', sa.String(), nullable=False),
        sa.Column('privateKey', sa.String(), nullable=True),
        sa.Column('currency_in', sa.String(), nullable=False),
        sa.Column('currency_out', sa.String(), nullable=False),
        sa.Column('amount_in', sa.Float(), nullable=True),
        sa.Column('amount_out', sa.Float(), nullable=True),
        sa.Column('creationDate', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_BitcoinBridgeTraderJoeSwap_address'), 'BitcoinBridgeTraderJoeSwap', ['address'], unique=False)
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_index(op.f('ix_BitcoinBridgeTraderJoeSwap_address'), table_name='BitcoinBridgeTraderJoeSwap')
    op.drop_table('BitcoinBridgeTraderJoeSwap')
    # ### end Alembic commands ###
