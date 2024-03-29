from datetime import datetime

import src.settings as settings
import strawberry
import numpy as np
import json
from sqlalchemy import select, delete, or_, func, and_
from typing import Optional, List
from sqlalchemy.orm import selectinload
from conn import get_session, Project as ProjectModel, Skill as SkillModel, ProjectSkills, Company as CompanyModel, \
    ProjectApplication as ProjectApplicationModel
from strawberry.types import Info
from src.recommendations.project_recom_engine import get_projects_recommendations, preprocess_skillsets, \
    cluster_projects
from src.schemas.company import CompanyType
from src.schemas.job_seeker import JobSeekerType
from src.schemas.skill import SkillType


# Input class for creating a new project
@strawberry.input
class CreateProjectInput:
    project_name: str
    company_id: strawberry.ID
    project_types: Optional[str]
    project_min_salary: Optional[int] = None
    project_max_salary: Optional[int] = None
    project_desc: Optional[str]
    project_req: Optional[str]
    project_status: Optional[bool]
    project_exp_lvl: Optional[str]
    skills: List[int]


# Input class for updating an existing project
@strawberry.input
class UpdateProjectInput:
    project_id: strawberry.ID
    project_name: Optional[str] = None
    project_types: Optional[str] = None
    project_min_salary: Optional[int] = None
    project_max_salary: Optional[int] = None
    project_desc: Optional[str] = None
    project_req: Optional[str] = None
    project_status: Optional[bool] = None
    project_exp_lvl: Optional[str] = None
    skills: Optional[List[int]] = None


# Type definition for a Project Application
@strawberry.type
class ProjectApplicationType:
    project_application_id: strawberry.ID
    seeker_id: strawberry.ID
    project_id: strawberry.ID
    application_status: Optional[str]
    application_is_invited: Optional[bool]
    job_seeker: Optional[JobSeekerType]


# Type definition for a Project
@strawberry.type
class ProjectType:
    project_id: strawberry.ID
    project_name: str
    company_id: strawberry.ID
    company: Optional[CompanyType]
    project_types: Optional[str]
    post_dates: Optional[str]
    project_min_salary: Optional[int]
    project_max_salary: Optional[int]
    project_desc: Optional[str]
    project_req: Optional[str]
    project_status: Optional[bool]
    project_exp_lvl: Optional[str]
    skills: List[SkillType]
    project_applications: List[ProjectApplicationType]
    similarity_score: Optional[float] = None


# Type definition for a modified Project (used in response after creating or updating a project)
@strawberry.type
class ProjectModifyType:
    project_id: strawberry.ID


# Type definition for the response
@strawberry.type
class ProjectResponse:
    success: bool
    project: Optional[ProjectType] = None
    message: Optional[str] = None


# Type definition for the response after creating, updating, or deleting a project
@strawberry.type
class ProjectModifyResponse:
    success: bool
    project: Optional[ProjectModifyType] = None
    message: Optional[str] = None


# Type definition for the Query class
@strawberry.type
class Query:
    # Function to get the details of a specific project
    @strawberry.field
    async def project_detail(self, project_id: int) -> Optional[ProjectType]:
        async with get_session() as session:
            query = select(ProjectModel).options(selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                                                 selectinload(ProjectModel.skills),
                                                 selectinload(ProjectModel.project_applications).selectinload(
                                                     ProjectApplicationModel.job_seeker)
                                                 ).where(ProjectModel.project_id == project_id)
            result = await session.execute(query)
            return result.scalar_one() if result else None

    # Function to get a list of projects (can include recommendations)
    @strawberry.field
    async def project_listing(self, info: Info, recommendation: Optional[bool] = False) -> List[ProjectType]:
        async with get_session() as session:
            if recommendation:
                user_id = await info.context.get_current_user
                if user_id is None:
                    raise ValueError("User not authenticated")

                ranked_projects = await get_projects_recommendations(user_id)
                project_ids = [i for i, _ in ranked_projects]
                query = select(ProjectModel).options(
                    selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                    selectinload(ProjectModel.skills)
                ).where(ProjectModel.project_id.in_(project_ids))
                result = await session.execute(query)
                projects = result.scalars().unique().all()

                # Create a dictionary to map project id to the project object
                project_dict = {project.project_id: project for project in projects}

                # Reorder the projects based on the project_ids sequence
                ordered_projects = []
                for project_id, similarity_score in ranked_projects:
                    project = project_dict.get(project_id)
                    if project:
                        project.similarity_score = similarity_score
                        ordered_projects.append(project)

                return ordered_projects
            else:
                query = select(ProjectModel).options(
                    selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                    selectinload(ProjectModel.skills)
                ).where(ProjectModel.project_status == True).order_by(func.random())
                results = await session.execute(query)
                projects = results.scalars().unique().all()

                for project in projects:
                    project.similarity_score = None

                return projects

    # Function to search for projects based on a search keyword
    @strawberry.field
    async def search_projects(self, search_keyword: str) -> List[ProjectType]:
        async with get_session() as session:
            query = select(ProjectModel).options(
                selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                selectinload(ProjectModel.skills)
            ).where(
                and_(
                    or_(
                        ProjectModel.project_name.ilike(f"%{search_keyword}%"),
                        ProjectModel.project_desc.ilike(f"%{search_keyword}%"),
                        ProjectModel.project_req.ilike(f"%{search_keyword}%")
                    ),
                    ProjectModel.project_status == True
                )
            )
            result = await session.execute(query)
            projects = result.scalars().all()

            for project in projects:
                project.similarity_score = None

            return projects

    # Function to get a list of projects belonging to a specific company
    @strawberry.field
    async def company_project_listing(self, company_id: int) -> List[Optional[ProjectType]]:
        async with get_session() as session:
            query = select(ProjectModel).options(
                selectinload(ProjectModel.company).joinedload(CompanyModel.users),
                selectinload(ProjectModel.skills),
                selectinload(ProjectModel.project_applications).selectinload(ProjectApplicationModel.job_seeker)
            ).where(ProjectModel.company_id == company_id).order_by(ProjectModel.project_id.desc())
            result = await session.execute(query)
            projects = result.scalars().all()

            return projects if projects else []


