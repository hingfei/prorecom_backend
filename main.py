from fastapi import FastAPI
from controllers.index import graphql_app
app = FastAPI()

app.include_router(graphql_app, prefix="/graphql")
# app.add_websocket_route("/graphql", graphql_app)
