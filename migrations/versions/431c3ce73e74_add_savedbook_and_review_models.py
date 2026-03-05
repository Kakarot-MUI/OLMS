"""Add SavedBook and Review models

Revision ID: 431c3ce73e74
Revises: 7bb7c26360cc
Create Date: 2026-03-05 20:24:56.788827

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '431c3ce73e74'
down_revision = '7bb7c26360cc'
branch_labels = None
depends_on = None


def upgrade():
    # Create saved_books table
    op.create_table('saved_books',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('book_id', sa.Integer(), nullable=False),
    sa.Column('saved_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'book_id', name='uq_user_saved_book')
    )
    with op.batch_alter_table('saved_books', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_saved_books_book_id'), ['book_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_saved_books_user_id'), ['user_id'], unique=False)

    # Create reviews table
    op.create_table('reviews',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('book_id', sa.Integer(), nullable=False),
    sa.Column('rating', sa.Integer(), nullable=False),
    sa.Column('content', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['book_id'], ['books.id'], ),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'book_id', name='uq_user_book_review')
    )
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_reviews_book_id'), ['book_id'], unique=False)
        batch_op.create_index(batch_op.f('ix_reviews_user_id'), ['user_id'], unique=False)


def downgrade():
    with op.batch_alter_table('reviews', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_reviews_user_id'))
        batch_op.drop_index(batch_op.f('ix_reviews_book_id'))
    op.drop_table('reviews')
    
    with op.batch_alter_table('saved_books', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_saved_books_user_id'))
        batch_op.drop_index(batch_op.f('ix_saved_books_book_id'))
    op.drop_table('saved_books')