# Type definition for the Mutation class
@strawberry.type
class Mutation:
    # Mutation to create a new project
    @strawberry.mutation
    async def create_project(self, input: CreateProjectInput) -> ProjectModifyResponse:

        async with get_session() as session:
            try:
                sql = select(CompanyModel).where(CompanyModel.company_id == input.company_id)
                company = (await session.execute(sql)).first()

                if company is None:
                    return ProjectModifyResponse(success=False,
                                                 message=f"Company does not exist.")

                # Create project and add it to the session
                new_project = ProjectModel(
                    project_name=input.project_name,
                    company_id=input.company_id,
                    project_types=input.project_types,
                    post_dates=datetime.now().strftime('%m-%d-%Y'),
                    project_min_salary=input.project_min_salary,
                    project_max_salary=input.project_max_salary,
                    project_desc=input.project_desc,
                    project_req=input.project_req,
                    project_status=input.project_status,
                    project_exp_lvl=input.project_exp_lvl,
                )

                # Add skills to project
                if input.skills is not None:
                    skill_list = []
                    # Add skills to project
                    for skill_id in input.skills:
                        skill = await session.execute(select(SkillModel).where(SkillModel.skill_id == skill_id))
                        skill = skill.scalar()
                        skill_list.append(skill.skill_name)
                        new_project.skills.append(skill)

                    # Update skillset vector
                    skills_processed = preprocess_skillsets(skill_list)
                    skillset_size = settings.ft_model.get_dimension()
                    if len(skills_processed) > 0:
                        project_vector = np.mean(
                            [settings.ft_model.get_word_vector(skill) for skill in skills_processed], axis=0)
                    else:
                        project_vector = np.zeros(skillset_size)
                    new_project.project_skillset_vector = json.dumps(project_vector.tolist())

                session.add(new_project)
                await session.commit()
                await cluster_projects(refresh=True)

                return ProjectModifyResponse(
                    success=True, project=new_project, message="Project is added."
                )

            except Exception as e:
                # Return an error response with the error message
                return ProjectModifyResponse(success=False, message=str(e))

    # Mutation to update an existing project
    @strawberry.mutation
    async def update_project(self, input: UpdateProjectInput) -> ProjectModifyResponse:
        async with get_session() as session:
            try:
                project = await session.get(ProjectModel, input.project_id)
                if project is None:
                    return ProjectModifyResponse(
                        success=False, message=f"Project with ID {input.project_id} not found."
                    )

                if input.project_name is not None:
                    project.project_name = input.project_name
                if input.project_types is not None:
                    project.project_types = input.project_types
                if input.project_min_salary is not None:
                    project.project_min_salary = input.project_min_salary
                if input.project_max_salary is not None:
                    project.project_max_salary = input.project_max_salary
                if input.project_desc is not None:
                    project.project_desc = input.project_desc
                if input.project_req is not None:
                    project.project_req = input.project_req
                if input.project_exp_lvl is not None:
                    project.project_exp_lvl = input.project_exp_lvl
                if input.project_status is not None:
                    project.project_status = input.project_status
                if input.skills is not None:
                    skill_list = []
                    # Remove all existing skills from project
                    await session.execute(delete(ProjectSkills).where(ProjectSkills.project_id == project.project_id))

                    # Add skills to project
                    for skill_id in input.skills:
                        skill = await session.execute(select(SkillModel).where(SkillModel.skill_id == skill_id))
                        skill = skill.scalar()
                        skill_list.append(skill.skill_name)
                        project_skill = ProjectSkills(project_id=project.project_id, skill_id=skill.skill_id)
                        session.add(project_skill)

                    # Update skillset vector
                    skills_processed = preprocess_skillsets(skill_list)
                    skillset_size = settings.ft_model.get_dimension()
                    if len(skills_processed) > 0:
                        project_vector = np.mean(
                            [settings.ft_model.get_word_vector(skill) for skill in skills_processed], axis=0)
                    else:
                        project_vector = np.zeros(skillset_size)
                    project.project_skillset_vector = json.dumps(project_vector.tolist())

                await session.commit()
                await cluster_projects(refresh=True)

                return ProjectModifyResponse(success=True, project=project, message="Project has been updated.")

            except Exception as e:
                return ProjectModifyResponse(success=False, project=None, message=str(e))

    # Mutation to delete a project
    @strawberry.mutation
    async def delete_project(self, info: Info, project_id: int) -> ProjectModifyResponse:
        async with get_session() as session:
            try:
                # delete project from the database
                delete_query = delete(ProjectModel).where(ProjectModel.project_id == project_id)
                deleted_job_seeker = await session.execute(delete_query)
                if deleted_job_seeker.rowcount == 0:
                    return ProjectModifyResponse(success=False, message=f"Project with ID {project_id} not found.")

                await session.execute(delete(ProjectSkills).where(ProjectSkills.project_id == project_id))
                await session.commit()
                await cluster_projects(refresh=True)

                return ProjectModifyResponse(success=True, message="Project deleted successfully")

            except Exception as e:
                # Return an error response with the error message
                return ProjectModifyResponse(success=False, message=str(e))
