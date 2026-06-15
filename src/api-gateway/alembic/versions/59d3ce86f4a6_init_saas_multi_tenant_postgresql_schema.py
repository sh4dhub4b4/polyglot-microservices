"""Init SaaS Multi-tenant PostgreSQL Schema

Revision ID: 59d3ce86f4a6
Revises: 
Create Date: 2026-06-12 02:54:06.283044

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import sqlalchemy_utils

# revision identifiers, used by Alembic.
revision: str = '59d3ce86f4a6'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # Extensions for UUID and LTree
    op.execute('CREATE EXTENSION IF NOT EXISTS "ltree";')

    # Enums
    user_role_enum = postgresql.ENUM('ADMIN', 'FACULTY', 'STUDENT', name='userrole')
    tenant_type_enum = postgresql.ENUM('UNIVERSITY', 'DEPARTMENT', 'COURSE', name='tenanttype')
    enrollment_status_enum = postgresql.ENUM('ACTIVE', 'DROPPED', 'COMPLETED', name='enrollmentstatus')

    user_role_enum.create(op.get_bind(), checkfirst=True)
    tenant_type_enum.create(op.get_bind(), checkfirst=True)
    enrollment_status_enum.create(op.get_bind(), checkfirst=True)

    # 1. Tenants
    op.create_table(
        'tenants',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('type', tenant_type_enum, nullable=False),
        sa.Column('path', sqlalchemy_utils.types.ltree.LtreeType(), nullable=False),
        sa.Column('compute_credits', sa.Float(), nullable=True),
        sa.Column('subscription_tier', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenants_path'), 'tenants', ['path'], unique=True)
    
    # Enable GIST index for fast ltree queries
    op.execute("CREATE INDEX ix_tenants_path_gist ON tenants USING GIST (path);")

    # 2. Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('role', user_role_enum, nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_path', sqlalchemy_utils.types.ltree.LtreeType(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email')
    )
    op.create_index(op.f('ix_users_tenant_path'), 'users', ['tenant_path'], unique=False)
    op.execute("CREATE INDEX ix_users_tenant_path_gist ON users USING GIST (tenant_path);")

    # 3. Course Offerings
    op.create_table(
        'course_offerings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_catalog_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('semester_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('faculty_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('section_number', sa.String(), nullable=False),
        sa.Column('max_capacity', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['faculty_id'], ['users.id']),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 4. Enrollments
    op.create_table(
        'enrollments',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('course_offering_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('status', enrollment_status_enum, nullable=False),
        sa.Column('enrollment_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dropped_date', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['course_offering_id'], ['course_offerings.id']),
        sa.ForeignKeyConstraint(['student_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 5. Pod Catalog
    op.create_table(
        'pod_catalog',
        sa.Column('id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('docker_image', sa.String(), nullable=False),
        sa.Column('language', sa.String(), nullable=False),
        sa.Column('is_gui', sa.Boolean(), nullable=True),
        sa.Column('base_cost', sa.Float(), nullable=True),
        sa.Column('custom_env_id', sa.String(), nullable=True),
        sa.Column('owner_faculty_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('custom_init_script', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['owner_faculty_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # 6. Tenant Enabled Pods
    op.create_table(
        'tenant_enabled_pods',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_path', sqlalchemy_utils.types.ltree.LtreeType(), nullable=False),
        sa.Column('pod_id', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(['pod_id'], ['pod_catalog.id']),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_tenant_enabled_pods_path'), 'tenant_enabled_pods', ['tenant_path'], unique=False)
    op.execute("CREATE INDEX ix_tenant_enabled_pods_path_gist ON tenant_enabled_pods USING GIST (tenant_path);")

def downgrade() -> None:
    # Drop indices
    op.execute("DROP INDEX IF EXISTS ix_tenant_enabled_pods_path_gist;")
    op.execute("DROP INDEX IF EXISTS ix_users_tenant_path_gist;")
    op.execute("DROP INDEX IF EXISTS ix_tenants_path_gist;")
    
    op.drop_index(op.f('ix_tenant_enabled_pods_path'), table_name='tenant_enabled_pods')
    op.drop_index(op.f('ix_users_tenant_path'), table_name='users')
    op.drop_index(op.f('ix_tenants_path'), table_name='tenants')
    
    # Drop tables
    op.drop_table('tenant_enabled_pods')
    op.drop_table('pod_catalog')
    op.drop_table('enrollments')
    op.drop_table('course_offerings')
    op.drop_table('users')
    op.drop_table('tenants')

    # Drop enums
    postgresql.ENUM(name='enrollmentstatus').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='tenanttype').drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name='userrole').drop(op.get_bind(), checkfirst=True)
