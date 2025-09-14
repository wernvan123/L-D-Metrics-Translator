import requests
import json

url = "http://localhost:5000/api/analyze-event"
headers = {
    'Content-Type': 'application/json'
}
data = {
    "event_description": "Team struggled with project deadline due to communication issues"
}

try:
    print("Sending request to:", url)
    print("Headers:", headers)
    print("Data:", data)
    
    response = requests.post(url, headers=headers, json=data)
    
    print("\nResponse Status Code:", response.status_code)
    print("Response Headers:", response.headers)
    print("Response Content:", response.text)
    
    try:
        print("\nResponse JSON:", response.json())
    except json.JSONDecodeError:
        print("\nResponse is not valid JSON")
        
except Exception as e:
    print("\nError:", str(e))
