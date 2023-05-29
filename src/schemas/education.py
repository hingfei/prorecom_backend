from typing import Optional, List
import strawberry
from sqlalchemy import select, delete
from strawberry.types import Info
from conn import get_session, Education as EducationModel


@strawberry.input
class EducationInput:
    education_id: Optional[strawberry.ID] = None
    education_level: Optional[int] = None
    education_institution: Optional[str] = None
    field_of_study: Optional[int] = None
    graduation_year: Optional[int] = None
    description: Optional[str] = None
    grade: Optional[str] = None


@strawberry.type
class EducationType:
    education_id: strawberry.ID
    education_level: Optional[int]
    education_institution: Optional[str]
    field_of_study: Optional[int]
    graduation_year: Optional[int]
    description: Optional[str]
    grade: Optional[str]


@strawberry.type
class EducationResponse:
    success: bool
    message: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    async def education_listing(self, info: Info) -> List[EducationType]:
        async with get_session() as session:
            sql = select(EducationModel)
            educations = await session.execute(sql)
            return educations.scalars().unique().all()


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def delete_education(self, info: Info, education_id: strawberry.ID) -> EducationResponse:
        async with get_session() as session:
            try:
                delete_query = delete(EducationModel).where(EducationModel.education_id == education_id)
                deleted_education = await session.execute(delete_query)

                if deleted_education.rowcount == 0:
                    return EducationResponse(success=False, message="Education not found.")

                await session.commit()
                return EducationResponse(success=True, message="Education deleted successfully.")
            except Exception as e:
                return EducationResponse(success=False, message=str(e))
