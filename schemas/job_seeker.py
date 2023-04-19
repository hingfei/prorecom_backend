import strawberry
from sqlalchemy import select, delete, update
from typing import Optional, List
from conn import get_session, JobSeeker as JobSeekerModel, User as UserModel, Skill as SkillModel, JobSeekerSkills
from sqlalchemy.orm import selectinload
from strawberry.types import Info
from strawberry.file_uploads import Upload
import bcrypt

from schemas.skill import SkillType
from schemas.user import UserType


@strawberry.input
class CreateJobSeekerInput:
    user_name: str
    user_email: str
    password: str
    seeker_name: Optional[str]
    seeker_age: Optional[int]
    seeker_gender: Optional[str]
    seeker_birthdate: Optional[str] = None
    seeker_phone_no: Optional[int]
    seeker_street: Optional[str]
    seeker_city: Optional[str]
    seeker_state: Optional[str]
    seeker_highest_educ: Optional[str] = None
    seeker_resume: Optional[Upload] = None
    seeker_about: Optional[str] = None


@strawberry.input
class UpdateJobSeekerInput:
    seeker_id: strawberry.ID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    password: Optional[str] = None
    seeker_name: Optional[str] = None
    seeker_age: Optional[int] = None
    seeker_gender: Optional[str] = None
    seeker_birthdate: Optional[str] = None
    seeker_phone_no: Optional[int] = None
    seeker_street: Optional[str] = None
    seeker_city: Optional[str] = None
    seeker_state: Optional[str] = None
    seeker_highest_educ: Optional[str] = None
    seeker_resume: Optional[Upload] = None
    seeker_about: Optional[str] = None
    skills: Optional[List[int]] = None


@strawberry.type
class JobSeekerType:
    seeker_id: strawberry.ID
    users: Optional[UserType]
    seeker_name: Optional[str]
    seeker_age: Optional[int]
    seeker_gender: Optional[str]
    seeker_birthdate: Optional[str]
    seeker_phone_no: Optional[int]
    seeker_street: Optional[str]
    seeker_city: Optional[str]
    seeker_state: Optional[str]
    seeker_highest_educ: Optional[str]
    seeker_resume: Optional[Upload]
    seeker_about: Optional[str] = None
    skills: List[SkillType]


@strawberry.type
class JobSeekerResponse:
    success: bool
    job_seeker: Optional[JobSeekerType]
    message: Optional[str]


def hash_password(password: str) -> str:
    hashed_bytes = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
    return hashed_bytes.decode('utf-8')


