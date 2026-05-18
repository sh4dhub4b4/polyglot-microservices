import pytest
from uuid import uuid4
from domain.entities import CourseOffering, Enrollment, EnrollmentStatus
from use_cases.enroll_student import EnrollStudentUseCase, EnrollmentError
from use_cases.ports import CourseOfferingRepository, EnrollmentRepository

# --- In-Memory Mocks (Fake Adapters) ---
class FakeCourseRepo:
    def __init__(self, offering: CourseOffering, current_count: int = 0):
        self.offering = offering
        self.current_count = current_count

    def get_by_id(self, offering_id):
        return self.offering if self.offering.id == offering_id else None

    def get_active_enrollment_count(self, offering_id):
        return self.current_count

class FakeEnrollmentRepo:
    def __init__(self, existing_enrollment=None):
        self.existing = existing_enrollment
        self.saved_enrollment = None

    def get_by_student_and_offering(self, student_id, offering_id):
        return self.existing

    def save(self, enrollment):
        self.saved_enrollment = enrollment

# --- The Tests ---
def test_successful_enrollment():
    offering = CourseOffering(course_catalog_id=uuid4(), semester_id=uuid4(), faculty_id=uuid4(), section_number="A", max_capacity=30)
    course_repo = FakeCourseRepo(offering, current_count=10)
    enrollment_repo = FakeEnrollmentRepo()
    
    use_case = EnrollStudentUseCase(course_repo, enrollment_repo)
    student_id = uuid4()
    
    result = use_case.execute(student_id=student_id, offering_id=offering.id)
    
    assert result.status == EnrollmentStatus.ACTIVE
    assert enrollment_repo.saved_enrollment is not None
    assert enrollment_repo.saved_enrollment.student_id == student_id

def test_fails_when_over_capacity():
    offering = CourseOffering(course_catalog_id=uuid4(), semester_id=uuid4(), faculty_id=uuid4(), section_number="B", max_capacity=30)
    course_repo = FakeCourseRepo(offering, current_count=30)  # Class is full!
    enrollment_repo = FakeEnrollmentRepo()
    
    use_case = EnrollStudentUseCase(course_repo, enrollment_repo)
    
    with pytest.raises(EnrollmentError, match="Course is at maximum capacity."):
        use_case.execute(student_id=uuid4(), offering_id=offering.id)

def test_fails_duplicate_enrollment():
    student_id = uuid4()
    offering = CourseOffering(course_catalog_id=uuid4(), semester_id=uuid4(), faculty_id=uuid4(), section_number="C", max_capacity=30)
    existing_enrollment = Enrollment(student_id=student_id, course_offering_id=offering.id, status=EnrollmentStatus.ACTIVE)
    
    course_repo = FakeCourseRepo(offering, current_count=5)
    enrollment_repo = FakeEnrollmentRepo(existing_enrollment)
    
    use_case = EnrollStudentUseCase(course_repo, enrollment_repo)
    
    with pytest.raises(EnrollmentError, match="Student is already actively enrolled in this course."):
        use_case.execute(student_id=student_id, offering_id=offering.id)