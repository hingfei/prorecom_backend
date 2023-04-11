import strawberry
from typing import Optional, List

from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from strawberry.types import Info

from conn import get_session, Company as CompanyModel, User as UserModel
from schemas.user import UserType


@strawberry.input
class CreateCompanyInput:
    user_name: str
    user_email: str
    password: str
    company_name: Optional[str]
    company_founder: Optional[str]
    company_size: Optional[str]
    company_desc: Optional[str]
    company_street: Optional[str]
    company_city: Optional[str]
    company_state: Optional[str]


@strawberry.input
class UpdateCompanyInput:
    company_id: strawberry.ID
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    password: Optional[str] = None
    company_name: Optional[str] = None
    company_founder: Optional[str] = None
    company_size: Optional[str] = None
    company_desc: Optional[str] = None
    company_street: Optional[str] = None
    company_city: Optional[str] = None
    company_state: Optional[str] = None


@strawberry.type
class CompanyType:
    company_id: strawberry.ID
    users: Optional[UserType]
    company_name: Optional[str]
    company_founder: Optional[str]
    company_size: Optional[str]
    company_desc: Optional[str]
    company_street: Optional[str]
    company_city: Optional[str]
    company_state: Optional[str]


@strawberry.type
class CompanyResponse:
    success: bool
    company: Optional[CompanyType] = None
    message: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    async def company_detail(self, info: Info, company_id: int) -> Optional[CompanyType]:
        async with get_session() as session:
            sql = select(CompanyModel).options(selectinload(CompanyModel.users)).where(
                CompanyModel.company_id == company_id)
            result = await session.execute(sql)
            company = result.scalars().first()
            return company if company else None

    @strawberry.field
    async def company_listing(self, info: Info) -> List[CompanyType]:
        async with get_session() as session:
            sql = select(CompanyModel).options(selectinload(CompanyModel.users))
            company = await session.execute(sql)
            return company.scalars().unique().all()


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_company(self, input: CreateCompanyInput) -> CompanyResponse:

        async with get_session() as session:
            try:
                sql = select(UserModel).where(UserModel.user_name == input.user_name)
                company = (await session.execute(sql)).first()

                if company is not None:
                    return CompanyResponse(success=False, company=None,
                                           message=f"Username already exist.")

                sql = select(UserModel).where(UserModel.user_email == input.user_email)
                company = (await session.execute(sql)).first()

                if company is not None:
                    return CompanyResponse(success=False, company=None,
                                           message=f"Email already exist.")

                company = CompanyModel(
                    user_name=input.user_name,
                    user_email=input.user_email,
                    password=input.password,
                    company_name=input.company_name,
                    company_founder=input.company_founder,
                    company_size=input.company_size,
                    company_desc=input.company_desc,
                    company_street=input.company_street,
                    company_city=input.company_city,
                    company_state=input.company_state
                )

                session.add(company)
                await session.commit()

                return CompanyResponse(
                    success=True, company=company, message="Account is created."
                )

            except Exception as e:
                # Return an error response with the error message
                return CompanyResponse(success=False, company=None, message=str(e))

    @strawberry.mutation
    async def update_company(self, input: UpdateCompanyInput) -> CompanyResponse:

        async with get_session() as session:
            company = await session.get(CompanyModel, input.company_id)

            if company is None:
                return CompanyResponse(success=False, company=None,
                                       message=f"Account not found.")

            if input.user_name is not None:
                company.user_name = input.user_name
            if input.user_email is not None:
                company.user_email = input.user_email
            if input.password is not None:
                company.password = input.password
            if input.company_name is not None:
                company.company_name = input.company_name
            if input.company_founder is not None:
                company.company_founder = input.company_founder
            if input.company_size is not None:
                company.company_size = input.company_size
            if input.company_desc is not None:
                company.company_desc = input.company_desc
            if input.company_street is not None:
                company.company_street = input.company_street
            if input.company_city is not None:
                company.company_city = input.company_city
            if input.company_state is not None:
                company.company_state = input.company_state

            try:
                await session.commit()
                return CompanyResponse(
                    success=True, company=company, message="Account has been updated."
                )
            except Exception as e:
                return CompanyResponse(success=False, company=None, message=str(e))

    @strawberry.mutation
    async def delete_company(self, info: Info, company_id: int) -> CompanyResponse:
        async with get_session() as session:
            try:
                # delete job seeker from the database
                delete_query = delete(CompanyModel).where(CompanyModel.company_id == company_id)
                deleted_company = await session.execute(delete_query)
                if deleted_company.rowcount == 0:
                    return CompanyResponse(success=False, company=None,
                                           message=f"Account not found.")
                else:
                    delete_query = delete(UserModel).where(UserModel.user_id == company_id)
                    await session.execute(delete_query)

                await session.commit()

                return CompanyResponse(success=True, message="Account deleted successfully")

            except Exception as e:
                # Return an error response with the error message
                return CompanyResponse(success=False, message=str(e))
