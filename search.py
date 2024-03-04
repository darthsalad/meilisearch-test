import requests
import json
import os

def upload_to_index(client, index_name, file_name):
    if index_name and file_name:
        with open(file_name, "r", encoding="utf-8") as f:
            data = json.load(f)
        client.index(index_name).add_documents(data)
        return {
            "response": "success",
            "message": "index created successfully."
        }
    else:
        raise Exception("Index name and file name are required.")


def update_index_settings(index_name):
    """DOCUMENT TEMPLATE EXAMPLE:
    "A movie titled '{{doc.title}}' whose description starts with {{doc.overview|truncatewords: 20}}"
    """
    
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
    if response.status_code == 200:
        print("Settings updated successfully.")
    else:
        print("Failed to update settings. Status code:", response.status_code)
        print(response.text)
        raise Exception("Failed to update settings.")


# def task_update():
#     url = f"{os.getenv('SEARCH_HTTP_ADDR')}/tasks"
#     headers = {
#         "Content-Type": "application/json",
#         "Authorization": f"Bearer {os.getenv('SEARCH_MASTER_KEY')}"
#     }

#     response = requests.get(url, headers=headers)
#     return response.text


# def vector_search(index, query):
#     url = f'{os.getenv("SEARCH_HTTP_ADDR")}/indexes/{index}/search'
#     headers = {'content-type': 'application/json', "authorization": f'Bearer {os.getenv("SEARCH_MASTER_KEY")}'}
#     data = {
#         "q": query,
#         "hybrid": {
#             "semanticRatio": 0.9,
#             "embedder": "default"
#         }
#     }

#     response = requests.post(url, headers=headers, json=data)
#     if response.status_code == 200:
#         return response.json()
#     else:
#         return False


# def delete_index(client, index_name):
#     if index_name:
#         client.index(index_name).delete()
#         return True
#     return False
