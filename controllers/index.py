import strawberry
from strawberry.fastapi import GraphQLRouter
from schemas.user import Query as UserQuery, Mutation as UserMutation
from schemas.project import Query as ProjectQuery, Mutation as ProjectMutation


# Define the combined schema
@strawberry.type
class Query(UserQuery, ProjectQuery):
    pass


@strawberry.type
class Mutation(UserMutation, ProjectMutation):
    pass


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema)
