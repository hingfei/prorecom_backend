import csv
import asyncio
from sqlalchemy import Table, MetaData, ForeignKey, LargeBinary, create_engine, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, relationship, selectinload
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional
from sqlalchemy.orm import declarative_base, Mapped
from sqlalchemy import Column, Integer, String, select

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./database.db"
metadata = MetaData()
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}, echo=True)
async_sessionmaker = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    user_id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_name: str = Column(String, nullable=False, unique=True)
    user_email: Optional[str] = Column(String, nullable=False, unique=True)
    password: str = Column(String, nullable=False)
    user_type: str = Column(String, nullable=False)
    __mapper_args__ = {"polymorphic_on": user_type, 'polymorphic_identity': 'users'}


class JobSeekerSkills(Base):
    __tablename__ = 'job_seeker_skills'

    seeker_id = Column(Integer, ForeignKey('job_seekers.seeker_id'), primary_key=True)
    skill_id = Column(Integer, ForeignKey('skills.skill_id'), primary_key=True)


job_seeker_skills = Table('job_seeker_skills', Base.metadata,
                          Column('seeker_id', Integer, ForeignKey('job_seekers.seeker_id'), primary_key=True),
                          Column('skill_id', String, ForeignKey('skills.skill_id'), primary_key=True),
                          extend_existing=True
                          )


class JobSeeker(User):
    __tablename__ = "job_seekers"
    seeker_id: int = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    seeker_name: str = Column(String, nullable=True)
    seeker_age: int = Column(Integer, nullable=True)
    seeker_gender: str = Column(String, nullable=True)
    seeker_birthdate: Optional[str] = Column(String, nullable=True)
    seeker_phone_no: int = Column(Integer, nullable=True)
    seeker_street: str = Column(String, nullable=True)
    seeker_city: str = Column(String, nullable=True)
    seeker_state: str = Column(String, nullable=True)
    seeker_highest_educ: Optional[str] = Column(String, nullable=True)
    seeker_resume: Optional[bytes] = Column(LargeBinary, nullable=True)
    seeker_about: Optional[str] = Column(String, nullable=True)
    users = relationship("User", backref="job_seekers")
    skills = relationship("Skill", secondary=job_seeker_skills, backref='job_seekers')
    __mapper_args__ = {"polymorphic_identity": "job_seekers"}


class Company(User):
    __tablename__ = "companies"
    company_id: int = Column(Integer, ForeignKey("users.user_id"), primary_key=True)
    company_name: str = Column(String, nullable=True)
    company_founder: str = Column(String, nullable=True)
    company_size: str = Column(String, nullable=True)
    company_desc: str = Column(String, nullable=True)
    company_street: str = Column(String, nullable=True)
    company_city: str = Column(String, nullable=True)
    company_state: str = Column(String, nullable=True)
    users = relationship("User", backref="companies")
    __mapper_args__ = {"polymorphic_identity": "companies"}


class ProjectSkills(Base):
    __tablename__ = 'project_skills'

    project_id = Column(Integer, ForeignKey('projects.project_id'), primary_key=True)
    skill_id = Column(Integer, ForeignKey('skills.skill_id'), primary_key=True)


project_skills = Table('project_skills', Base.metadata,
                       Column('project_id', Integer, ForeignKey('projects.project_id'), primary_key=True),
                       Column('skill_id', Integer, ForeignKey('skills.skill_id'), primary_key=True),
                       extend_existing=True
                       )


class Project(Base):
    __tablename__ = "projects"
    project_id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_name: str = Column(String, nullable=False)
    company_id: int = Column(Integer, ForeignKey("companies.company_id"), nullable=False)
    company: Mapped[Company] = relationship("Company", backref="projects")
    project_types: str = Column(String, nullable=True)
    post_dates: str = Column(String, nullable=True)
    project_salary: str = Column(String, nullable=True)
    project_desc: str = Column(String, nullable=True)
    project_req: str = Column(String, nullable=True)
    project_exp_lvl: str = Column(String, nullable=True)
    skills = relationship(
        "Skill",
        secondary=project_skills,
        backref="projects"
    )


class Skill(Base):
    __tablename__ = "skills"
    skill_id: int = Column(Integer, primary_key=True, autoincrement=True)
    skill_name: str = Column(String, nullable=False, unique=True)


@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_sessionmaker() as session:
        async with session.begin():
            try:
                yield session
                # await session.commit()
            except:
                await session.rollback()
                raise
            finally:
                await session.close()


async def _async_main():
    async with engine.begin() as connect:
        await connect.run_sync(Base.metadata.drop_all)
        await connect.run_sync(Base.metadata.create_all)
    await engine.dispose()


async def import_csv():
    with open('projects_list.csv', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        async with get_session() as session:
            for row in reader:
                # Check if the company already exists in the database
                sql = select(Company).where(Company.company_name == row['company_name'])
                company = await session.execute(sql)
                company = company.scalar()
                if company is None:
                    # If the company doesn't exist, create a new one
                    company = Company(
                        user_name=row['company_name'].lower().replace(' ', ''),  # Use company name as the username
                        user_email=row['company_name'].lower().replace(' ', ''),
                        password=row['company_name'].lower().replace(' ', ''),
                        company_name=row['company_name'],
                        company_street=row['company_locations']
                    )
                    session.add(company)
                    await session.flush()  # Flush the session to get the new company ID
                    await session.refresh(company)
                else:
                    print("exists")
                    # company = company.company_id
                    print("run here")

                # Split the project skills into a list of skill names
                skills = row['skills'].split('\n')
                print("exists")
                # Create a new project for the company
                project = Project(
                    project_name=row['job_title'],
                    company_id=company.company_id,
                    project_types=row['job_types'],
                    post_dates=row['post_dates'],
                    project_salary=row['salary'],
                    project_desc=row['job_desc'],
                    project_req=row['job_req'],
                    project_exp_lvl=row['exp_lvl']
                )

                # Add each skill to the project
                print('here?')
                for skill_name in skills:
                    if skill_name != '':
                        skill = await session.execute(select(Skill).where(Skill.skill_name == skill_name))
                        skill = skill.scalar()
                        if skill is None:
                            skill = Skill(skill_name=skill_name)
                            session.add(skill)
                        project.skills.append(skill)
                print('here?')
                session.add(project)

            await session.commit()


async def add_column():
    async with get_session() as session:
        # Migrate the database as needed
        await session.execute(text('alter table job_seekers add column seeker_about String'))
        await session.commit()


if __name__ == "__main__":
    # print("Dropping and creating tables")
    # asyncio.run(_async_main())
    # asyncio.run(import_csv())
    # asyncio.run(add_column())
    print("Done.")
