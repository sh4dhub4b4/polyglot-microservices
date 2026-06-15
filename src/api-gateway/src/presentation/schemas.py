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

class CustomPodRequest(BaseModel):
    faculty_id: UUID
    base_image: str # The ID of the base image, e.g., 'cpp-basic'
    custom_env_id: str # e.g., 'custom_cpp_101'
    custom_init_script: str
    base_cost: float = 0.0

class CustomPodResponse(BaseModel):
    id: str
    name: str
    docker_image: str
    custom_env_id: str
    custom_init_script: str

    class Config:
        from_attributes = True