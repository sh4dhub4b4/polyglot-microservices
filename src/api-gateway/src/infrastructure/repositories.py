from typing import Optional
from uuid import UUID
from sqlalchemy.orm import Session
from domain.entities import CourseOffering, Enrollment
from infrastructure.orm_models import CourseOfferingORM, EnrollmentORM
from use_cases.ports import CourseOfferingRepository, EnrollmentRepository

class SQLCourseOfferingRepository(CourseOfferingRepository):
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_id(self, offering_id: UUID) -> Optional[CourseOffering]:
        orm = self.db.query(CourseOfferingORM).filter(CourseOfferingORM.id == offering_id).first()
        if not orm:
            return None
        return CourseOffering(
            id=orm.id,
            course_catalog_id=orm.course_catalog_id,
            semester_id=orm.semester_id,
            faculty_id=orm.faculty_id,
            section_number=orm.section_number,
            max_capacity=orm.max_capacity
        )

    def get_active_enrollment_count(self, offering_id: UUID) -> int:
        from domain.entities import EnrollmentStatus
        return self.db.query(EnrollmentORM).filter(
            EnrollmentORM.course_offering_id == offering_id,
            EnrollmentORM.status == EnrollmentStatus.ACTIVE
        ).count()

class SQLEnrollmentRepository(EnrollmentRepository):
    def __init__(self, db_session: Session):
        self.db = db_session

    def get_by_student_and_offering(self, student_id: UUID, offering_id: UUID) -> Optional[Enrollment]:
        orm = self.db.query(EnrollmentORM).filter(
            EnrollmentORM.student_id == student_id,
            EnrollmentORM.course_offering_id == offering_id
        ).first()
        
        if not orm:
            return None
            
        return Enrollment(
            id=orm.id,
            student_id=orm.student_id,
            course_offering_id=orm.course_offering_id,
            status=orm.status,
            enrollment_date=orm.enrollment_date,
            dropped_date=orm.dropped_date
        )

    def save(self, enrollment: Enrollment) -> None:
        # Translate Domain Entity back to DB ORM for saving
        orm = EnrollmentORM(
            id=enrollment.id,
            student_id=enrollment.student_id,
            course_offering_id=enrollment.course_offering_id,
            status=enrollment.status,
            enrollment_date=enrollment.enrollment_date,
            dropped_date=enrollment.dropped_date
        )
        self.db.add(orm)
        self.db.commit()