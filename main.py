from web import get_google_search_results, navigate_and_extract, similarity_search
from selenium.webdriver.firefox.options import Options
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import AzureOpenAIEmbeddings
from fastapi import FastAPI, Request
from selenium import webdriver
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

API_VERSION = os.environ.get("API_VERSION_1")
API_KEY = os.environ.get("API_KEY_1")
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT_1")

API_KEY_2 = os.environ.get("API_KEY_2")
API_VERSION_2 = os.environ.get("API_VERSION_2")
AZURE_ENDPOINT_2 = os.environ.get("AZURE_ENDPOINT_2")

client = meilisearch.Client(
    f"{SEARCH_URL}", f"{SEARCH_KEY}",
)

embeddings_1 = AzureOpenAIEmbeddings(
    azure_deployment=DEPLOYMENT_NAME,
    openai_api_version=API_VERSION,
    api_key=API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    dimensions=1536,
    disallowed_special=()
)

embeddings_2 = AzureOpenAIEmbeddings(
    azure_deployment=DEPLOYMENT_NAME,
    openai_api_version=API_VERSION_2,
    api_key=API_KEY_2,
    azure_endpoint=AZURE_ENDPOINT_2,
    dimensions=1536,
    disallowed_special=()
)

firefox_options = Options()
firefox_options.add_argument("--headless")

drivers = [webdriver.Firefox(options=firefox_options) for _ in range(5)]
for driver in drivers:
    driver.get("about:blank")

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

    generate_embeddings(files, project, email, embeddings_array=[embeddings_1, embeddings_2])

    print(f"Time taken to generate embeddings: {time.time() - timer} seconds")

    time.sleep(1)

    upload_to_index(client, index, "temp.json")

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

    query_embeddings = embeddings_1.embed_query(query)

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


@app.get("/search")
def search_internet(q: str):
    start_time_main = time.time()
    res = get_google_search_results(q)
    
    google_results_time = str(time.time() - start_time_main)
    print(f"Google results time: {google_results_time}")

    with ThreadPoolExecutor(max_workers=5) as executor:
        # Start a future for each of the first 5 search results
        futures = [
            executor.submit(
                navigate_and_extract,
                drivers[i],
                res["organic_search_results"][i]["link"],
            )
            for i in range(5)
        ]

        # Wait for all futures to complete and collect the results
        contents = [future.result() for future in futures]

    generate_embedding_time = str(time.time() - start_time_main)
    print(f"Generate embedding time: {generate_embedding_time}")

    top_3 = similarity_search(q, contents)
    # Print total time and quit all the drivers
    complete_end_time = str(time.time() - start_time_main)
    print(f"Complete end time: {complete_end_time}")

    return {
        "top_3": top_3,
        "links": [res["organic_search_results"][i]["link"] for i in range(3)],
    }
