from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
from openai import AzureOpenAI
from uuid import uuid4
import json
import os

load_dotenv()

API_VERSION = os.environ.get("API_VERSION")
API_KEY = os.environ.get("API_KEY")
AZURE_ENDPOINT = os.environ.get("AZURE_ENDPOINT")

model = AzureOpenAI(
    api_key=API_KEY,
    api_version=API_VERSION,
    azure_endpoint=AZURE_ENDPOINT,
)

i = 0

# def generate_keywords_for_file(file, project, email):
#     global i
#     i += 1

#     new_id = uuid4()

#     new_dict = {
#         "id": str(new_id),
#         "file_path": file["name"],
#         "file_content": file["content"],
#         "dependency": file["dependency"],
#         "loc": file["loc"],
#         # "keywords": generate_keywords(file["content"]),
#         "project": project,
#         "email": email,
#     }

#     print(f"{i}  ::  ", file["name"])
#     return new_dict


# def generate_file_dicts(files, project, email):
#     timer = time.time()
#     chunk_array = []

#     with ThreadPoolExecutor(max_workers=40) as executor:
#         futures = [executor.submit(generate_keywords_for_file, file, project, email) for file in files]

#         for futures in as_completed(futures):
#             chunk_array.append(futures.result())

#     with open("temp.json", "w", encoding="utf-8") as outfile:
#         json.dump(chunk_array, outfile)

#     print("Time taken to generate dicts:", time.time() - timer)


def generate_embedding_for_file(file, project, email, embeddings: AzureOpenAIEmbeddings):
    global i
    i += 1
    print(f"{i}  ::  ", file["name"])
    
    new_id = uuid4()
    content_embedding = embeddings.embed_query(f"{file['name']}\n\n{file['content']}")

    new_dict = {
        "id": str(new_id),
        "file_path": file["name"],
        "file_content": file["content"],
        "dependency": file["dependency"],
        "loc": file["loc"],
        "keywords": generate_keywords(file["content"]),
        "_vectors": {"custom": content_embedding},
        "project": project,
        "email": email,
    }

    return new_dict


def generate_embeddings(files, project, email, embeddings: AzureOpenAIEmbeddings):
    chunk_array = []

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = [executor.submit(generate_embedding_for_file, file, project, email, embeddings) for file in files]

        for futures in as_completed(futures):
            chunk_array.append(futures.result())

    with open("temp.json", "w", encoding="utf-8") as outfile:
        json.dump(chunk_array, outfile)


def generate_keywords(content):
    model_call = model.chat.completions.create(
        model="gpt-35-turbo-16k",
        stream=False,
        temperature=0,
        messages=[
            {
                "role": "system",
                "content": "Your task is to generate comma separated keywords/tags for the given code",
            },
            {"role": "user", "content": content},
        ],
    )

    return model_call.choices[0].message.content


    # initial_keywords = model_call.choices[0].message.content

    # additional_call = model.chat.completions.create(
    #     model="gpt-35-turbo-16k",
    #     stream=False,
    #     temperature=0,
    #     messages=[
    #         {
    #             "role": "system",
    #             "content": "Run keyword expansion on the below provided keywords and return them as comma separated. NOTHING ELSE SHALL BE RETURNED.",
    #         },
    #         {"role": "user", "content": initial_keywords},
    #     ],
    # )
    # return additional_call.choices[0].message.content
