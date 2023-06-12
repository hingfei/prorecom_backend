from datetime import datetime
import strawberry
from pydantic.class_validators import Optional
from sqlalchemy import select
from conn import get_session, JobSeeker as JobSeekerModel, Project as ProjectModel, \
    ProjectApplication as ProjectApplicationModel


@strawberry.input
class CreateApplicationInput:
    seeker_id: strawberry.ID
    project_id: strawberry.ID


@strawberry.input
class UpdateApplicationInput:
    project_application_id: strawberry.ID
    application_status: Optional[str] = None


@strawberry.type
class JobSeekerResponse:
    success: bool
    application_id: int
    message: Optional[str]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_application(
            self,
            input: CreateApplicationInput
    ) -> JobSeekerResponse:
        async with get_session() as session:
            try:
                # Fetch the job seeker and project from the database
                job_seeker_sql = select(JobSeekerModel).where(JobSeekerModel.seeker_id == input.seeker_id)
                job_seeker = (await session.execute(job_seeker_sql)).first()

                if job_seeker is None:
                    return JobSeekerResponse(
                        success=False,
                        application_id=None,
                        message="Job seeker not found"
                    )

                project_sql = select(ProjectModel).where(ProjectModel.project_id == input.project_id)
                project = (await session.execute(project_sql)).first()

                if project is None:
                    return JobSeekerResponse(
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

                return JobSeekerResponse(
                    success=True,
                    application_id=application.project_application_id,
                    message="Application created successfully"
                )

            except Exception as e:
                return JobSeekerResponse(
                    success=False,
                    application_id=None,
                    message=str(e)
                )
