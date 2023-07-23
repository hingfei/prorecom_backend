from typing import Optional, List
import strawberry
from sqlalchemy import select
from conn import get_session, Skill as SkillModel
import csv


# Type definition for the SkillType
@strawberry.type
class SkillType:
    skill_id: strawberry.ID
    skill_name: Optional[str]


# Function to export skills to a CSV file
async def export_skills_to_csv():
    async with get_session() as session:
        # Query all skills from the SkillModel
        query = select(SkillModel)
        results = await session.execute(query)
        skills = results.scalars().unique()

        # Define the CSV file headers and rows
        headers = ['skill_id', 'skill_name']
        rows = [(skill.skill_id, skill.skill_name) for skill in skills]

        # Write the skills to a CSV file
        with open('skill_list.csv', 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)
            writer.writerows(rows)

        print(f'Skills saved to skill_list.csv successfully.')


# Type definition for the Query class
@strawberry.type
class Query:
    # Query to fetch a list of all skills
    @strawberry.field
    async def skill_listing(self) -> List[SkillType]:
        async with get_session() as session:
            query = select(SkillModel)
            results = await session.execute(query)
            return results.scalars().unique()
