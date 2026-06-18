#!/bin/bash

echo "1. Attempting login with valid credentials..."
# SHA256 of 'admin123'
PASSWORD_HASH="8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918"

curl -s -X POST http://127.0.0.1:8000/api/v1/auth/login -H "Content-Type: application/x-www-form-urlencoded" -d "username=admin&password=$PASSWORD_HASH" > /tmp/login_resp.json

cat /tmp/login_resp.json

# Simple parsing since we don't have jq guaranteed
TOKEN=$(grep -o '"access_token":"[^"]*"' /tmp/login_resp.json | cut -d'"' -f4)

echo -e "\n\n2. Attempting to access protected route WITH token..."
curl -s -w "\nHTTP_CODE:%{http_code}" -X GET http://127.0.0.1:8000/api/v1/tasks/ -H "Authorization: Bearer $TOKEN"

echo -e "\n\n3. Attempting to access protected route WITHOUT token..."
curl -s -w "\nHTTP_CODE:%{http_code}" -X GET http://127.0.0.1:8000/api/v1/tasks/
