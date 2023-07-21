"""init

Revision ID: 0001
Revises: 
Create Date: 2023-07-20 15:41:14.477844

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
    op.create_table('StarknetAccountDeploy',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('addressETH', sa.String(), nullable=True),
    sa.Column('amount', sa.Float(), nullable=False),
    sa.Column('addressStark', sa.String(), nullable=False),
    sa.Column('privateKey', sa.String(), nullable=False),
    sa.Column('phrase', sa.String(), nullable=False),
    sa.Column('deployed', sa.Boolean(), nullable=False),
    sa.Column('creationDate', sa.DateTime(), nullable=True),
    sa.PrimaryKeyConstraint('id')
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table('StarknetAccountDeploy')
    # ### end Alembic commands ###
