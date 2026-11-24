"""Initial database

Revision ID: 512f8f09c954
Revises: 
Create Date: 2026-11-24 15:21:57.231107

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '512f8f09c954'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('username', sa.String(length=64), nullable=False),
    sa.Column('email', sa.String(length=120), nullable=False),
    sa.Column('password_hash', sa.String(length=256), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_username'), ['username'], unique=True)

    op.create_table('events',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('title', sa.String(length=150), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('location', sa.String(length=200), nullable=False),
    sa.Column('start_at', sa.DateTime(), nullable=False),
    sa.Column('end_at', sa.DateTime(), nullable=False),
    sa.Column('capacity', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('organizer_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['organizer_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_events_organizer_id'), ['organizer_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_events_start_at'), ['start_at'], unique=False)

    op.create_table('discount_codes',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=32), nullable=False),
    sa.Column('percent', sa.Integer(), nullable=False),
    sa.Column('max_uses', sa.Integer(), nullable=False),
    sa.Column('used_count', sa.Integer(), nullable=False),
    sa.Column('expires_at', sa.DateTime(), nullable=True),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.CheckConstraint('percent BETWEEN 1 AND 100', name='ck_discount_percent'),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('discount_codes', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_discount_codes_code'), ['code'], unique=True)
        batch_op.create_index(batch_op.f('ix_discount_codes_event_id'), ['event_id'], unique=False)

    op.create_table('ticket_types',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=50), nullable=False),
    sa.Column('price', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('quantity', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('ticket_types', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_ticket_types_event_id'), ['event_id'], unique=False)

    op.create_table('orders',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('subtotal', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('discount_amount', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('total', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('event_id', sa.Integer(), nullable=False),
    sa.Column('discount_code_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['discount_code_id'], ['discount_codes.id'], ),
    sa.ForeignKeyConstraint(['event_id'], ['events.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_orders_event_id'), ['event_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_orders_user_id'), ['user_id'], unique=False)

    op.create_table('tickets',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('code', sa.String(length=64), nullable=False),
    sa.Column('checked_in_at', sa.DateTime(), nullable=True),
    sa.Column('order_id', sa.Integer(), nullable=False),
    sa.Column('ticket_type_id', sa.Integer(), nullable=False),
    sa.Column('checked_in_by_id', sa.Integer(), nullable=True),
    sa.ForeignKeyConstraint(['checked_in_by_id'], ['users.id'], ),
    sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ),
    sa.ForeignKeyConstraint(['ticket_type_id'], ['ticket_types.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_tickets_code'), ['code'], unique=True)
        batch_op.create_index(batch_op.f('ix_tickets_order_id'), ['order_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_tickets_ticket_type_id'), ['ticket_type_id'], unique=False)


def downgrade():
    with op.batch_alter_table('tickets', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_tickets_ticket_type_id'))
        batch_op.drop_index(batch_op.f('ix_tickets_order_id'))
        batch_op.drop_index(batch_op.f('ix_tickets_code'))

    op.drop_table('tickets')
    with op.batch_alter_table('orders', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_orders_user_id'))
        batch_op.drop_index(batch_op.f('ix_orders_event_id'))

    op.drop_table('orders')
    with op.batch_alter_table('ticket_types', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_ticket_types_event_id'))

    op.drop_table('ticket_types')
    with op.batch_alter_table('discount_codes', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_discount_codes_event_id'))
        batch_op.drop_index(batch_op.f('ix_discount_codes_code'))

    op.drop_table('discount_codes')
    with op.batch_alter_table('events', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_events_start_at'))
        batch_op.drop_index(batch_op.f('ix_events_organizer_id'))

    op.drop_table('events')
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_username'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
