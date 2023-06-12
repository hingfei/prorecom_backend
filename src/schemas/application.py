from datetime import datetime
from typing import List

import strawberry
from pydantic.class_validators import Optional
from sqlalchemy import select
from conn import get_session, JobSeeker as JobSeekerModel, Project as ProjectModel, \
    ProjectApplication as ProjectApplicationModel
from src.schemas.job_seeker import JobSeekerType
from src.schemas.project import ProjectType


@strawberry.input
class CreateApplicationInput:
    seeker_id: strawberry.ID
    project_id: strawberry.ID


@strawberry.input
class UpdateApplicationInput:
    project_application_id: strawberry.ID
    application_status: Optional[str] = None


@strawberry.type
class ApplicationType:
    project_application_id: strawberry.ID
    seeker_id: strawberry.ID
    project_id: strawberry.ID
    application_status: Optional[str]
    job_seeker: Optional[JobSeekerType]
    project: Optional[ProjectType]


@strawberry.type
class ApplicationResponse:
    success: bool
    application_id: int
    message: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    async def get_job_seeker_applications(self, seeker_id: strawberry.ID) -> List[ApplicationType]:
        async with get_session() as session:
            try:
                # Fetch the job seeker's applications
                applications_sql = select(ProjectApplicationModel).where(
                    ProjectApplicationModel.seeker_id == int(seeker_id)
                )
                applications = await session.execute(applications_sql)

                return applications.scalars().all()

            except Exception as e:
                # Return an empty list if an error occurs
                return []

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


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_application(self, input: CreateApplicationInput) -> ApplicationResponse:
        async with get_session() as session:
            try:
                # Fetch the job seeker and project from the database
                job_seeker_sql = select(JobSeekerModel).where(JobSeekerModel.seeker_id == input.seeker_id)
                job_seeker = (await session.execute(job_seeker_sql)).first()

                if job_seeker is None:
                    return ApplicationResponse(
                        success=False,
                        application_id=None,
                        message="Job seeker not found"
                    )

                project_sql = select(ProjectModel).where(ProjectModel.project_id == input.project_id)
                project = (await session.execute(project_sql)).first()

                if project is None:
                    return ApplicationResponse(
                        success=False,
                        application_id=None,
                        message="Project not found"
                    )

                # Create a new project application with default status as 'pending'
                application = ProjectApplicationModel(
                    job_seeker=job_seeker,
                    project=project,
                    application_status='pending',
                    application_date=datetime.now().strftime('%m-%d-%Y')
                )

                session.add(application)
                await session.commit()

                return ApplicationResponse(
                    success=True,
                    application_id=application.project_application_id,
                    message="Application created successfully"
                )

            except Exception as e:
                return ApplicationResponse(
                    success=False,
                    application_id=None,
                    message=str(e)
                )

    @strawberry.mutation
    async def update_application(self, input: UpdateApplicationInput) -> ApplicationResponse:
        async with get_session() as session:
            try:
                # Fetch the project application from the database
                application_sql = select(ProjectApplicationModel).where(
                    ProjectApplicationModel.project_application_id == input.project_application_id
                )
                application = (await session.execute(application_sql)).first()

                if application is None:
                    return ApplicationResponse(
                        success=False,
                        application_id=None,
                        message="Application not found"
                    )

                # Update the application status if provided
                if input.application_status is not None:
                    application.application_status = input.application_status

                await session.commit()

                return ApplicationResponse(
                    success=True,
                    application_id=application.project_application_id,
                    message="Application updated successfully"
                )

            except Exception as e:
                return ApplicationResponse(
                    success=False,
                    application_id=None,
                    message=str(e)
                )
