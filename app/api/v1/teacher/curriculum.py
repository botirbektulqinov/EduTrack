"""
EduTrack - Teacher: Curriculum Read API
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_teacher_user
from app.core.database import get_db
from app.models.user import User
from app.schemas.common import SuccessResponse
from app.schemas.curriculum import CurriculumModuleResponse, SubjectResponse, SubjectTreeResponse, TopicResponse
from app.services.curriculum_service import CurriculumService

router = APIRouter(tags=["Teacher - Curriculum"])


@router.get("/curriculum/tree", response_model=SuccessResponse)
async def get_curriculum_tree(
    db: AsyncSession = Depends(get_db),
    teacher: User = Depends(get_teacher_user),
):
    subjects = await CurriculumService.list_tree(db)
    serialized = []
    for subject in subjects:
        serialized.append(
            SubjectTreeResponse.model_validate({
                **SubjectResponse.model_validate(subject).model_dump(),
                "modules": [
                    {
                        **CurriculumModuleResponse.model_validate(module).model_dump(),
                        "topics": [
                            {
                                **TopicResponse.model_validate(topic).model_dump(),
                                "module_name": module.name,
                                "subject_id": subject.id,
                                "subject_name": subject.name,
                            }
                            for topic in module.topics
                        ],
                    }
                    for module in subject.modules
                ],
            }).model_dump()
        )

    return SuccessResponse(data={"subjects": serialized})
