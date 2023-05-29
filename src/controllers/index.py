from typing import Optional
import strawberry
from strawberry.fastapi import GraphQLRouter, BaseContext
from src.schemas.user import Query as UserQuery, Mutation as UserMutation
from src.schemas.project import Query as ProjectQuery, Mutation as ProjectMutation
from src.schemas.job_seeker import Query as SeekerQuery, Mutation as SeekerMutation
from src.schemas.company import Query as CompanyQuery, Mutation as CompanyMutation
from src.schemas.skill import Query as SkillQuery
from src.schemas.education import Query as EducationQuery, Mutation as EducationMutation
from functools import cached_property
from strawberry.types import Info as _Info
from strawberry.types.info import RootValueType
from datetime import datetime
from decouple import config
from jwt import decode, InvalidTokenError

JWT_SECRET = config('secret')
JWT_ALGORITHM = config('algorithm')


class SessionExpired(Exception):
    pass


# TODO: CHECK IF TOKEN IS EXPIRED
def is_token_expired(token: str) -> Optional[bool]:
    try:
        payload = decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        exp = payload.get("exp")
        if not exp:
            return None
        now = datetime.utcnow().timestamp()
        return now > exp
    except InvalidTokenError:
        return None


class Context(BaseContext):
    @cached_property
    async def get_current_user(self) -> int:
        if not self.request.headers.get("Authorization", None):
            return None

        try:
            authorization = self.request.headers.get("Authorization", None)
            print("authorization", authorization)
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")

            payload = decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload["user_id"]

            if is_token_expired(token):
                raise SessionExpired("Session has expired")

            return user_id
        except InvalidTokenError:
            raise Exception("Invalid token")


Info = _Info[Context, RootValueType]


async def get_context() -> Context:
    return Context()


# Define the combined schema
@strawberry.type
class Query(UserQuery, ProjectQuery, SeekerQuery, CompanyQuery, SkillQuery, EducationQuery):
    pass


@strawberry.type
class Mutation(UserMutation, ProjectMutation, SeekerMutation, CompanyMutation, EducationMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, context_getter=get_context)
