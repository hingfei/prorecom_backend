from typing import Optional, List

import strawberry
from sqlalchemy import select


from conn import get_session, Skill as SkillModel


@strawberry.type
class SkillType:
    skill_id: strawberry.ID
    skill_name: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    async def skill_listing(self) -> List[SkillType]:
        async with get_session() as session:
            query = select(SkillModel)
            results = await session.execute(query)
            return results.scalars().unique()
