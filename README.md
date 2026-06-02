# Dataflow

Instant data profiling — drop a CSV/Excel/JSON, get schema, types, nulls, and sample rows.

## Structure
```
dataflow/
  backend/   FastAPI — POST /api/upload
  frontend/  React + Vite
```

## Local dev

**Backend**
```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload
```

**Frontend**
```bash
cd frontend
npm install
npm run dev
```
