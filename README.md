# NL2SQL with Gemini 2.5 Pro

Convert natural language queries to SQL using Google's Gemini 2.5 Pro and execute them against PostgreSQL.

## Quick Start

1. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Start server**
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Test API**
   - Server: http://localhost:8000
   - Docs: http://localhost:8000/docs
   - Health: http://localhost:8000/health

## API Usage

**POST /query** - Generate SQL and execute
```json
{
  "schema_text": "Table: users\n- id (integer, primary key)\n- name (varchar)",
  "query": "Show all users"
}
```

**POST /generate-sql** - Generate SQL only (no execution)

## Configuration

Edit `backend/config.env`:
- `DATABASE_URL` - Your PostgreSQL connection string
- `GEMINI_API_KEY` - Your Google Gemini API key

## Features

- ✅ Gemini 2.5 Pro integration
- ✅ Safe SQL execution (SELECT only)
- ✅ User-provided schema support
- ✅ JSON API responses
- ✅ Real-time error handling