@strawberry.type
class Query:
    @strawberry.field
    async def job_seeker_detail(self, info: Info, seeker_id: int) -> Optional[JobSeekerType]:
        async with get_session() as session:
            sql = select(JobSeekerModel).options(selectinload(JobSeekerModel.users),
                                                 selectinload(JobSeekerModel.skills)).where(
                JobSeekerModel.seeker_id == seeker_id)
            result = await session.execute(sql)
            job_seeker = result.scalars().first()
            return job_seeker if job_seeker else None

    @strawberry.field
    async def job_seeker_listing(self, info: Info) -> List[JobSeekerType]:
        async with get_session() as session:
            sql = select(JobSeekerModel).options(selectinload(JobSeekerModel.users),
                                                 selectinload(JobSeekerModel.skills))
            job_seekers = await session.execute(sql)
            return job_seekers.scalars().unique().all()


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_job_seeker(self, input: CreateJobSeekerInput) -> JobSeekerResponse:

        async with get_session() as session:
            try:
                sql = select(UserModel).where(UserModel.user_name == input.user_name)
                job_seeker = (await session.execute(sql)).first()

                if job_seeker is not None:
                    return JobSeekerResponse(success=False, job_seeker=None,
                                             message=f"Username already exist.")

                sql = select(UserModel).where(UserModel.user_email == input.user_email)
                job_seeker = (await session.execute(sql)).first()

                if job_seeker is not None:
                    return JobSeekerResponse(success=False, job_seeker=None,
                                             message=f"Email already exist.")

                hashed_password = hash_password(input.password)

                job_seeker = JobSeekerModel(
                    user_name=input.user_name,
                    user_email=input.user_email,
                    password=hashed_password,
                    seeker_name=input.seeker_name,
                    seeker_age=input.seeker_age,
                    seeker_gender=input.seeker_gender,
                    seeker_birthdate=input.seeker_birthdate if input.seeker_birthdate else None,
                    seeker_phone_no=input.seeker_phone_no,
                    seeker_street=input.seeker_street,
                    seeker_city=input.seeker_city,
                    seeker_state=input.seeker_state,
                    seeker_highest_educ=input.seeker_highest_educ if input.seeker_highest_educ else None,
                    seeker_resume=input.seeker_resume if input.seeker_resume else None,
                    seeker_about=input.seeker_about if input.seeker_about else None,
                )

                session.add(job_seeker)
                await session.commit()

                return JobSeekerResponse(
                    success=True, job_seeker=job_seeker, message="Account created"
                )

            except Exception as e:
                # Return an error response with the error message
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    @strawberry.mutation
    async def update_job_seeker(self, input: UpdateJobSeekerInput) -> JobSeekerResponse:

        async with get_session() as session:
            job_seeker = await session.get(JobSeekerModel, input.seeker_id)

            if job_seeker is None:
                return JobSeekerResponse(success=False, job_seeker=None,
                                         message=f"Account not found.")

            if input.user_name is not None:
                job_seeker.user_name = input.user_name
            if input.user_email is not None:
                job_seeker.user_email = input.user_email
            if input.seeker_name is not None:
                job_seeker.seeker_name = input.seeker_name
            if input.seeker_age is not None:
                job_seeker.seeker_age = input.seeker_age
            if input.seeker_gender is not None:
                job_seeker.seeker_gender = input.seeker_gender
            if input.seeker_birthdate is not None:
                job_seeker.seeker_birthdate = input.seeker_birthdate
            if input.seeker_phone_no is not None:
                job_seeker.seeker_phone_no = input.seeker_phone_no
            if input.seeker_street is not None:
                job_seeker.seeker_street = input.seeker_street
            if input.seeker_city is not None:
                job_seeker.seeker_city = input.seeker_city
            if input.seeker_state is not None:
                job_seeker.seeker_state = input.seeker_state
            if input.seeker_highest_educ is not None:
                job_seeker.seeker_highest_educ = input.seeker_highest_educ
            if input.seeker_resume is not None:
                job_seeker.seeker_resume = input.seeker_resume
            if input.seeker_about is not None:
                job_seeker.seeker_about = input.seeker_about
            if input.skills is not None:
                # Remove all existing skills from job seeker
                await session.execute(delete(JobSeekerSkills).where(JobSeekerSkills.seeker_id == job_seeker.seeker_id))

                # Add skills to jobseeker
                for skill_id in input.skills:
                    skill = await session.execute(select(SkillModel).where(SkillModel.skill_id == skill_id))
                    skill = skill.scalar()
                    # if skill is None:
                    #     skill = SkillModel(skill_name=skill_name)
                    #     session.add(skill)
                    #     await session.flush()
                    job_seeker_skill = JobSeekerSkills(seeker_id=job_seeker.seeker_id, skill_id=skill.skill_id)
                    session.add(job_seeker_skill)

            try:
                await session.commit()
                return JobSeekerResponse(
                    success=True, job_seeker=job_seeker, message="Account has been updated."
                )
            except Exception as e:
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    @strawberry.mutation
    async def delete_job_seeker(self, info: Info, seeker_id: int) -> JobSeekerResponse:
        async with get_session() as session:
            try:
                # delete job seeker from the database
                delete_query = delete(JobSeekerModel).where(JobSeekerModel.seeker_id == seeker_id)
                deleted_job_seeker = await session.execute(delete_query)
                if deleted_job_seeker.rowcount == 0:
                    return JobSeekerResponse(success=False, job_seeker=None,
                                             message=f"Account not found.")
                else:
                    delete_query = delete(UserModel).where(UserModel.user_id == seeker_id)
                    await session.execute(delete_query)

                await session.commit()

                return JobSeekerResponse(success=True, job_seeker=None, message="Account deleted successfully")

            except Exception as e:
                # Return an error response with the error message
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    @strawberry.mutation
    async def update_job_seeker_password(self, info: Info, current_password: str,
                                         new_password: str, user_id: int) -> JobSeekerResponse:
        async with get_session() as session:
            try:
                # Get the job seeker by the current user ID
                user = await session.get(UserModel, user_id)
                if not user:
                    return JobSeekerResponse(success=False, job_seeker=None,
                                             message=f"Job Seeker not found.")

                # Verify the current password
                if not bcrypt.checkpw(current_password.encode('utf-8'), user.password.encode('utf-8')):
                    return JobSeekerResponse(success=False, job_seeker=None,
                                             message=f"Invalid current password.")

                # Update the password
                hashed_password = hash_password(new_password)
                if user.password is not None:
                    user.password = hashed_password

                await session.commit()

                return JobSeekerResponse(success=True, job_seeker=None, message="Password updated successfully")

            except Exception as e:
                # Return an error response with the error message
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))
