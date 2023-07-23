from typing import Optional
import strawberry
from strawberry.fastapi import GraphQLRouter, BaseContext
from src.schemas.user import Query as UserQuery, Mutation as UserMutation
from src.schemas.project import Query as ProjectQuery, Mutation as ProjectMutation
from src.schemas.job_seeker import Query as SeekerQuery, Mutation as SeekerMutation
from src.schemas.company import Query as CompanyQuery, Mutation as CompanyMutation
from src.schemas.skill import Query as SkillQuery
from src.schemas.education import Query as EducationQuery, Mutation as EducationMutation
from src.schemas.application import Query as ApplicationQuery, Mutation as ApplicationMutation
from src.schemas.notfication import Query as NotificationQuery, Mutation as NotificationMutation
from functools import cached_property
from strawberry.types import Info as _Info
from strawberry.types.info import RootValueType
from datetime import datetime
from decouple import config
from jwt import decode, InvalidTokenError, ExpiredSignatureError

# JWT_SECRET and JWT_ALGORITHM are read from environment variables
JWT_SECRET = config('secret')
JWT_ALGORITHM = config('algorithm')


# Custom Exception to handle session expiration
class SessionExpired(Exception):
    pass


# Function to check if a JWT token is expired
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


# Custom context class that extends BaseContext
class Context(BaseContext):
    @cached_property
    async def get_current_user(self) -> int:
        # Check if the Authorization header exists in the request
        if not self.request.headers.get("Authorization", None):
            return None

        try:
            # Extract the token from the Authorization header
            authorization = self.request.headers.get("Authorization", None)
            print("authorization", authorization)
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")

            # Decode the token to get the user_id
            payload = decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload["user_id"]

            # Check if the token has expired
            if "exp" in payload and payload["exp"] < datetime.utcnow().timestamp():
                raise Exception("Session has expired")

            return user_id
        except (InvalidTokenError, ExpiredSignatureError):
            if InvalidTokenError:
                raise Exception("Invalid token")
            elif ExpiredSignatureError:
                raise Exception("Session has expired")


# Type alias for Info
Info = _Info[Context, RootValueType]


# Function to get the context, used as a context_getter for GraphQLRouter
async def get_context() -> Context:
    return Context()


# Define the combined schema
@strawberry.type
class Query(UserQuery, ProjectQuery, SeekerQuery, CompanyQuery, SkillQuery, EducationQuery, ApplicationQuery,
            NotificationQuery):
    pass


@strawberry.type
class Mutation(UserMutation, ProjectMutation, SeekerMutation, CompanyMutation, EducationMutation, ApplicationMutation,
               NotificationMutation):
    pass


# Create the Strawberry schema with combined query and mutation
schema = strawberry.Schema(query=Query, mutation=Mutation)
# Create the GraphQL app using the schema and context_getter
graphql_app = GraphQLRouter(schema, context_getter=get_context)
