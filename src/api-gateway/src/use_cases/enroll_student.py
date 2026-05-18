from uuid import UUID
from domain.entities import Enrollment, EnrollmentStatus
from use_cases.ports import CourseOfferingRepository, EnrollmentRepository

class EnrollmentError(Exception):
    """Custom exception for enrollment business rule violations."""
    pass

class EnrollStudentUseCase:
    def __init__(self, course_repo: CourseOfferingRepository, enrollment_repo: EnrollmentRepository):
        # Dependency Injection: We inject the interface, not the database.
        self.course_repo = course_repo
        self.enrollment_repo = enrollment_repo

    def execute(self, student_id: UUID, offering_id: UUID) -> Enrollment:
        # 1. Validate Course Exists
        offering = self.course_repo.get_by_id(offering_id)
        if not offering:
            raise EnrollmentError("Course offering does not exist.")

        # 2. Check for Duplicate Enrollment
        existing_enrollment = self.enrollment_repo.get_by_student_and_offering(student_id, offering_id)
        if existing_enrollment and existing_enrollment.status == EnrollmentStatus.ACTIVE:
            raise EnrollmentError("Student is already actively enrolled in this course.")

        # 3. Enforce Capacity Business Rule
        current_enrollment_count = self.course_repo.get_active_enrollment_count(offering_id)
        if current_enrollment_count >= offering.max_capacity:
            raise EnrollmentError("Course is at maximum capacity.")

        # 4. Create Entity and Persist
        new_enrollment = Enrollment(student_id=student_id, course_offering_id=offering_id)
        self.enrollment_repo.save(new_enrollment)

        return new_enrollment