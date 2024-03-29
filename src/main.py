from fastapi import FastAPI
from src.controllers.index import graphql_app
from src.recommendations.project_recom_engine import cluster_projects
from src.recommendations.candidates_recom_engine import cluster_candidates
from src.settings import init, load_fasttext_model
import asyncio

app = FastAPI()

# Include the GraphQL router
app.include_router(graphql_app, prefix="/graphql")


# Function to be executed on startup to load models and cluster data
async def startup():
    # Load the pre-trained FastText model
    init()
    load_fasttext_model()

    # Cluster projects and candidates asynchronously
    await cluster_projects()
    await cluster_candidates()
    print('finished cluster')


# Event handler for application startup
@app.on_event("startup")
async def app_startup():
    # Create a task to execute the startup function asynchronously
    asyncio.create_task(startup())
