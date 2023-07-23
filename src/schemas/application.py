from datetime import datetime
from typing import List

import strawberry
from pydantic.class_validators import Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from conn import get_session, JobSeeker as JobSeekerModel, Project as ProjectModel, \
    ProjectApplication as ProjectApplicationModel
from src.schemas.job_seeker import JobSeekerType
from src.schemas.project import ProjectType


# Input class for updating the application
@strawberry.input
class UpdateApplicationInput:
    project_application_id: strawberry.ID
    application_status: Optional[str] = None


# Type definition for an application
@strawberry.type
class ApplicationType:
    project_application_id: strawberry.ID
    seeker_id: strawberry.ID
    project_id: strawberry.ID
    application_status: Optional[str]
    application_date: Optional[str]
    application_is_invited: Optional[bool]
    job_seeker: Optional[JobSeekerType]
    project: Optional[ProjectType]


# Type definition for the application response
@strawberry.type
class ApplicationResponse:
    success: bool
    project_application_id: Optional[int]
    message: Optional[str]


# Type definition for the Query class
@strawberry.type
class Query:
    # Query to get job seeker's applications
    @strawberry.field
    async def get_job_seeker_applications(self, info: Info) -> List[ApplicationType]:
        async with get_session() as session:
            try:
                # Fetch the job seeker and project from the database
                user_id = await info.context.get_current_user
                if user_id is None:
                    raise ValueError("User not authenticated")

                # Fetch the job seeker's applications with eagerly loaded projects, companies, and skills
                applications_sql = select(ProjectApplicationModel).options(
                    selectinload(ProjectApplicationModel.project).options(
                        selectinload(ProjectModel.company),
                        selectinload(ProjectModel.skills)
                    ), selectinload(ProjectApplicationModel.job_seeker)
                ).where(ProjectApplicationModel.seeker_id == int(user_id)).order_by(
                    ProjectApplicationModel.project_application_id.desc())

                applications = await session.execute(applications_sql)
                return applications.scalars().all()

            except Exception as e:
                # Return an empty list if an error occurs
                return []

    # Query to get project's applications
    @strawberry.field
    async def get_project_applications(self, project_id: strawberry.ID) -> List[ApplicationType]:
        async with get_session() as session:
            try:
                # Fetch the project's applications
                applications_sql = select(ProjectApplicationModel).where(
                    ProjectApplicationModel.project_id == int(project_id)
                )
                applications = await session.execute(applications_sql)

                return applications.scalars().all()

            except Exception as e:
                # Return an empty list if an error occurs
                return []


# Type definition for the Mutation class
@strawberry.type
class Mutation:
    # Mutation to create a new application
    @strawberry.mutation
    async def create_application(self, info: Info, project_id: int, user_id: Optional[int] = None,
                                 application_is_invited: Optional[bool] = False) -> ApplicationResponse:
        async with get_session() as session:
            try:
                # Fetch the job seeker and project from the database
                if user_id is None:
                    user_id = await info.context.get_current_user
                    if user_id is None:
                        raise ValueError("User not authenticated")

                job_seeker_sql = select(JobSeekerModel).where(JobSeekerModel.seeker_id == user_id)
                job_seeker = (await session.execute(job_seeker_sql)).first()

                if job_seeker is None:
                    return ApplicationResponse(
                        success=False,
                        project_application_id=None,
                        message="Job seeker not found"
                    )

                project_sql = select(ProjectModel).where(ProjectModel.project_id == project_id)
                project = (await session.execute(project_sql)).first()

                if project is None:
                    return ApplicationResponse(
                        success=False,
                        project_application_id=None,
                        message="Project not found"
                    )

                # Create a new project application with default status as 'pending'
                application = ProjectApplicationModel(
                    seeker_id=user_id,
                    project_id=project_id,
                    application_status='pending',
                    application_date=datetime.now().strftime('%m-%d-%Y'),
                    application_is_invited=application_is_invited
                )

                session.add(application)
                await session.commit()

                return ApplicationResponse(
                    success=True,
                    project_application_id=None,
                    message="Application created successfully"
                )

            except Exception as e:
                return ApplicationResponse(
                    success=False,
                    project_application_id=None,
                    message=str(e)
                )

    # Mutation to update an application
    @strawberry.mutation
    async def update_application(self, input: UpdateApplicationInput) -> ApplicationResponse:
        async with get_session() as session:
            try:
                # Fetch the project application from the database
                application = await session.get(ProjectApplicationModel, input.project_application_id)

                if application is None:
                    return ApplicationResponse(
                        success=False,
                        project_application_id=None,
                        message="Application not found"
                    )

                # Update the application status if provided
                if input.application_status is not None:
                    application.application_status = input.application_status

                await session.commit()

                return ApplicationResponse(
                    success=True,
                    project_application_id=None,
                    message="Application updated successfully"
                )

            except Exception as e:
                return ApplicationResponse(
                    success=False,
                    project_application_id=None,
                    message=str(e)
                )
