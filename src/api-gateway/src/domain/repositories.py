from abc import ABC, abstractmethod
from typing import Optional, List
from uuid import UUID
from .entities import User, Course, Enrollment

class UserRepository(ABC):
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> Optional[User]:
        pass

class CourseRepository(ABC):
    @abstractmethod
    def get_by_id(self, course_id: UUID) -> Optional[Course]:
        pass

class EnrollmentRepository(ABC):
    @abstractmethod
    def get_by_student_and_course(self, student_id: UUID, course_id: UUID) -> Optional[Enrollment]:
        pass

    @abstractmethod
    def save(self, enrollment: Enrollment) -> None:
        pass