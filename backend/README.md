## Log:
`docker logs -f fastapi`
 

Install Docker Compose V2

## Step 1 — Add Docker official repository

```bash
sudo apt-get update
sudo apt-get install ca-certificates curl gnupg -y

sudo install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

sudo chmod a+r /etc/apt/keyrings/docker.gpg
```

---

## Step 2 — Add Docker repo

```bash
echo \
  "deb [arch=$(dpkg --print-architecture) \
  signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```

---

## Step 3 — Install Compose plugin

```bash
sudo apt-get update
sudo apt-get install docker-compose-plugin -y
```

---

## 🔍 Step 4 — Verify

```bash
docker compose version
```
 
---

#  Run your stack

```bash
docker compose up -d --build
```


## How to test the containers talk to each other

```bash

docker exec -it fastapi sh

curl http://qdrant:6333
curl http://ollama:11434

```


