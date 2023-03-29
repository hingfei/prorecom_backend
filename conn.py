import csv
import asyncio
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String

SQLALCHEMY_DATABASE_URL = "sqlite+aiosqlite:///./database.db"
metadata = MetaData()
engine = create_async_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
async_session = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id: int = Column(Integer, primary_key=True, autoincrement=True)
    user_name: str = Column(String, nullable=False, unique=True)
    user_email: str = Column(String, nullable=False, unique=True)
    password: str = Column(String, nullable=False, unique=True)
    # books: list["Book"] = relationship("Book", lazy="joined", back_populates="author")


class Project(Base):
    __tablename__ = "projects"
    project_id: int = Column(Integer, primary_key=True, autoincrement=True)
    project_name: str = Column(String, nullable=False)
    company_name: str = Column(String, nullable=False)
    company_location: str = Column(String, nullable=True)
    project_types: str = Column(String, nullable=True)
    post_dates: str = Column(String, nullable=True)
    project_salary: str = Column(String, nullable=True)
    project_desc: str = Column(String, nullable=True)
    project_req: str = Column(String, nullable=True)
    project_skills: str = Column(String, nullable=True)
    project_exp_lvl: str = Column(String, nullable=True)


# Get session
@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:
        async with session.begin():
            try:
                yield session
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
        print(reader)
        async with get_session() as session:
            for row in reader:
                project = Project(
                    project_name=row['job_title'],
                    company_name=row['company_name'],
                    company_location=row['company_locations'],
                    project_types=row['job_types'],
                    post_dates=row['post_dates'],
                    project_salary=row['salary'],
                    project_desc=row['job_desc'],
                    project_req=row['job_req'],
                    project_skills=row['skills'],
                    project_exp_lvl=row['exp_lvl']
                )
                print(project)
                session.add(project)
            await session.commit()


if __name__ == "__main__":
    print("Dropping and creating tables")
    asyncio.run(_async_main())
    print("Done.")
    # asyncio.run(import_csv())
