from dotenv import load_dotenv
import traceback
import requests
import json
import os

load_dotenv()

SERVER_URL=os.environ.get("SERVER_URL")

def check_user_project(email, projects, product):
    try:
        url = f"{SERVER_URL}/setpinecone"
        headers = {"Content-Type": "application/json"}

        response = requests.post(url, headers=headers, data=json.dumps(
            {
                "email": email, 
                "projects": projects, 
                "product": product
            }
        ))

        return response.status_code
    except Exception as e:
        print(traceback.format_exc())
        raise Exception("Failed to check user.", str(e))
