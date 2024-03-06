from web import get_google_search_results, navigate_and_extract, similarity_search
from concurrent.futures import ThreadPoolExecutor, as_completed
from selenium.webdriver.firefox.options import Options
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from langchain_openai import AzureOpenAIEmbeddings
from selenium import webdriver
from project_loader import *
import traceback
from kb import *
import requests
import json
import time
import os

DEPLOYMENT_NAME = os.environ.get("DEPLOYMENT_NAME_1")
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT_1")
API_VERSION = os.environ.get("API_VERSION_1")
API_KEY = os.environ.get("API_KEY_1")

DEPLOYMENT_NAME_2 = os.environ.get("DEPLOYMENT_NAME_2")
AZURE_ENDPOINT_2 = os.environ.get("AZURE_ENDPOINT_2")
API_VERSION_2 = os.environ.get("API_VERSION_2")
API_KEY_2 = os.environ.get("API_KEY_2")

embeddings_1 = AzureOpenAIEmbeddings(
    azure_deployment=DEPLOYMENT_NAME,
    openai_api_version=API_VERSION,
    api_key=API_KEY,
    azure_endpoint=AZURE_ENDPOINT,
    dimensions=1536,
    disallowed_special=(),
)

embeddings_2 = AzureOpenAIEmbeddings(
    azure_deployment=DEPLOYMENT_NAME_2,
    openai_api_version=API_VERSION_2,
    api_key=API_KEY_2,
    azure_endpoint=AZURE_ENDPOINT_2,
    dimensions=1536,
    disallowed_special=(),
)

firefox_options = Options()
firefox_options.add_argument("--headless")

drivers = [webdriver.Firefox(options=firefox_options) for _ in range(5)]
for driver in drivers:
    driver.get("about:blank")

app = FastAPI()

origins = ["*"]

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

    try:
        generate_embeddings(
            files, project, email, embeddings_array=[embeddings_1, embeddings_2], index=index
        )
        print(
            f"Time taken to generate and upload embeddings: {time.time() - timer} seconds"
        )

        update_index_settings(index)
        print(f"Time taken to update settings: {time.time() - timer} seconds")

        return {"message": "Content added successfully"}
    except Exception as e:
        print(traceback.format_exc())

        raise HTTPException(status_code=500, detail=str(e))


@app.post("/search", status_code=200)
async def search(request: Request):
    timer = time.time()
    try:
        data = await request.json()

        email = data["email"]
        query = data["query"]
        index = data["index"]
        projects = data["projects"]

        query_embeddings = embeddings_1.embed_query(query)

        hits = []

        with ThreadPoolExecutor() as executor:
            futures = [
                executor.submit(
                    get_search_results, query_embeddings, index, project, email
                )
                for project in projects
            ]

            for future in as_completed(futures):
                hits.extend(future.result())

        print(f"Time taken to search: {time.time() - timer} seconds")

        return {
            "query": query,
            "projects": projects,
            "results": hits,
        }
    except Exception as e:
        print(traceback.format_exc())

        raise HTTPException(status_code=500, detail=str(e))


def get_search_results(vectors, index, project, email):
    try:
        results = []

        request = requests.post(
            f"{SEARCH_URL}/indexes/{index}/search",
            data=json.dumps(
                {
                    "vector": vectors,
                    "filter": [f"project = '{project}'", f"email = '{email}'"],
                    "limit": 5,
                }
            ),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {SEARCH_KEY}",
            },
            verify=False,
        )

        res = request.json()

        for hit in res["hits"]:
            results.append(
                {
                    "id": hit["id"],
                    "file": hit["file_path"],
                    "content": hit["file_content"],
                    "project": hit["project"],
                    "loc": hit["loc"],
                    "score": hit["_semanticScore"] if "_semanticScore" in hit else 0,
                }
            )

        return results
    except Exception as e:
        print(traceback.format_exc())

        raise Exception("Failed to get search results.")


@app.get("/search", status_code=200)
def search_internet(q: str):
    start_time_main = time.time()
    try:
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
    except Exception as e:
        print(e)

        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/delete_kb", status_code=200)
async def delete_kb(request: Request):
    data = await request.json()

    email = data["email"]
    index = data["index"]

    try:
        delete_by_email(index, email)

        return {"message": "Content deleted successfully"}
    except Exception as e:
        print(e)

        raise HTTPException(status_code=500, detail=str(e))
