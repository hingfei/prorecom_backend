from typing import Optional, List
import strawberry
from sqlalchemy import select
from conn import get_session, Skill as SkillModel
import csv


@strawberry.type
class SkillType:
    skill_id: strawberry.ID
    skill_name: Optional[str]


async def export_skills_to_csv():
    async with get_session() as session:
        query = select(SkillModel)
        results = await session.execute(query)
        skills = results.scalars().unique()

        headers = ['skill_id', 'skill_name']
        rows = [(skill.skill_id, skill.skill_name) for skill in skills]

        with open('skill_list.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

        print(f'Skills saved to skill_list.csv successfully.')


@strawberry.type
class Query:
    @strawberry.field
    async def skill_listing(self) -> List[SkillType]:
        async with get_session() as session:
            query = select(SkillModel)
            results = await session.execute(query)
            return results.scalars().unique()
