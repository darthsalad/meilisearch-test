from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_openai import AzureOpenAIEmbeddings
from dotenv import load_dotenv
from openai import AzureOpenAI
from typing import List
from uuid import uuid4
import json
import time
import os

load_dotenv()

API_KEY_1 = os.environ.get("API_KEY_1")
API_VERSION_1 = os.environ.get("API_VERSION_1")
AZURE_ENDPOINT_1 = os.environ.get("AZURE_ENDPOINT_1")

model = AzureOpenAI(
    api_key=API_KEY_1,
    api_version=API_VERSION_1,
    azure_endpoint=AZURE_ENDPOINT_1,
)

i = 0


def generate_embedding_for_file(file, project, email, embeddings: AzureOpenAIEmbeddings):
    global i
    i += 1
    print(f"{i}  ::  ", file["name"])
    time.sleep(5)
    
    try:
        new_id = uuid4()
        content_embedding = embeddings.embed_query(f"{file['name']}\n\n{file['content']}")

        new_dict = {
            "id": str(new_id),
            "file_path": file["name"],
            "file_content": file["content"],
            "dependency": file["dependency"],
            "loc": file["loc"],
            # "keywords": generate_keywords(file["content"]),
            "_vectors": {"custom": content_embedding},
            "project": project,
            "email": email,
        }

        return new_dict
    except Exception as e:
        print(str(e))
        raise Exception("Failed to generate embeddings.")

def generate_embeddings(files, project, email, embeddings_array: List[AzureOpenAIEmbeddings]):
    global i
    
    chunk_array = []

    try:
        with ThreadPoolExecutor(max_workers=30) as executor:
            futures = [executor.submit(generate_embedding_for_file, file, project, email, embeddings_array[index % 2]) for index, file in enumerate(files)]

            for futures in as_completed(futures):
                chunk_array.append(futures.result())

        with open("temp.json", "w") as outfile:
            json.dump(chunk_array, outfile)
        
        i = 0
    except Exception as e:
        print(str(e))
        raise Exception("Failed to generate embeddings.")


# def generate_keywords(content):
#     model_call = model.chat.completions.create(
#         model="gpt-35-turbo-16k",
#         stream=False,
#         temperature=0,
#         messages=[
#             {
#                 "role": "system",
#                 "content": "Your task is to generate comma separated keywords/tags for the given code",
#             },
#             {"role": "user", "content": content},
#         ],
#     )

#     return model_call.choices[0].message.content


#     # initial_keywords = model_call.choices[0].message.content

#     # additional_call = model.chat.completions.create(
#     #     model="gpt-35-turbo-16k",
#     #     stream=False,
#     #     temperature=0,
#     #     messages=[
#     #         {
#     #             "role": "system",
#     #             "content": "Run keyword expansion on the below provided keywords and return them as comma separated. NOTHING ELSE SHALL BE RETURNED.",
#     #         },
#     #         {"role": "user", "content": initial_keywords},
#     #     ],
#     # )
#     # return additional_call.choices[0].message.content
