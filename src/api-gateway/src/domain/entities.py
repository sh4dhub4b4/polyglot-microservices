from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from enum import Enum
from uuid import UUID, uuid4

# --- Domain Enums ---
class UserRole(Enum):
    STUDENT = "STUDENT"
    FACULTY = "FACULTY"
    ADMIN = "ADMIN"

class EnrollmentStatus(Enum):
    ACTIVE = "ACTIVE"
    DROPPED = "DROPPED"
    COMPLETED = "COMPLETED"

# --- Domain Entities ---

@dataclass(kw_only=True)
class University:
    name: str
    domain: str  
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

@dataclass(kw_only=True)
class Department:
    university_id: UUID
    name: str
    code: str  
    id: UUID = field(default_factory=uuid4)

@dataclass(kw_only=True)
class Semester:
    university_id: UUID
    name: str  
    start_date: date
    end_date: date
    id: UUID = field(default_factory=uuid4)

    def is_current(self, target_date: date) -> bool:
        return self.start_date <= target_date <= self.end_date

@dataclass(kw_only=True)
class User:
    university_id: UUID
    email: str
    full_name: str
    role: UserRole
    id: UUID = field(default_factory=uuid4)
    is_active: bool = True

@dataclass(kw_only=True)
class CourseCatalog:
    department_id: UUID
    title: str
    course_code: str  
    credits: int
    prerequisite_course_ids: list[UUID] = field(default_factory=list)
    id: UUID = field(default_factory=uuid4)

@dataclass(kw_only=True)
class CourseOffering:
    course_catalog_id: UUID
    semester_id: UUID
    faculty_id: UUID
    section_number: str 
    max_capacity: int  # Added to enforce enrollment limits
    id: UUID = field(default_factory=uuid4)

@dataclass(kw_only=True)
class Enrollment:
    student_id: UUID
    course_offering_id: UUID 
    status: EnrollmentStatus = EnrollmentStatus.ACTIVE
    # FIXED: Use timezone-aware UTC datetime
    enrollment_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    dropped_date: datetime | None = None
    id: UUID = field(default_factory=uuid4)

    def drop_course(self):
        if self.status == EnrollmentStatus.DROPPED:
            raise ValueError("Student has already dropped this course.")
        self.status = EnrollmentStatus.DROPPED
        # FIXED: Use timezone-aware UTC datetime
        self.dropped_date = datetime.now(timezone.utc)