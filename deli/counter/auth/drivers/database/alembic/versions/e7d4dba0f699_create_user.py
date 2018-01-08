"""create builtin user

Revision ID: e7d4dba0f699
Revises:
Create Date: 2017-12-02 18:13:36.109525

"""
import sqlalchemy as sa
import sqlalchemy_utils as sau
from alembic import op

# revision identifiers, used by Alembic.
revision = 'e7d4dba0f699'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'users',
        sa.Column('id', sa.Integer, autoincrement=True, primary_key=True),
        sa.Column('username', sa.String, nullable=False, unique=True),
        sa.Column('password', sau.PasswordType(schemes=['bcrypt']), nullable=False),
        sa.Column('created_at', sau.ArrowType(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sau.ArrowType(timezone=True), nullable=False)
    )
    op.create_table(
        'user_roles',
        sa.Column('id', sa.Integer, autoincrement=True, primary_key=True),
        sa.Column('user_id', sa.Integer, sa.ForeignKey('users.id'), nullable=False, index=True),
        sa.Column('role', sa.String, nullable=False),
        sa.Column('created_at', sau.ArrowType(timezone=True), nullable=False, index=True),
        sa.Column('updated_at', sau.ArrowType(timezone=True), nullable=False)
    )


def downgrade():
    op.drop_table('user_roles')
    op.drop_table('users')
