# ShipFast Product Catalogue API

FastAPI · PostgreSQL · Docker · AWS ECS Fargate

## Project Structure

```
shipfast-api/
├── app/
│   ├── main.py          # App entry-point, lifespan, /health
│   ├── database.py      # SQLAlchemy engine + session
│   ├── models.py        # ORM models
│   ├── schemas.py       # Pydantic request/response schemas
│   └── routers/
│       └── products.py  # GET /products, POST /products, etc.
├── tests/
│   └── test_api.py      # Pytest suite (SQLite in-memory)
├── Dockerfile           # Multi-stage build (< 200 MB)
├── docker-compose.yml   # Local dev (app + Postgres)
├── requirements.txt
└── .env.example
```

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | /products | List all products (paginated) |
| GET | /products/{id} | Get a single product |
| POST | /products | Create a product |
| PUT | /products/{id} | Update a product |
| DELETE | /products/{id} | Delete a product |
| GET | /health | ECS / ALB health check |

## Local Development

```bash
# 1. Start Postgres + API
docker-compose up --build

# 2. Open interactive docs
open http://localhost:8000/docs
```

## Run Tests

```bash
pip install -r requirements.txt pytest httpx
pytest -v
```

## Secrets Manager (Production)

Set `DB_SECRET_NAME` to your AWS secret name.  
The secret must be a JSON object:

```json
{
  "host":     "your-rds-endpoint",
  "port":     5432,
  "dbname":   "catalogue",
  "username": "shipfast",
  "password": "supersecret"
}
```

The app fetches credentials at startup — **no passwords in env vars or images**.