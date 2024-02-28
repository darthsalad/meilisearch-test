from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import AzureOpenAIEmbeddings
from fastapi import FastAPI, Request
from dotenv import load_dotenv
from project_loader import *
from search import *
import meilisearch
import requests
import json
import time
import os

load_dotenv()

SEARCH_URL = os.environ.get("SEARCH_HTTP_ADDR")
SEARCH_KEY = os.environ.get("SEARCH_MASTER_KEY")
DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME")
API_VERSION = os.environ.get("API_VERSION")
API_KEY = os.environ.get("API_KEY")
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")

client = meilisearch.Client(
    f"{SEARCH_URL}", f"{SEARCH_KEY}",
)

embeddings = AzureOpenAIEmbeddings(
    azure_deployment=DEPLOYMENT_NAME,
    openai_api_version=API_VERSION,
    api_key=API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    dimensions=1536,
    disallowed_special=()
)

app = FastAPI()

origins = [ "*" ] 

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],  
)

@app.get("/ping")
def ping():
    return "Pong"

@app.post("/add_kb")
async def add_kb(request: Request):
    data = await request.json()

    email = data["email"]
    files = data["files"]
    project = data["project"]
    index = data["index"]

    timer = time.time()

    generate_embeddings(files, project, email, embeddings)

    print(f"Time taken to generate embeddings: {time.time() - timer} seconds")

    time.sleep(1)

    upload_to_index(index, "temp.json")

    print(f"Time taken to add documents: {time.time() - timer} seconds")

    update_index_settings(index)
    
    print(f"Time taken to update settings: {time.time() - timer} seconds")

    return {
        "message": "Content added successfully"
    }

@app.post("/search")
async def search(request: Request):
    timer = time.time()
    data = await request.json()

    query = data["query"]
    project = data["project"]
    index = data["index"]

    query_embeddings = embeddings.embed_query(query)

    request = requests.post(
        f"{SEARCH_URL}/indexes/{index}/search",
        data=json.dumps({
            "vector": query_embeddings, 
            "filter": [
                f"project = {project}"
            ],
            "limit": 5,
        }),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {SEARCH_KEY}",
        },
        verify=False
    )

    result = request.json()

    hits = []

    for hit in result["hits"]:
        hits.append(
            {
                "id": hit["id"],
                "file_path": hit["file_path"],
                "score": hit["_semanticScore"] if "_semanticScore" in hit else 0,
            }
        )

    print("Time taken:", time.time() - timer)

    return {
        "query": query,
        "project": project,
        "results": hits,
    }
