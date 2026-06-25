from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from presentation.schemas import EnrollStudentRequest, EnrollmentResponse
from infrastructure.database import SessionLocal
from infrastructure.repositories import SQLCourseOfferingRepository, SQLEnrollmentRepository
from use_cases.enroll_student import EnrollStudentUseCase, EnrollmentError

router = APIRouter(prefix="/api/v1/enrollments", tags=["Enrollments"])

# --- Dependency Injection Helpers ---
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_enrollment_use_case(db: Session = Depends(get_db)) -> EnrollStudentUseCase:
    course_repo = SQLCourseOfferingRepository(db)
    enrollment_repo = SQLEnrollmentRepository(db)
    return EnrollStudentUseCase(course_repo, enrollment_repo)

# --- The Actual API Endpoint ---
@router.post("/",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a student in a course offering",
    description="""
    Enrolls a student in a specific course offering.
    Validates:
    - Student exists
    - Course offering exists and is not at capacity
    - Student is not already enrolled
    """)
def enroll_student(
    request: EnrollStudentRequest,
    use_case: EnrollStudentUseCase = Depends(get_enrollment_use_case)
):
    try:
        # The web layer simply passes data to the pure business logic
        enrollment = use_case.execute(
            student_id=request.student_id,
            offering_id=request.course_offering_id
        )
        return enrollment
    except EnrollmentError as e:
        # Map our custom business rule violations to standard 400 HTTP errors
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Internal server error")