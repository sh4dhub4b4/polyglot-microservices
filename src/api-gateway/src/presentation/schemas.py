from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from domain.entities import EnrollmentStatus

class EnrollStudentRequest(BaseModel):
    student_id: UUID
    course_offering_id: UUID

class EnrollmentResponse(BaseModel):
    id: UUID
    student_id: UUID
    course_offering_id: UUID
    status: EnrollmentStatus
    enrollment_date: datetime
    
    class Config:
        from_attributes = True  # Allows Pydantic to read our Domain Entity