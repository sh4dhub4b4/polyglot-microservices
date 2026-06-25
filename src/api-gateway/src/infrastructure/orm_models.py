from sqlalchemy import Column, String, Integer, DateTime, Boolean, Float, Enum as SQLEnum, ForeignKey, Text
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
    display_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)
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

# ──────────────────────────────────────────
# Academic Layer (Google Classroom Equivalent)
# ──────────────────────────────────────────

class AssignmentStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CLOSED = "closed"

class SubmissionStatus(enum.Enum):
    SUBMITTED = "submitted"
    GRADED = "graded"
    LATE = "late"
    RESUBMITTED = "resubmitted"

class AssignmentORM(Base):
    """Teacher posts an assignment to a course offering."""
    __tablename__ = "assignments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    course_offering_id = Column(UUID(as_uuid=True), ForeignKey("course_offerings.id"), nullable=False)
    created_by_faculty_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(300), nullable=False)
    description = Column(Text, nullable=True)
    allowed_pod_id = Column(String, ForeignKey("pod_catalog.id"), nullable=True)  # restrict env type
    max_marks = Column(Float, default=100.0)
    due_date = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(AssignmentStatus), nullable=False, default=AssignmentStatus.DRAFT)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")
    updated_at = Column(DateTime(timezone=True), nullable=True)
    # Hidden test cases stored as JSON string: [{"stdin": "1 2", "expected_stdout": "3"}]
    hidden_test_cases = Column(Text, nullable=True)

    course_offering = relationship("CourseOfferingORM")
    faculty = relationship("UserORM", foreign_keys=[created_by_faculty_id])
    allowed_pod = relationship("PodCatalogORM")
    submissions = relationship("SubmissionORM", back_populates="assignment")

class SubmissionORM(Base):
    """Student submits code for an assignment. Stores latest attempt and auto-grader result."""
    __tablename__ = "submissions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    assignment_id = Column(UUID(as_uuid=True), ForeignKey("assignments.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    source_code = Column(Text, nullable=False)
    language = Column(String(50), nullable=False)
    status = Column(SQLEnum(SubmissionStatus), nullable=False, default=SubmissionStatus.SUBMITTED)
    submitted_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")
    # Auto-grader results
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    tests_passed = Column(Integer, default=0)
    tests_total = Column(Integer, default=0)
    marks_awarded = Column(Float, nullable=True)
    grader_feedback = Column(Text, nullable=True)

    assignment = relationship("AssignmentORM", back_populates="submissions")
    student = relationship("UserORM")

# ──────────────────────────────────────────
# Billing Layer (Compute Credits Tracking)
# ──────────────────────────────────────────

class BillingTransactionORM(Base):
    """Records every deduction of compute credits per execution."""
    __tablename__ = "billing_transactions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid7)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    task_id = Column(String, nullable=False)  # ws task_id for traceability
    pod_id = Column(String, nullable=True)
    credits_deducted = Column(Float, nullable=False)
    execution_time_ms = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default="now()")

    tenant = relationship("TenantORM")
    student = relationship("UserORM")