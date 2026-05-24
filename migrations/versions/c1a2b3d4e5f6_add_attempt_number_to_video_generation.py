"""add attempt_number to video_generation

Revision ID: c1a2b3d4e5f6
Revises: 4e8200be169b
Create Date: 2026-05-24 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c1a2b3d4e5f6'
down_revision = '4e8200be169b'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('video_generation') as batch_op:
        batch_op.add_column(sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'))

    # Backfill: assign attempt_number per scene by created_at order
    conn = op.get_bind()
    rows = conn.execute(sa.text(
        "SELECT id, scene_id FROM video_generation ORDER BY scene_id, created_at, id"
    )).fetchall()
    counters = {}
    for row in rows:
        gen_id, scene_id = row[0], row[1]
        counters[scene_id] = counters.get(scene_id, 0) + 1
        conn.execute(
            sa.text("UPDATE video_generation SET attempt_number = :n WHERE id = :id"),
            {"n": counters[scene_id], "id": gen_id},
        )

    # Drop server_default so future inserts must specify (matches model default at app layer)
    with op.batch_alter_table('video_generation') as batch_op:
        batch_op.alter_column('attempt_number', server_default=None)


def downgrade():
    with op.batch_alter_table('video_generation') as batch_op:
        batch_op.drop_column('attempt_number')
