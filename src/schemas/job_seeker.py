import json
import os
import uuid

import strawberry
from sqlalchemy import select, delete, or_, and_
from typing import Optional, List
from conn import get_session, JobSeeker as JobSeekerModel, User as UserModel, Skill as SkillModel, JobSeekerSkills, \
    Education as EducationModel
from sqlalchemy.orm import selectinload
from strawberry.types import Info
from strawberry.file_uploads import Upload
import bcrypt
from src.schemas.skill import SkillType
from src.schemas.user import UserType
from src.schemas.education import EducationType, EducationInput
from src.recommendations.project_recom_engine import preprocess_skillsets
from src.recommendations.candidates_recom_engine import cluster_candidates, get_candidates_recommendations
import src.settings as settings
import numpy as np


# Input class for creating a job seeker
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
    seeker_resume: Optional[Upload] = None
    seeker_about: Optional[str] = None


# Input class for updating a job seeker
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
    seeker_resume: Optional[Upload] = None
    seeker_about: Optional[str] = None
    seeker_is_open_for_work: Optional[bool] = None
    skills: Optional[List[int]] = None
    educations: Optional[List[EducationInput]] = None


# Type definition for the JobSeeker
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
    seeker_resume: Optional[str]
    seeker_profile_pic: Optional[str]
    seeker_about: Optional[str]
    seeker_is_open_for_work: Optional[bool]
    skills: List[SkillType]
    educations: List[EducationType]
    similarity_score: Optional[float] = None


# Type definition for the JobSeeker response
@strawberry.type
class JobSeekerResponse:
    success: bool
    job_seeker: Optional[JobSeekerType]
    message: Optional[str]


# Type definition for the Query class
@strawberry.type
class Query:
    # Query to get job seeker details based on seeker id
    @strawberry.field
    async def job_seeker_detail(self, info: Info, seeker_id: int) -> Optional[JobSeekerType]:
        async with get_session() as session:
            sql = select(JobSeekerModel).options(selectinload(JobSeekerModel.users),
                                                 selectinload(JobSeekerModel.skills),
                                                 selectinload(JobSeekerModel.educations)).where(
                JobSeekerModel.seeker_id == seeker_id)
            result = await session.execute(sql)
            job_seeker = result.scalars().first()
            return job_seeker if job_seeker else None

    # Query to get job seeker listing
    @strawberry.field
    async def job_seeker_listing(self, info: Info) -> List[JobSeekerType]:
        async with get_session() as session:
            sql = select(JobSeekerModel).options(selectinload(JobSeekerModel.users),
                                                 selectinload(JobSeekerModel.skills),
                                                 selectinload(JobSeekerModel.educations))
            job_seekers = await session.execute(sql)
            return job_seekers.scalars().unique().all()

    # Query to search job seekers based on keywords
    @strawberry.field
    async def search_job_seekers(self, info: Info, search_keyword: str) -> List[JobSeekerType]:
        async with get_session() as session:
            # Search for job seekers based on the keyword and skills
            subquery = select(JobSeekerModel.seeker_id).join(JobSeekerModel.skills).where(
                SkillModel.skill_name.ilike(f"%{search_keyword}%")
            )
            query = select(JobSeekerModel).options(
                selectinload(JobSeekerModel.users),
                selectinload(JobSeekerModel.skills),
                selectinload(JobSeekerModel.educations)
            ).where(
                and_(
                    or_(
                        JobSeekerModel.seeker_name.ilike(f"%{search_keyword}%"),
                        JobSeekerModel.seeker_about.ilike(f"%{search_keyword}%"),
                        JobSeekerModel.seeker_street.ilike(f"%{search_keyword}%"),
                        JobSeekerModel.seeker_city.ilike(f"%{search_keyword}%"),
                        JobSeekerModel.seeker_state.ilike(f"%{search_keyword}%"),
                        JobSeekerModel.seeker_id.in_(subquery)
                    ),
                    JobSeekerModel.seeker_is_open_for_work == True
                )
            )
            result = await session.execute(query)
            job_seekers = result.scalars().unique().all()

            return job_seekers

    # Query to get recommended job seeker listing based on project id
    @strawberry.field
    async def recommended_job_seeker_listing(self, info: Info, project_id: int) -> List[JobSeekerType]:
        async with get_session() as session:
            ranked_candidates = await get_candidates_recommendations(project_id)
            print('ranked', ranked_candidates)
            candidate_ids = [candidate_id for candidate_id, _ in ranked_candidates[:10]]
            print('ids', candidate_ids)
            query = select(JobSeekerModel).options(
                selectinload(JobSeekerModel.users),
                selectinload(JobSeekerModel.skills),
                selectinload(JobSeekerModel.educations)
            ).where(JobSeekerModel.seeker_id.in_(candidate_ids))
            result = await session.execute(query)
            job_seekers = result.scalars().all()

            # Create a dictionary to map job seeker id to the job seeker object
            job_seeker_dict = {job_seeker.seeker_id: job_seeker for job_seeker in job_seekers}

            # Reorder the job seekers based on the candidate_ids sequence
            ordered_job_seekers = []
            for candidate_id, similarity_score in ranked_candidates:
                job_seeker = job_seeker_dict.get(candidate_id)
                if job_seeker:
                    job_seeker.similarity_score = similarity_score
                    ordered_job_seekers.append(job_seeker)

            return ordered_job_seekers


