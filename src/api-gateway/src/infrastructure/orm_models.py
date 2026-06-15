from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, Enum as SQLEnum, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from infrastructure.database import Base
from domain.entities import EnrollmentStatus
from sqlalchemy_utils import LtreeType, Ltree
from uuid6 import uuid7
import enum

class UserRole(enum.Enum):
    ADMIN = "admin"
    FACULTY = "faculty"
    STUDENT = "student"

class TenantType(enum.Enum):
    UNIVERSITY = "university"
    DEPARTMENT = "department"
    COURSE = "course"

class TenantORM(Base):
    __tablename__ = "tenants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    name = Column(String, nullable=False)
    type = Column(SQLEnum(TenantType), nullable=False)
    path = Column(LtreeType, nullable=False, unique=True, index=True) # e.g., 'stanford', 'stanford.cs'
    compute_credits = Column(Float, default=1000.0) # Relevant for root tenants
    subscription_tier = Column(String, default="Basic") 

    users = relationship("UserORM", back_populates="tenant")

class UserORM(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    email = Column(String, nullable=False, unique=True)
    role = Column(SQLEnum(UserRole), nullable=False)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    tenant_path = Column(LtreeType, nullable=False, index=True) # Copied from tenant for efficient hierarchical querying

    tenant = relationship("TenantORM", back_populates="users")

class CourseOfferingORM(Base):
    __tablename__ = "course_offerings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    course_catalog_id = Column(UUID(as_uuid=True), nullable=False, default=uuid7)
    semester_id = Column(UUID(as_uuid=True), nullable=False, default=uuid7)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False) # Represents the course tenant node
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    section_number = Column(String, nullable=False)
    max_capacity = Column(Integer, nullable=False)

    faculty = relationship("UserORM")
    tenant = relationship("TenantORM")

class EnrollmentORM(Base):
    __tablename__ = "enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    course_offering_id = Column(UUID(as_uuid=True), ForeignKey("course_offerings.id"), nullable=False)
    status = Column(SQLEnum(EnrollmentStatus), nullable=False)
    enrollment_date = Column(DateTime(timezone=True), nullable=False)
    dropped_date = Column(DateTime(timezone=True), nullable=True)

    student = relationship("UserORM")
    course_offering = relationship("CourseOfferingORM")

class PodCatalogORM(Base):
    __tablename__ = "pod_catalog"

    id = Column(String, primary_key=True) # e.g., "cpp-basic", "python-ds"
    name = Column(String, nullable=False) # e.g., "C++ Basic Sandbox"
    docker_image = Column(String, nullable=False) # e.g., "polyglot-cpp-engine:latest"
    language = Column(String, nullable=False)
    is_gui = Column(Boolean, default=False)
    base_cost = Column(Float, default=0.0) # Cost in compute credits
    
    # Custom Pod Architecture Fields
    custom_env_id = Column(String, nullable=True) # To identify it as a custom extension
    owner_faculty_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    custom_init_script = Column(String, nullable=True)

    owner_faculty = relationship("UserORM")

class TenantEnabledPodsORM(Base):
    __tablename__ = "tenant_enabled_pods"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_path = Column(LtreeType, nullable=False, index=True) # Allows inheritance queries using LTree @> operator
    pod_id = Column(String, ForeignKey("pod_catalog.id"), nullable=False)
    
    pod = relationship("PodCatalogORM")