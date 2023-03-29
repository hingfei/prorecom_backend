import strawberry
from sqlalchemy import select, delete
from typing import Optional
# from models import project
from conn import get_session, Project as ProjectModel
from strawberry.types import Info


@strawberry.type
class Project:
    project_id: strawberry.ID
    project_name: str
    company_name: str
    company_location: str
    project_types: str
    post_dates: str
    project_salary: str
    project_desc: str
    project_req: str
    project_skills: str
    project_exp_lvl: str

    @classmethod
    def marshal(cls, model: ProjectModel) -> "Project":
        return cls(
            project_id=strawberry.ID(str(model.project_id)),
            project_name= model.project_name,
            company_name= model.company_name,
            company_location= model.company_location,
            project_types= model.project_types,
            post_dates= model.post_dates,
            project_salary= model.project_salary,
            project_desc= model.project_desc,
            project_req= model.project_req,
            project_skills= model.project_skills,
            project_exp_lvl= model.project_exp_lvl,
        )


# @strawberry.type
# class UserExists:
#     message: str = "User with this name already exist"


@strawberry.type
class ProjectUpdateMessage:
    message: str


@strawberry.type
class ProjectNotFound:
    message: str = "Project not found"


@strawberry.type
class ProjectDeleteMessage:
    message: str = "Project deleted successfully"


# Responses
# AddProjectResponse = strawberry.union("AddProjectResponse", Project)
UpdateProjectResponse = strawberry.union("UpdateProjectResponse", (ProjectUpdateMessage, ProjectNotFound))
DeleteProjectResponse = strawberry.union("DeleteProjectResponse", (ProjectDeleteMessage, ProjectNotFound))


@strawberry.type
class Query:
    @strawberry.field
    async def project_detail(self, info: Info, project_id: int) -> Optional[Project]:
        async with get_session() as s:
            sql = select(ProjectModel).where(ProjectModel.project_id == project_id)
            db_project = (await s.execute(sql)).scalars().first()
            return Project.marshal(db_project) if db_project else None

    @strawberry.field
    async def project_listing(self) -> list[Project]:
        async with get_session() as s:
            sql = select(ProjectModel).order_by(ProjectModel.project_id)
            db_project = (await s.execute(sql)).scalars().unique().all()
        return [Project.marshal(loc) for loc in db_project]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_project(self, project_name: str, company_name: str, company_location: str, project_types: str,
                             post_dates: str, project_salary: str, project_desc: str, project_req: str,
                             project_skills: str, project_exp_lvl: str) -> Project:
        async with get_session() as s:
            db_project = ProjectModel(project_name=project_name, company_name=company_name,
                                      company_location=company_location, project_types=project_types,
                                      post_dates=post_dates, project_salary=project_salary,
                                      project_desc=project_desc, project_req=project_req,
                                      project_skills=project_skills,
                                      project_exp_lvl=project_exp_lvl)
            s.add(db_project)
            await s.commit()
        return Project.marshal(db_project)

    @strawberry.mutation
    async def update_project(self, project_id: int, project_name: Optional[str] = None,
                             company_name: Optional[str] = None,
                             company_location: Optional[str] = None, project_types: Optional[str] = None,
                             post_dates: Optional[str] = None, project_salary: Optional[str] = None,
                             project_desc: Optional[str] = None, project_req: Optional[str] = None,
                             project_skills: Optional[str] = None,
                             project_exp_lvl: Optional[str] = None) -> UpdateProjectResponse:
        async with get_session() as s:
            db_project = await s.get(ProjectModel, project_id)
            if db_project is None:
                return ProjectNotFound()

            if project_name is not None:
                db_project.project_name = project_name
            if company_name is not None:
                db_project.company_name = company_name
            if company_location is not None:
                db_project.company_location = company_location
            if project_types is not None:
                db_project.project_types = project_types
            if post_dates is not None:
                db_project.post_dates = post_dates
            if project_salary is not None:
                db_project.project_salary = project_salary
            if project_desc is not None:
                db_project.project_desc = project_desc
            if project_req is not None:
                db_project.project_req = project_req
            if project_skills is not None:
                db_project.project_skills = project_skills
            if project_exp_lvl is not None:
                db_project.project_exp_lvl = project_exp_lvl

            await s.commit()

        return ProjectUpdateMessage(message=f"Project with id {project_id} updated successfully")

    @strawberry.mutation
    async def delete_project(self, project_id: int) -> DeleteProjectResponse:
        async with get_session() as s:
            sql = delete(ProjectModel).where(ProjectModel.id == project_id)
            db_user = await s.execute(sql)
            if db_user.rowcount == 0:
                return ProjectNotFound()

            await s.commit()

        return ProjectDeleteMessage
