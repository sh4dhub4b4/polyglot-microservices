from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from infrastructure.database import Base
from domain.entities import EnrollmentStatus
import uuid

class CourseOfferingORM(Base):
    __tablename__ = "course_offerings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    course_catalog_id = Column(UUID(as_uuid=True), nullable=False)
    semester_id = Column(UUID(as_uuid=True), nullable=False)
    faculty_id = Column(UUID(as_uuid=True), nullable=False)
    section_number = Column(String, nullable=False)
    max_capacity = Column(Integer, nullable=False)

class EnrollmentORM(Base):
    __tablename__ = "enrollments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), nullable=False)
    course_offering_id = Column(UUID(as_uuid=True), nullable=False)
    status = Column(SQLEnum(EnrollmentStatus), nullable=False)
    enrollment_date = Column(DateTime(timezone=True), nullable=False)
    dropped_date = Column(DateTime(timezone=True), nullable=True)