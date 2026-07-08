# Running the Travel Agent

## Prerequisites

- `.env` file configured (copy from `env_template` and fill in keys)
- `cert.pem` at the repo root
- Python virtualenv activated

## 1. Set environment

```bash
export $(grep -v '^#' .env | xargs)
export PYTHONPATH=$PYTHONPATH:.
```

## 2. Start the backend API

```bash
uvicorn api:app --reload --port 8001
```

## 3. Start the frontend

```bash
cd frontend
npm run dev
```

Open [http://localhost:3001](http://localhost:3001) in your browser.

## Docker Compose (alternative)

```bash
docker compose up --build
```

Open [http://localhost:3001](http://localhost:3001) in your browser.

## CLI mode (no frontend)

```bash
python travel_agent.py
```
