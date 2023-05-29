from fastapi import FastAPI
from src.controllers.index import graphql_app
from src.recommendations.recommendation_engine import cluster_projects
from src.settings import init, load_fasttext_model
import asyncio

app = FastAPI()

app.include_router(graphql_app, prefix="/graphql")


async def startup():
    # Load the pre-trained FastText model
    init()
    load_fasttext_model()
    await cluster_projects()
    print('finished cluster')


@app.on_event("startup")
async def app_startup():
    asyncio.create_task(startup())