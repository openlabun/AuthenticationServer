Authentication server


Build with:

docker build --tag authi .   
docker run -d -it -p 8000:8000 authi

From Docker Hub:
docker run -d -it -p 8000:8000 augustosalazar/authi:2   
   
@baseUrl = http://127.0.0.1:8000
@contentType = application/json


GET {{baseUrl}}/users/ HTTP/1.1

### ----------------- ###

POST {{baseUrl}}/register/ HTTP/1.1
Content-Type: {{contentType}}

{
    "username": "pepe22",
    "first_name": "pepon",
    "last_name": "pentoski",
    "password": "1234"
}

### ----------------- ###

POST {{baseUrl}}/login/ HTTP/1.1
Content-Type: {{contentType}}

{
    "username": "pepe22",
    "password": "1234"
}

### ----------------- ###

GET {{baseUrl}}/me/ HTTP/1.1
Content-Type: {{contentType}}
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqdWFuOTk5IiwiZXhwIjoxNjgzOTk5NjExfQ.Z1jgEvksFd7ZGB4uUxQzdIxRDGfmNf9jFPfeM-TBub0

### ----------------- ###

POST {{baseUrl}}/refresh/ HTTP/1.1
Content-Type: {{contentType}}

{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqdWFuOTk5IiwiZXhwIjoxNjg0MDM4NDYwfQ.GiEn9Gc4kL3_KkRAbwfIn2tpqn0dDNGGjRu3iGj3VU0"
}

### ----------------- ###

GET {{baseUrl}}/users/ HTTP/1.1

Next steps:

1.	Service mode: the idea is to provide authentication services to multiple applications, each with its own contract, to achieve this, we need:
a.	An endpoint that receives a request to create a new contract and gives back a key, this key should be unique and serves to identify the contract    
b.	The key should be used in any subsequential request    
c.	Each contract will be allowed up to 100 users.   
3.	Persistence   
a.	Use a database to store keys and user information for every contract    
b.	Create an admin page to be able to delete contracts   


Author: Shaddia Andrea Acuña Lara
