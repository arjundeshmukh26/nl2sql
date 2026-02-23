# 🤖 Autonomous Agentic AI Framework for Business Intelligence

> Transform abstract natural language questions into multi-step, self-directed business investigations.

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2-61DAFB.svg)](https://reactjs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://www.postgresql.org/)
[![License](https://img.shields.io/badge/License-Academic-yellow.svg)]()

---

## 🌟 What Is This?

An **autonomous business intelligence platform** that goes far beyond simple NL2SQL.

Ask a vague, strategic, high-level question like:

> "Tell me what trends you see in the South region and how we can improve performance."

The system will:

- 🔍 Explore your database schema automatically  
- 🧠 Decide what sub-questions to investigate  
- 📊 Run multi-step analysis using 22 specialized tools  
- 🚨 Detect anomalies and unusual patterns  
- 📈 Generate interactive visualizations  
- 💡 Provide strategic, actionable recommendations  

All without manual prompting, copying schema, or iterative back-and-forth.

---

## 🧠 The Core Idea: Agentic Business Intelligence

Most AI tools — including ChatGPT — are **reactive**:

You ask → They answer.

But real business analysis is not reactive.

It is:

- Iterative  
- Exploratory  
- Decision-based  
- Context-aware  

Inspired by autonomous code agents like Cursor and Windsurf,  
this system brings **agentic behavior** to structured business data.

---

## 🚀 What Makes This Different?

| Capability | Traditional BI Tools | ChatGPT | **This System** |
|------------|---------------------|----------|----------------|
| Natural Language Input | ❌ | ✅ | ✅ |
| Direct Database Access | ✅ | ❌ | ✅ |
| Multi-Step Autonomous Investigation | ❌ | ❌ | ✅ |
| Statistical Analysis | ⚠️ Limited | ❌ | ✅ |
| Anomaly Detection | ⚠️ Limited | ❌ | ✅ |
| Automatic Visualization | ❌ | ❌ | ✅ |
| Self-Directed Exploration | ❌ | ❌ | ✅ |

---

> **The system autonomously decides what to analyze next based on intermediate results — without the user micromanaging each step.**

That's the fundamental breakthrough.

---

## 🔄 How the Agent Thinks

When given an abstract query:

> "Why is revenue declining in Region A?"

The system:

1. Understands intent (metrics, time, filters)
2. Explores schema automatically
3. Generates multiple investigative SQL queries
4. Applies statistical validation (Z-score, IQR)
5. Performs anomaly detection
6. Decides whether deeper analysis is required
7. Synthesizes findings into business recommendations

This is not a single SQL execution.

It is a reasoning pipeline.

---

## 🏗️ System Architecture
```
┌──────────────────────────────────────────────────────┐
│  Frontend (React + Chart.js + Tailwind)             │
│  Natural Language UI | Charts | Progress Tracker    │
└───────────────────────┬──────────────────────────────┘
                        │ REST API
┌───────────────────────▼──────────────────────────────┐
│  API Gateway (FastAPI)                               │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│  Agentic Investigation Engine                        │
│  Orchestrator | Context Manager | Decision Logic    │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│  Dynamic Tool Registry (22 Specialized Tools)       │
└───────────────────────┬──────────────────────────────┘
                        │
┌───────────────────────▼──────────────────────────────┐
│  External Services                                   │
│  Gemini LLM | PostgreSQL | Cache | Security         │
└──────────────────────────────────────────────────────┘
```

---

## 🧰 22 Specialized Tools (6 Categories)

### 1️⃣ Database Discovery
- Schema exploration  
- Table inspection  
- Relationship analysis  

### 2️⃣ SQL Execution
- Query generation  
- Query validation  
- Optimization  
- Safe execution  

### 3️⃣ Statistical Analysis
- Descriptive statistics  
- Correlation analysis  
- Distribution analysis  
- Data quality scoring  

### 4️⃣ Investigation Tools
- Drill-down analysis  
- Time comparison  
- Segmentation  

### 5️⃣ Visualization Tools
- Bar charts  
- Line charts  
- Pie charts  
- Scatter plots  
- Smart chart selection  

### 6️⃣ Business Metrics
- KPI evaluation  
- Growth analysis  
- Revenue diagnostics  
- Anomaly detection  
- Executive summary generation  

---

## ⚡ Why Not Just Use a Chatbot?

Using a general AI tool:

1. Copy schema
2. Ask for SQL
3. Run query
4. Paste results
5. Ask follow-up
6. Repeat many times

⏳ Slow.  
⚠️ Manual.  
❌ No guarantee of completeness.

Using this system:

1. Ask once  
2. Get full structured investigation  

---

## 🛠️ Technology Stack

### Backend
- FastAPI  
- AsyncPG  
- Google Gemini 2.5 Flash  
- Pydantic  

### Frontend
- React 18  
- Vite  
- Tailwind CSS  
- Chart.js  
- Axios  

### Database
- PostgreSQL  
- Neon Database  

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL
- Gemini API Key

---

### Installation
```bash
# Clone repository
git clone <repo-url>
cd nl2sql

# Backend setup
cd backend
pip install -r requirements.txt
cp env.example config.env
# Add DATABASE_URL and GEMINI_API_KEY

uvicorn app.main:app --reload

# Frontend setup
cd ../frontend
npm install
npm run dev
```

Open:

* Backend: [http://localhost:8000](http://localhost:8000)
* API Docs: [http://localhost:8000/docs](http://localhost:8000/docs)
* Frontend: [http://localhost:5173](http://localhost:5173)

---

## 🔌 API Endpoints

### `POST /investigate`

Autonomous multi-step investigation pipeline.

### `POST /query`

Basic NL2SQL execution.

### `GET /tools`

List available tools.

### `GET /health`

System health check.

---

## 🎯 Example Use Cases

### Revenue Diagnostics

"Why did revenue drop this quarter?"

→ Trend analysis  
→ Product breakdown  
→ Anomaly detection  
→ Strategic recommendations  

---

### Customer Insights

"Find unusual customer behavior in North region."

→ Segmentation  
→ Outlier detection  
→ Visualizations  
→ Actionable insights  

---

### Data Quality Analysis

"Evaluate customer data quality."

→ Missing value detection  
→ Duplicate identification  
→ Quality scorecard  

---

## 📁 Project Structure
```
nl2sql/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── agentic_client.py
│   │   ├── database.py
│   │   └── tools/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   ├── components/
│   │   └── services/
│   └── package.json
```

---

## 🔮 Future Roadmap

* Multi-database support (MySQL, MongoDB)
* Predictive analytics integration
* Vector memory for conversational continuity
* Enterprise multi-tenant architecture
* Authentication & RBAC
* Dashboard builder mode

---

## 👥 Team

B.Tech Computer Science and Engineering  
Indian Institute of Information Technology Kottayam

* Arjun Deshmukh

---

## 📊 Project Stats

* 8,000+ lines of code
* 22 specialized tools
* 6 tool categories
* 10+ API endpoints
* 2–5 second average investigation time

---

## 🏁 Final Positioning

This is not:

* A chatbot
* A simple SQL generator
* A static dashboard

This is:

> **An Autonomous Agentic System for Structured Business Intelligence**

It investigates.  
It reasons.  
It decides.  
It synthesizes.  
All automatically.
