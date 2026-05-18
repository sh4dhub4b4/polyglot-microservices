from typing import Protocol, Optional
from uuid import UUID
from domain.entities import CourseOffering, Enrollment

class CourseOfferingRepository(Protocol):
    def get_by_id(self, offering_id: UUID) -> Optional[CourseOffering]:
        """Fetch a specific course offering."""
        ...
        
    def get_active_enrollment_count(self, offering_id: UUID) -> int:
        """Count how many students are currently active in this offering."""
        ...

class EnrollmentRepository(Protocol):
    def get_by_student_and_offering(self, student_id: UUID, offering_id: UUID) -> Optional[Enrollment]:
        """Check if a student is already enrolled or dropped."""
        ...

    def save(self, enrollment: Enrollment) -> None:
        """Persist the enrollment entity."""
        ...