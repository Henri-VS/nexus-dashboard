# Nexus — Deployment Guide
# For: Henri-VS (Willem)

---

## Before you start — what you need

- Docker Desktop installed and running on your machine
- A terminal (PowerShell on Windows, Terminal on Mac/Linux)
- Git installed

---

## Part 1 — Setting up GitHub (one time)

### Step 1: Create the GitHub repository

1. Go to **https://github.com/new**
2. Fill in:
   - **Repository name**: `nexus-dashboard`
   - **Visibility**: Public
   - **DO NOT** tick "Add a README file" — you already have one
3. Click **Create repository**

Your repo URL will be: `https://github.com/Henri-VS/nexus-dashboard`

---

### Step 2: Push your code to GitHub

Open a terminal in your `_Dashboard` folder and run these commands one by one:

```bash
git init
git add .
git commit -m "initial: nexus dashboard"
git branch -M main
git remote add origin https://github.com/Henri-VS/nexus-dashboard.git
git push -u origin main
```

When it asks for a username/password, use your GitHub username (`Henri-VS`) and a **Personal Access Token** (not your GitHub password). To create a token:
1. Go to https://github.com/settings/tokens
2. Click **Generate new token (classic)**
3. Tick `repo` scope
4. Copy the token — use it as your password in the terminal

---

## Part 2 — Setting up Docker Hub (one time)

### Step 3: Create a Docker Hub account

1. Go to **https://hub.docker.com**
2. Sign up with username **HenriVS** (all lowercase in image names)
3. Verify your email

---

### Step 4: Create two Docker Hub repositories

You need one repo for the frontend and one for the backend.

1. Go to https://hub.docker.com/repository/create
2. **First repo:**
   - Repository name: `nexus-frontend`
   - Visibility: **Public**
   - Click **Create**
3. **Second repo** (repeat):
   - Repository name: `nexus-backend`
   - Visibility: **Public**
   - Click **Create**

Your image names will be:
- `henriVS/nexus-frontend:latest`
- `henriVS/nexus-backend:latest`

---

### Step 5: Log in to Docker Hub from your terminal

```bash
docker login
```

Enter your Docker Hub username (`HenriVS`) and password when prompted.

---

## Part 3 — Building and pushing Docker images

### Step 6: Build the images

From your `_Dashboard` folder:

```bash
docker compose build
```

This builds both frontend and backend and tags them as `henriVS/nexus-frontend:latest` and `henriVS/nexus-backend:latest`. Takes 3–5 minutes the first time.

---

### Step 7: Push images to Docker Hub

```bash
docker push henriVS/nexus-frontend:latest
docker push henriVS/nexus-backend:latest
```

You can verify they uploaded at:
- https://hub.docker.com/r/henriVS/nexus-frontend
- https://hub.docker.com/r/henriVS/nexus-backend

---

## Part 4 — Every time you make changes

After editing code and wanting to publish the update:

```bash
# 1. Build the updated images
docker compose build

# 2. Push to Docker Hub
docker push henriVS/nexus-frontend:latest
docker push henriVS/nexus-backend:latest

# 3. Commit and push code to GitHub
git add .
git commit -m "describe what you changed"
git push
```

Users get the update by running `docker compose -f docker-compose-hub.yml pull && ./start.sh`.

---

## Part 5 — Running it yourself

### On your own machine (local dev)

```bash
cp backend/.env.example .env
# Edit .env — set NEXUS_SECRET_KEY
./start.sh        # Linux/Mac
.\start.ps1       # Windows PowerShell
```

The start script auto-detects your local IP and opens the dashboard at `http://YOUR_IP:3000`.

---

## Summary — your image and repo locations

| Thing | URL |
|-------|-----|
| GitHub repo | https://github.com/Henri-VS/nexus-dashboard |
| Frontend image | https://hub.docker.com/r/henriVS/nexus-frontend |
| Backend image | https://hub.docker.com/r/henriVS/nexus-backend |
| Raw compose file | https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/docker-compose-hub.yml |
| Raw env example | https://raw.githubusercontent.com/Henri-VS/nexus-dashboard/main/backend/.env.example |
