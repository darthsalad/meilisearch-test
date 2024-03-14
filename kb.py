from dotenv import load_dotenv
import meilisearch
import requests
import json
import os

load_dotenv()

SEARCH_URL = os.environ.get("SEARCH_HTTP_ADDR")
SEARCH_KEY = os.environ.get("SEARCH_MASTER_KEY")

client = meilisearch.Client(
    f"{SEARCH_URL}",
    f"{SEARCH_KEY}",
)

def upload_to_index(index_name, documents):
    try:
        if index_name:
            client.index(index_name).add_documents(documents)
            # print("Documents added successfully.")
        else:
            raise Exception("Index name and file name are required.")
    except Exception as e:
        print(e)
        raise Exception("Failed to upload documents.")


def update_index_settings(index_name):
    """DOCUMENT TEMPLATE EXAMPLE:
    "A movie titled '{{doc.title}}' whose description starts with {{doc.overview|truncatewords: 20}}"
    """
    try:
        url = f'{os.getenv("SEARCH_HTTP_ADDR")}/indexes/{index_name}/settings'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {os.getenv("SEARCH_MASTER_KEY")}'
        }
        data = {
            "embedders": {
                "custom": {
                    "source": "userProvided",
                    "dimensions": 1536
                }
            }
        }

        response = requests.patch(url, headers=headers, data=json.dumps(data))
        print("Settings updated successfully.", response.text)
    except Exception as e:    
        print(e)
        raise Exception("Failed to update settings.")

def delete_all(index_name, email):
    try:
        client.index(index_name).delete_documents(filter=f"email = '{email}'")
        print("Documents deleted successfully.")
    except Exception as e:
        print(e)
        raise Exception("Failed to delete documents.")

def delete_project(index_name, email, project):
    try:
        client.index(index_name).delete_documents(filter=f"email = '{email}' AND project = '{project}'")
        print("Documents deleted successfully.")
    except Exception as e:
        print(e)
        raise Exception("Failed to delete documents.")