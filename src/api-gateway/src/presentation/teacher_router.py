from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID

from presentation.schemas import CustomPodRequest, CustomPodResponse
from infrastructure.database import SessionLocal
from infrastructure.orm_models import CourseOfferingORM, PodCatalogORM

router = APIRouter(prefix="/api/v1/teacher", tags=["Teacher Dashboard"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/courses/{faculty_id}",
    summary="List courses for a faculty member",
    description="Returns all course offerings taught by the specified faculty member.")
def get_faculty_courses(faculty_id: UUID, db: Session = Depends(get_db)):
    courses = db.query(CourseOfferingORM).filter(CourseOfferingORM.faculty_id == faculty_id).all()
    return [{"id": str(c.id), "section_number": c.section_number, "max_capacity": c.max_capacity} for c in courses]

@router.post("/env/customize",
    response_model=CustomPodResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a custom sandbox environment",
    description="""
    Faculty can create a customized sandbox environment by extending a base pod image.
    This allows injecting custom initialization scripts and setting compute limits
    for specific assignments or projects.
    """)
def customize_environment(request: CustomPodRequest, db: Session = Depends(get_db)):
    # 1. Fetch the base image catalog entry
    base_pod = db.query(PodCatalogORM).filter(PodCatalogORM.id == request.base_image).first()
    if not base_pod:
        raise HTTPException(status_code=404, detail="Base image not found")

    # 2. Create the customized pod spec
    custom_pod = PodCatalogORM(
        id=request.custom_env_id,
        name=f"{base_pod.name} (Customized)",
        docker_image=base_pod.docker_image,
        language=base_pod.language,
        is_gui=base_pod.is_gui,
        base_cost=request.base_cost,
        custom_env_id=request.custom_env_id,
        owner_faculty_id=request.faculty_id,
        custom_init_script=request.custom_init_script
    )

    try:
        db.add(custom_pod)
        db.commit()
        db.refresh(custom_pod)
        
        # Note: In a real system, we also need to push this new custom pod to Redis Cache 
        # so the Orchestrator can find it! We'll handle that via a helper or event later.
        
        return custom_pod
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
