import strawberry
from strawberry.fastapi import GraphQLRouter
from schemas.user import Query as UserQuery, Mutation as UserMutation
from schemas.project import Query as ProjectQuery, Mutation as ProjectMutation
from schemas.job_seeker import Query as SeekerQuery, Mutation as SeekerMutation
from schemas.company import Query as CompanyQuery, Mutation as CompanyMutation


# Define the combined schema
@strawberry.type
class Query(UserQuery, ProjectQuery, SeekerQuery, CompanyQuery):
    pass


@strawberry.type
class Mutation(UserMutation, ProjectMutation, SeekerMutation, CompanyMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
