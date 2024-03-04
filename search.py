import requests
import json
import os

def upload_to_index(client, index_name, file_name):
    try:
        if index_name:
            with open(file_name, "r") as f:
                data = json.load(f)

            client.index(index_name).add_documents(data)
            print("Documents added successfully.")
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