# Type definition for the Mutation class
@strawberry.type
class Mutation:
    # Mutation to create a job seeker
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

                hashed_password = settings.hash_password(input.password)

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
                    seeker_resume=input.seeker_resume if input.seeker_resume else None,
                    seeker_about=input.seeker_about if input.seeker_about else None,
                )

                session.add(job_seeker)
                await session.commit()

                return JobSeekerResponse(
                    success=True, job_seeker=job_seeker, message="Account is created"
                )

            except Exception as e:
                # Return an error response with the error message
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    # Mutation to update a job seeker
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
            if input.seeker_resume is not None:
                job_seeker.seeker_resume = input.seeker_resume
            if input.seeker_about is not None:
                job_seeker.seeker_about = input.seeker_about
            if input.seeker_is_open_for_work is not None:
                job_seeker.seeker_is_open_for_work = input.seeker_is_open_for_work
            if input.skills is not None:
                skill_list = []
                # Remove all existing skills from job seeker
                await session.execute(delete(JobSeekerSkills).where(JobSeekerSkills.seeker_id == job_seeker.seeker_id))

                # Add skills to jobseeker
                for skill_id in input.skills:
                    skill = await session.execute(select(SkillModel).where(SkillModel.skill_id == skill_id))
                    skill = skill.scalar()
                    skill_list.append(skill.skill_name)
                    job_seeker_skill = JobSeekerSkills(seeker_id=job_seeker.seeker_id, skill_id=skill.skill_id)
                    session.add(job_seeker_skill)

                # Update skillset vector
                skills_processed = preprocess_skillsets(skill_list)
                skillset_size = settings.ft_model.get_dimension()
                if len(skills_processed) > 0:
                    skillset_vector = np.mean([settings.ft_model.get_word_vector(skill) for skill in skills_processed],
                                              axis=0)
                else:
                    skillset_vector = np.zeros(skillset_size)
                job_seeker.seeker_skillset_vector = json.dumps(skillset_vector.tolist())

            # Update educations of job seeker
            if input.educations is not None:
                if len(input.educations) == 0:
                    # job_seeker.educations = []
                    await session.execute(
                        delete(EducationModel).where(EducationModel.job_seeker_id == job_seeker.seeker_id))
                else:
                    for education_input in input.educations:
                        education = await session.get(EducationModel, education_input.education_id)
                        if education is not None:
                            if education_input.education_level is not None:
                                education.education_level = education_input.education_level
                            if education_input.education_institution is not None:
                                education.education_institution = education_input.education_institution
                            if education_input.field_of_study is not None:
                                education.field_of_study = education_input.field_of_study
                            if education_input.graduation_year is not None:
                                education.graduation_year = education_input.graduation_year
                            if education_input.description is not None:
                                education.description = education_input.description
                            if education_input.grade is not None:
                                education.grade = education_input.grade
                        else:
                            job_seeker_education = EducationModel(
                                job_seeker_id=job_seeker.seeker_id,
                                education_level=education_input.education_level,
                                education_institution=education_input.education_institution,
                                field_of_study=education_input.field_of_study,
                                graduation_year=education_input.graduation_year,
                                description=education_input.description,
                                grade=education_input.grade
                            )
                            session.add(job_seeker_education)

            try:
                await session.commit()
                await cluster_candidates(refresh=True)
                return JobSeekerResponse(
                    success=True, job_seeker=job_seeker, message="Account has been updated."
                )
            except Exception as e:
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    # Mutation to delete a job seeker
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
                await cluster_candidates(refresh=True)

                return JobSeekerResponse(success=True, job_seeker=None, message="Account deleted successfully")

            except Exception as e:
                # Return an error response with the error message
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    # Mutation to update a job seeker's password
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
                hashed_password = settings.hash_password(new_password)
                if user.password is not None:
                    user.password = hashed_password

                await session.commit()

                return JobSeekerResponse(success=True, job_seeker=None, message="Password updated successfully")

            except Exception as e:
                # Return an error response with the error message
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    # Mutation to upload a job seeker's resume
    @strawberry.mutation
    async def upload_resume(self, seeker_id: int, seeker_resume: Upload) -> JobSeekerResponse:
        async with get_session() as session:
            try:
                # Retrieve the job seeker from the database
                job_seeker = await session.get(JobSeekerModel, seeker_id)
                if not job_seeker:
                    return JobSeekerResponse(success=False, job_seeker=None,
                                             message=f"Job Seeker not found.")

                project_directory = os.path.join("..", "prorecom_frontend", "public", "images", "jobseekers", "resumes")

                # Generate a unique filename
                file_extension = seeker_resume.filename.split(".")[-1]
                unique_filename = f"{seeker_id}_resume_{uuid.uuid4().hex}.{file_extension}"

                # Delete the old resume file if it exists
                if job_seeker.seeker_resume:
                    old_file_path = os.path.join(project_directory, job_seeker.seeker_resume)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                # Save the new resume file
                file_path = os.path.join(project_directory, unique_filename)
                with open(file_path, "wb") as file:
                    file.write(await seeker_resume.read())

                # Update the seeker_resume column in the JobSeeker table
                job_seeker.seeker_resume = unique_filename
                await session.commit()

                return JobSeekerResponse(success=True, job_seeker=None, message="Resume uploaded successfully")

            except Exception as e:
                # Handle the error and return an appropriate response
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))

    # Mutation to upload a job seeker's profile picture
    @strawberry.mutation
    async def upload_seeker_profile_pic(self, user_id: int, profile_pic: Upload) -> JobSeekerResponse:
        async with get_session() as session:
            try:
                # Retrieve the job seeker from the database
                job_seeker = await session.get(JobSeekerModel, user_id)
                if not job_seeker:
                    return JobSeekerResponse(success=False, job_seeker=None, message=f"Job Seeker not found.")

                project_directory = os.path.join("..", "prorecom_frontend", "public", "images", "profile-pics")

                # Generate a unique filename
                file_extension = profile_pic.filename.split(".")[-1]
                unique_filename = f"{user_id}_profile_{uuid.uuid4().hex}.{file_extension}"

                # Delete the old profile picture file if it exists
                if job_seeker.seeker_profile_pic:
                    old_file_path = os.path.join(project_directory, job_seeker.seeker_profile_pic)
                    if os.path.exists(old_file_path):
                        os.remove(old_file_path)

                # Save the new profile picture file
                file_path = os.path.join(project_directory, unique_filename)
                with open(file_path, "wb") as file:
                    file.write(await profile_pic.read())

                # Update the seeker_profile_pic column in the JobSeeker table
                job_seeker.seeker_profile_pic = unique_filename
                await session.commit()

                return JobSeekerResponse(success=True, job_seeker=None, message="Profile picture uploaded successfully")

            except Exception as e:
                # Handle the error and return an appropriate response
                return JobSeekerResponse(success=False, job_seeker=None, message=str(e))
