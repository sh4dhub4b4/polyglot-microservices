from fastapi import APIRouter, Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import datetime
from uuid6 import uuid7
import json

from infrastructure.database import SessionLocal
from infrastructure.orm_models import (
    UserORM, UserRole, CourseOfferingORM, EnrollmentORM,
    AssignmentORM, AssignmentStatus, SubmissionORM, SubmissionStatus,
    TenantORM, BillingTransactionORM, PodCatalogORM
)
from domain.entities import EnrollmentStatus
from use_cases.grader_service import run_grader
from use_cases.auth_service import decode_access_token

security = HTTPBearer(auto_error=False)
router = APIRouter(prefix="/api/v1/academic", tags=["Academic"])

# ─────────────────────────────────────────────────────────
# Dependency: DB Session
# ─────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ─────────────────────────────────────────────────────────
# JWT Auth — validates Bearer token
# Falls back to X-User-ID / X-User-Role headers for backwards compatibility
# ─────────────────────────────────────────────────────────
def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_user_id: Optional[str] = Header(None),
    x_user_role: Optional[str] = Header(None),
    db: Session = Depends(get_db)
) -> UserORM:
    if credentials:
        payload = decode_access_token(credentials.credentials)
        if payload:
            user = db.query(UserORM).filter(UserORM.id == payload["sub"]).first()
            if user:
                return user

    if x_user_id and x_user_role:
        user = db.query(UserORM).filter(UserORM.id == x_user_id).first()
        if user:
            return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing authentication. Provide a Bearer token or X-User-ID / X-User-Role headers.",
        headers={"WWW-Authenticate": "Bearer"},
    )

def require_faculty(user: UserORM = Depends(get_current_user)) -> UserORM:
    if user.role != UserRole.FACULTY:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Faculty only action.")
    return user

def require_student(user: UserORM = Depends(get_current_user)) -> UserORM:
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Student only action.")
    return user

# ─────────────────────────────────────────────────────────
# TEACHER ENDPOINTS
# ─────────────────────────────────────────────────────────

@router.get("/teacher/courses", summary="[Teacher] List my course offerings")
def teacher_get_courses(
    faculty: UserORM = Depends(require_faculty),
    db: Session = Depends(get_db)
):
    """Returns all course offerings taught by this faculty member."""
    courses = db.query(CourseOfferingORM).filter(
        CourseOfferingORM.faculty_id == faculty.id
    ).all()
    return [{
        "id": str(c.id),
        "section_number": c.section_number,
        "max_capacity": c.max_capacity,
        "tenant_id": str(c.tenant_id)
    } for c in courses]


@router.post("/teacher/courses", summary="[Teacher] Create a course offering", status_code=201)
def teacher_create_course(
    body: dict,
    faculty: UserORM = Depends(require_faculty),
    db: Session = Depends(get_db)
):
    """
    Teacher creates a new course offering.
    Body: { "section_number": "CS101-A", "max_capacity": 40 }
    """
    offering = CourseOfferingORM(
        id=uuid7(),
        faculty_id=faculty.id,
        tenant_id=faculty.tenant_id,
        course_catalog_id=uuid7(),  # placeholder until catalog feature is built
        semester_id=uuid7(),         # placeholder
        section_number=body.get("section_number", "A"),
        max_capacity=body.get("max_capacity", 40)
    )
    db.add(offering)
    db.commit()
    db.refresh(offering)
    return {"id": str(offering.id), "section_number": offering.section_number, "status": "created"}


