"""add habit schedule history

Revision ID: 1e13956fc4cb
Revises: 1d556e199898
Create Date: 2026-11-04 16:08:48.023469

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone
import uuid



revision = '1e13956fc4cb'
down_revision = '1d556e199898'
branch_labels = None
depends_on = None


def upgrade():

    op.create_table('habit_schedule_versions',
    sa.Column('habit_id', sa.String(length=36), nullable=False),
    sa.Column('effective_from', sa.Date(), nullable=False),
    sa.Column('schedule_mask', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.ForeignKeyConstraint(['habit_id'], ['habits.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('habit_id', 'effective_from', name='uq_habit_schedule_effective_from')
    )
    with op.batch_alter_table('habit_schedule_versions', schema=None) as batch_op:
        batch_op.create_index('ix_habit_schedule_habit_effective', ['habit_id', 'effective_from'], unique=False)

    bind = op.get_bind()

    habits = sa.table(
        "habits",
        sa.column("id", sa.String(length=36)),
        sa.column("start_date", sa.Date()),
        sa.column("schedule_mask", sa.Integer()),
    )

    versions = sa.table(
        "habit_schedule_versions",
        sa.column("id", sa.String(length=36)),
        sa.column("habit_id", sa.String(length=36)),
        sa.column("effective_from", sa.Date()),
        sa.column("schedule_mask", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
    )

    existing_habits = bind.execute(
        sa.select(
            habits.c.id,
            habits.c.start_date,
            habits.c.schedule_mask,
        )
    ).mappings().all()

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    for habit in existing_habits:
        bind.execute(
            versions.insert().values(
                id=str(uuid.uuid4()),
                habit_id=habit["id"],
                effective_from=habit["start_date"],
                schedule_mask=habit["schedule_mask"],
                created_at=now,
            )
        )




def downgrade():

    with op.batch_alter_table('habit_schedule_versions', schema=None) as batch_op:
        batch_op.drop_index('ix_habit_schedule_habit_effective')

    op.drop_table('habit_schedule_versions')
