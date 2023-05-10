import strawberry
from sqlalchemy import select, delete
from typing import Optional, List

from sqlalchemy.orm import selectinload

from conn import get_session, Project as ProjectModel, Skill as SkillModel, ProjectSkills, Company as CompanyModel
from strawberry.types import Info

from recommendations.recommendation_engine import get_projects_recommendations
from schemas.company import CompanyType
from schemas.skill import SkillType


@strawberry.input
class CreateProjectInput:
    project_name: str
    company_id: strawberry.ID
    project_types: Optional[str]
    post_dates: Optional[str]
    project_salary: Optional[str]
    project_desc: Optional[str]
    project_req: Optional[str]
    project_exp_lvl: Optional[str]
    skills: List[str]


@strawberry.input
class UpdateProjectInput:
    project_id: strawberry.ID
    project_name: Optional[str] = None
    project_types: Optional[str] = None
    project_salary: Optional[str] = None
    project_desc: Optional[str] = None
    project_req: Optional[str] = None
    project_exp_lvl: Optional[str] = None
    skills: Optional[List[str]] = None


@strawberry.type
class ProjectType:
    project_id: strawberry.ID
    project_name: str
    company_id: strawberry.ID
    company: Optional[CompanyType]
    project_types: Optional[str]
    post_dates: Optional[str]
    project_salary: Optional[str]
    project_desc: Optional[str]
    project_req: Optional[str]
    project_exp_lvl: Optional[str]
    skills: List[SkillType]


@strawberry.type
class ProjectResponse:
    success: bool
    project: Optional[ProjectType] = None
    message: Optional[str] = None


@strawberry.type
class Query:
    @strawberry.field
    async def project_detail(self, project_id: int) -> Optional[ProjectType]:
        async with get_session() as session:
            query = select(ProjectModel).options(selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                                                 selectinload(ProjectModel.skills),
                                                 ).where(ProjectModel.project_id == project_id)
            result = await session.execute(query)
            return result.scalar_one() if result else None

    @strawberry.field
    async def project_listing(self, recommendation: Optional[bool] = False) -> List[ProjectType]:
        async with get_session() as session:
            if recommendation:
                ranked_projects = await get_projects_recommendations(417)
                # print('ranked projects', ranked_projects)
                project_ids = [i for i, _ in ranked_projects]
                # print("project id", project_ids)
                query = select(ProjectModel).options(
                    selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                    selectinload(ProjectModel.skills)
                ).where(ProjectModel.project_id.in_(project_ids))
                result = await session.execute(query)
                projects = result.scalars().all()

                # Create a dictionary to map project id to the project object
                project_dict = {project.project_id: project for project in projects}

                # Reorder the projects based on the project_ids sequence
                ordered_projects = [project_dict[project_id] for project_id in project_ids]

                return ordered_projects
            else:
                query = select(ProjectModel).options(selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                                                     selectinload(ProjectModel.skills)).limit(50)
                results = await session.execute(query)
                return results.scalars().unique()


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_project(self, input: CreateProjectInput) -> ProjectResponse:

        async with get_session() as session:
            try:
                sql = select(ProjectModel).where(ProjectModel.company_id == input.company_id)
                company = (await session.execute(sql)).first()

                if company is None:
                    return ProjectResponse(success=False,
                                           message=f"Company does not exist.")

                # Create project and add it to the session
                new_project = ProjectModel(
                    project_name=input.project_name,
                    company_id=input.company_id,
                    project_types=input.project_types,
                    post_dates=input.post_dates,
                    project_salary=input.project_salary,
                    project_desc=input.project_desc,
                    project_req=input.project_req,
                    project_exp_lvl=input.project_exp_lvl,
                )
                # Add skills to project
                for skill_name in input.skills:
                    skill = await session.execute(select(SkillModel).where(SkillModel.skill_name == skill_name))
                    skill = skill.scalar()
                    if skill is None:
                        skill = SkillModel(skill_name=skill_name)
                        session.add(skill)
                    new_project.skills.append(skill)

                session.add(new_project)
                await session.commit()

                return ProjectResponse(
                    success=True, project=new_project, message="Project is added."
                )

            except Exception as e:
                # Return an error response with the error message
                return ProjectResponse(success=False, message=str(e))

    @strawberry.mutation
    async def update_project(self, input: UpdateProjectInput) -> ProjectResponse:
        async with get_session() as session:
            try:
                project = await session.get(ProjectModel, input.project_id)
                if project is None:
                    return ProjectResponse(
                        success=False, message=f"Project with ID {input.project_id} not found."
                    )

                if input.project_name is not None:
                    project.project_name = input.project_name
                if input.project_types is not None:
                    project.project_types = input.project_types
                if input.project_salary is not None:
                    project.project_salary = input.project_salary
                if input.project_desc is not None:
                    project.project_desc = input.project_desc
                if input.project_req is not None:
                    project.project_req = input.project_req
                if input.project_exp_lvl is not None:
                    project.project_exp_lvl = input.project_exp_lvl
                if input.skills is not None:
                    # Remove all existing skills from project
                    await session.execute(delete(ProjectSkills).where(ProjectSkills.project_id == project.project_id))

                    # Add skills to project
                    for skill_name in input.skills:
                        skill = await session.execute(select(SkillModel).where(SkillModel.skill_name == skill_name))
                        skill = skill.scalar()
                        if skill is None:
                            skill = SkillModel(skill_name=skill_name)
                            session.add(skill)
                            await session.flush()
                        project_skill = ProjectSkills(project_id=project.project_id, skill_id=skill.skill_id)
                        session.add(project_skill)

                await session.commit()
                return ProjectResponse(success=True, project=project, message="Project has been updated.")

            except Exception as e:
                return ProjectResponse(success=False, project=None, message=str(e))

    @strawberry.mutation
    async def delete_project(self, info: Info, project_id: int) -> ProjectResponse:
        async with get_session() as session:
            try:
                # delete project from the database
                delete_query = delete(ProjectModel).where(ProjectModel.project_id == project_id)
                deleted_job_seeker = await session.execute(delete_query)
                if deleted_job_seeker.rowcount == 0:
                    return ProjectResponse(success=False, message=f"Project with ID {project_id} not found.")

                await session.execute(delete(ProjectSkills).where(ProjectSkills.project_id == project_id))
                await session.commit()

                return ProjectResponse(success=True, message="Project deleted successfully")

            except Exception as e:
                # Return an error response with the error message
                return ProjectResponse(success=False, message=str(e))