@router.post("/teacher/assignments", summary="[Teacher] Create an assignment", status_code=201)
def teacher_create_assignment(
    body: dict,
    faculty: UserORM = Depends(require_faculty),
    db: Session = Depends(get_db)
):
    """
    Teacher creates an assignment for a course offering.
    Body: {
        "course_offering_id": "...",
        "title": "Linked List Implementation",
        "description": "Implement a doubly linked list in C++...",
        "allowed_pod_id": "cpp-basic",
        "max_marks": 100,
        "due_date": "2026-07-01T23:59:00Z",
        "hidden_test_cases": [{"stdin": "5", "expected_stdout": "10"}]
    }
    """
    assignment = AssignmentORM(
        id=uuid7(),
        course_offering_id=body["course_offering_id"],
        created_by_faculty_id=faculty.id,
        title=body["title"],
        description=body.get("description", ""),
        allowed_pod_id=body.get("allowed_pod_id"),
        max_marks=body.get("max_marks", 100.0),
        due_date=datetime.fromisoformat(body["due_date"]) if body.get("due_date") else None,
        status=AssignmentStatus.PUBLISHED,
        hidden_test_cases=json.dumps(body.get("hidden_test_cases", []))
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return {"id": str(assignment.id), "title": assignment.title, "status": "published"}


@router.get("/teacher/assignments/{assignment_id}/submissions", summary="[Teacher] View all submissions")
def teacher_view_submissions(
    assignment_id: str,
    faculty: UserORM = Depends(require_faculty),
    db: Session = Depends(get_db)
):
    """Returns all student submissions for a given assignment."""
    # Verify faculty owns this assignment
    assignment = db.query(AssignmentORM).filter(
        AssignmentORM.id == assignment_id,
        AssignmentORM.created_by_faculty_id == faculty.id
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or not yours.")
    
    submissions = db.query(SubmissionORM).filter(
        SubmissionORM.assignment_id == assignment_id
    ).all()
    
    return [{
        "submission_id": str(s.id),
        "student_id": str(s.student_id),
        "language": s.language,
        "status": s.status.value,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        "tests_passed": s.tests_passed,
        "tests_total": s.tests_total,
        "marks_awarded": s.marks_awarded,
        "feedback": s.grader_feedback
    } for s in submissions]


@router.patch("/teacher/submissions/{submission_id}/grade", summary="[Teacher] Manually grade a submission")
def teacher_grade_submission(
    submission_id: str,
    body: dict,
    faculty: UserORM = Depends(require_faculty),
    db: Session = Depends(get_db)
):
    """Teacher can manually override grade and leave feedback."""
    submission = db.query(SubmissionORM).filter(SubmissionORM.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found.")
    
    submission.marks_awarded = body.get("marks_awarded", submission.marks_awarded)
    submission.grader_feedback = body.get("feedback", submission.grader_feedback)
    submission.status = SubmissionStatus.GRADED
    db.commit()
    return {"status": "graded", "marks_awarded": submission.marks_awarded}


# ─────────────────────────────────────────────────────────
# STUDENT ENDPOINTS
# ─────────────────────────────────────────────────────────

@router.get("/student/courses", summary="[Student] List my enrolled courses")
def student_get_courses(
    student: UserORM = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Returns all course offerings the student is actively enrolled in."""
    enrollments = db.query(EnrollmentORM).filter(
        EnrollmentORM.student_id == student.id,
        EnrollmentORM.status == EnrollmentStatus.ACTIVE
    ).all()
    
    result = []
    for enr in enrollments:
        offering = enr.course_offering
        result.append({
            "enrollment_id": str(enr.id),
            "course_offering_id": str(offering.id),
            "section_number": offering.section_number,
            "faculty_id": str(offering.faculty_id)
        })
    return result


@router.get("/student/courses/{course_offering_id}/assignments", summary="[Student] View assignments for a course")
def student_get_assignments(
    course_offering_id: str,
    student: UserORM = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Returns all published assignments for a course the student is enrolled in."""
    # Verify enrollment
    enrollment = db.query(EnrollmentORM).filter(
        EnrollmentORM.student_id == student.id,
        EnrollmentORM.course_offering_id == course_offering_id,
        EnrollmentORM.status == EnrollmentStatus.ACTIVE
    ).first()
    if not enrollment:
        raise HTTPException(status_code=403, detail="Not enrolled in this course.")
    
    assignments = db.query(AssignmentORM).filter(
        AssignmentORM.course_offering_id == course_offering_id,
        AssignmentORM.status == AssignmentStatus.PUBLISHED
    ).all()
    
    return [{
        "id": str(a.id),
        "title": a.title,
        "description": a.description,
        "allowed_pod_id": a.allowed_pod_id,
        "max_marks": a.max_marks,
        "due_date": a.due_date.isoformat() if a.due_date else None,
    } for a in assignments]


@router.post("/student/assignments/{assignment_id}/submit", summary="[Student] Submit code for an assignment", status_code=201)
def student_submit_assignment(
    assignment_id: str,
    body: dict,
    student: UserORM = Depends(require_student),
    db: Session = Depends(get_db)
):
    """
    Student submits code for an assignment.
    Body: { "source_code": "int main(){...}", "language": "cpp-basic" }
    The backend will run the code against hidden test cases (auto-grader).
    """
    assignment = db.query(AssignmentORM).filter(
        AssignmentORM.id == assignment_id,
        AssignmentORM.status == AssignmentStatus.PUBLISHED
    ).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found or not available.")
    
    source_code = body.get("source_code", "")
    language = body.get("language", "cpp-basic")
    
    result = run_grader(
        source_code=source_code,
        language=language,
        hidden_test_cases=assignment.hidden_test_cases or "[]",
        max_marks=assignment.max_marks,
    )
    tests_passed = result.tests_passed
    tests_total = result.tests_total
    marks_awarded = result.marks_awarded
    
    # Check if resubmitting
    existing = db.query(SubmissionORM).filter(
        SubmissionORM.assignment_id == assignment_id,
        SubmissionORM.student_id == student.id
    ).first()
    
    if existing:
        existing.source_code = source_code
        existing.language = language
        existing.status = SubmissionStatus.RESUBMITTED
        existing.submitted_at = datetime.utcnow()
        existing.tests_passed = tests_passed
        existing.tests_total = tests_total
        existing.marks_awarded = marks_awarded
        existing.stdout = result.stdout
        existing.stderr = result.stderr
        existing.grader_feedback = "; ".join(result.grader_feedback)
        submission = existing
    else:
        submission = SubmissionORM(
            id=uuid7(),
            assignment_id=assignment_id,
            student_id=student.id,
            source_code=source_code,
            language=language,
            status=SubmissionStatus.GRADED if tests_total > 0 else SubmissionStatus.SUBMITTED,
            submitted_at=datetime.utcnow(),
            tests_passed=tests_passed,
            tests_total=tests_total,
            marks_awarded=marks_awarded,
            stdout=result.stdout,
            stderr=result.stderr,
            grader_feedback="; ".join(result.grader_feedback),
        )
        db.add(submission)
    
    db.commit()
    db.refresh(submission)
    
    return {
        "submission_id": str(submission.id),
        "status": submission.status.value,
        "tests_passed": tests_passed,
        "tests_total": tests_total,
        "marks_awarded": marks_awarded,
        "message": f"Submitted successfully! {tests_passed}/{tests_total} test cases passed.",
        "feedback": result.grader_feedback,
    }


@router.get("/student/my-submissions", summary="[Student] View my all submissions")
def student_my_submissions(
    student: UserORM = Depends(require_student),
    db: Session = Depends(get_db)
):
    """Returns all submissions made by this student, across all courses."""
    submissions = db.query(SubmissionORM).filter(
        SubmissionORM.student_id == student.id
    ).order_by(SubmissionORM.submitted_at.desc()).all()
    
    return [{
        "submission_id": str(s.id),
        "assignment_id": str(s.assignment_id),
        "language": s.language,
        "status": s.status.value,
        "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
        "marks_awarded": s.marks_awarded,
        "tests_passed": s.tests_passed,
        "tests_total": s.tests_total
    } for s in submissions]


# ─────────────────────────────────────────────────────────
# BILLING ENDPOINTS (Admin/Faculty)
# ─────────────────────────────────────────────────────────

@router.get("/billing/credits", summary="[Faculty/Admin] View tenant compute credits")
def get_billing_credits(
    user: UserORM = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns the current compute credit balance for the university (tenant)."""
    tenant = db.query(TenantORM).filter(TenantORM.id == user.tenant_id).first()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found.")
    
    # Get recent transactions
    recent_txns = db.query(BillingTransactionORM).filter(
        BillingTransactionORM.tenant_id == user.tenant_id
    ).order_by(BillingTransactionORM.created_at.desc()).limit(20).all()
    
    return {
        "tenant_name": tenant.name,
        "subscription_tier": tenant.subscription_tier,
        "compute_credits_remaining": tenant.compute_credits,
        "recent_transactions": [{
            "task_id": t.task_id,
            "student_id": str(t.student_id),
            "pod_id": t.pod_id,
            "credits_deducted": t.credits_deducted,
            "execution_time_ms": t.execution_time_ms,
            "created_at": t.created_at.isoformat() if t.created_at else None
        } for t in recent_txns]
    }
