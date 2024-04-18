import requests
import json

BASE_URL = "https://api.autogenerate.ai"

# generateVideo 
data = {
    "mergeTagData": {
        "{{name}}": "Bob",
        "{{textName}}": "Bob"
    }
}

headers = {
    'Authorization': 'Token 37084a6b5336ad7235fb9fcbe40066acc8f96325',
    'Content-Type': 'application/json'
}

r = requests.post(f"{BASE_URL}/api/newvideo/video/generate/download/1906/",headers=headers,data=json.dumps(data))
print(r.status_code,r.json())