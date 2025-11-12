# 🤖 Natural Language Driven Agentic AI Framework for Business Intelligence

> Transform natural language questions into comprehensive business insights through autonomous AI agents

[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-Latest-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2-61DAFB.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-Academic-yellow.svg)]()

---

## 🌟 What is This?

An **autonomous business intelligence platform** that goes beyond simple NL2SQL. Ask a question in plain English, and our AI agents will:

- 🔍 **Investigate** your database autonomously
- 📊 **Analyze** data with 22 specialized tools
- 🎨 **Visualize** findings with interactive charts
- 🚨 **Detect** anomalies and unusual patterns
- 💡 **Provide** actionable business insights

**Example**: Ask "What's wrong with our sales?" → Get complete multi-step analysis, charts, anomaly detection, and recommendations in seconds.

---

## 🎯 Key Features

### ✨ What Makes Us Different

| Feature | Traditional Tools | ChatGPT/Claude | **Our System** |
|---------|------------------|----------------|----------------|
| Natural Language | ❌ | ✅ | ✅ |
| Multi-Step Analysis | ❌ | ❌ | ✅ |
| Auto Visualization | ❌ | ❌ | ✅ |
| Anomaly Detection | ⚠️ Limited | ❌ | ✅ |
| Direct DB Access | ✅ | ❌ | ✅ |
| Zero Manual Steps | ❌ | ❌ | ✅ |

### 🔧 22 Specialized Tools in 6 Categories

1. **Database Discovery** (4 tools): Schema exploration, table analysis
2. **SQL Execution** (4 tools): Query execution, validation, optimization
3. **Statistical Analysis** (4 tools): Statistics, correlations, data quality
4. **Investigation** (3 tools): Drill-downs, time comparisons, patterns
5. **Visualization** (6 tools): Bar, line, pie, scatter charts + smart suggestions
6. **Business Metrics** (5 tools): KPIs, summaries, anomaly detection

---

## 🏗️ System Architecture

```
┌──────────────────────────────────────────────────┐
│  Frontend (React + Chart.js + Tailwind)         │
│  User Interface | Progress Tracker | Charts     │
└───────────────────┬──────────────────────────────┘
                    │ REST API
┌───────────────────▼──────────────────────────────┐
│  API Gateway (FastAPI + CORS)                    │
└───────────────────┬──────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────┐
│  Agentic Investigation Engine                    │
│  Orchestrator | Context Manager | Synthesizer   │
└───────────────────┬──────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────┐
│  Dynamic Tool Registry (22 Tools)                │
└───────────────────┬──────────────────────────────┘
                    │
┌───────────────────▼──────────────────────────────┐
│  External Services                               │
│  Gemini LLM | PostgreSQL | Cache | Security     │
└──────────────────────────────────────────────────┘
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL (or Neon Database account)
- Google Gemini API key ([Get one here](https://ai.google.dev/))

### Installation

```bash
# 1. Clone repository
git clone <your-repo-url>
cd nl2sql

# 2. Backend Setup
cd backend
pip install -r requirements.txt
cp env.example config.env
# Edit config.env with your DATABASE_URL and GEMINI_API_KEY

# 3. Start Backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Frontend Setup (new terminal)
cd frontend
npm install
npm run dev

# 5. Open http://localhost:5173
```

### Verify Installation

- Backend: http://localhost:8000/health
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

---

## 📖 Usage Examples

### Basic Queries

```
"Show me top 10 customers by revenue"
→ Automatically queries database, generates chart, shows results

"What were our sales trends last quarter?"
→ Multi-step analysis with time series visualization

"Find unusual transactions in the last week"
→ Statistical anomaly detection with explanations

"Compare Q1 vs Q2 revenue"
→ Period comparison with percentage changes
```

### What Happens Behind the Scenes

1. **Query Understanding**: AI parses intent and entities
2. **Schema Discovery**: Automatically explores database structure
3. **Data Retrieval**: Generates and executes optimized SQL
4. **Statistical Analysis**: Calculates metrics and trends
5. **Anomaly Detection**: Identifies unusual patterns
6. **Visualization**: Creates appropriate interactive charts
7. **Business Context**: Provides KPIs and actionable insights
8. **Result Synthesis**: Combines everything into clear summary

---

## 🛠️ Technology Stack

### Backend
- **FastAPI**: Modern async Python web framework
- **AsyncPG**: High-performance PostgreSQL driver
- **Google Gemini 2.5 Flash**: LLM for reasoning and NLP
- **Pydantic**: Data validation

### Frontend
- **React 18**: UI framework with hooks
- **Vite**: Fast build tool
- **Tailwind CSS**: Utility-first styling
- **Chart.js**: Interactive visualizations
- **Axios**: HTTP client

### Database
- **PostgreSQL**: Primary database
- **Neon Database**: Cloud hosting

---

## 📁 Project Structure

```
nl2sql/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI app
│   │   ├── agentic_client.py    # Investigation engine
│   │   ├── database.py          # DB connection manager
│   │   └── tools/               # 22 specialized tools
│   ├── config.env               # Configuration
│   └── requirements.txt         # Dependencies
│
├── frontend/
│   ├── src/
│   │   ├── pages/
│   │   │   └── AgenticChatPage.jsx  # Main interface
│   │   ├── components/
│   │   │   └── ChartRenderer.jsx    # Visualization
│   │   └── services/
│   │       └── api.js               # API client
│   └── package.json
│
└── BTP_Report_Files/            # Academic report (LaTeX)
```

---

## 🔌 API Endpoints

### `POST /investigate`
Autonomous multi-step investigation

**Request:**
```json
{
  "query": "What are sales trends last month?"
}
```

**Response:**
```json
{
  "investigation_steps": [
    {
      "step_number": 1,
      "reasoning": "First, I'll discover the schema...",
      "tool_name": "get_database_schema",
      "result": { ... },
      "success": true
    }
  ],
  "final_answer": "Sales showed 15% growth...",
  "execution_time": 2.4
}
```

### `POST /query`
Simple NL2SQL (no investigation)

### `GET /tools`
List all 22 available tools

### `GET /health`
System health check

---

## 💡 Why Not Just Use ChatGPT?

### Capabilities Impossible with General AI Chatbots:

❌ **ChatGPT Can't:**
- Directly access your database
- Perform multi-step autonomous analysis
- Run statistical algorithms (Z-score, IQR)
- Generate interactive Chart.js visualizations
- Guarantee results with fallback pipeline
- Use 22 specialized business intelligence tools

✅ **Our System Can:** All of the above, automatically!

### Real-World Comparison

**ChatGPT Approach:**
1. You: "Analyze my sales data"
2. ChatGPT: "I can't access databases"
3. You: *Manually copy schema*
4. ChatGPT: *Gives you SQL*
5. You: *Run SQL, copy results back*
6. You: "Find anomalies"
7. ChatGPT: "Please provide statistical context"
8. **Total: 15+ manual steps, no charts**

**Our System:**
1. You: "Analyze my sales data"
2. System: *Complete analysis with charts in 3 seconds*
3. **Total: 1 step, zero manual work**

---

## 🎯 Example Use Cases

### 1. Revenue Analysis
```
Query: "Analyze revenue performance this month"
Output: Daily revenue trends (line chart), statistics, 
        anomalies highlighted, MoM comparison
```

### 2. Customer Insights
```
Query: "Find unusual customer behavior"
Output: Scatter plot, outlier customers identified,
        behavioral patterns, recommendations
```

### 3. Time Comparison
```
Query: "Compare this quarter vs last quarter"
Output: Side-by-side charts, % changes,
        key drivers, future projections
```

### 4. Data Quality
```
Query: "Check customer data quality"
Output: Quality scorecard, missing data visualization,
        duplicate detection, cleanup suggestions
```

---

## 🤖 Autonomous Features

### System Intelligence Beyond LLM

Our system actively contributes alongside the LLM:

- **Automatic Schema Caching**: Reduces repeated queries
- **Fallback Pipeline**: Guarantees results even if agent fails
- **Query Optimization**: Rewrites SQL for performance
- **Tool Orchestration**: Manages dependencies automatically
- **Error Recovery**: Retries and alternative approaches
- **Progress Tracking**: Real-time step-by-step updates

**Example**: When LLM asks for 3 tools, system automatically adds 5 more supporting tools for comprehensive analysis!

---

## 🚀 Future Roadmap

### Upcoming Features (Dec 2024 - Mar 2025)

- ✅ **Enhanced Visualization**: Heatmaps, sankey diagrams, dashboards
- ✅ **Performance Optimization**: Query caching, latency < 2s
- ✅ **Multi-Database Support**: MySQL, MongoDB, SQLite
- ✅ **Advanced Analytics**: Predictive models, ML integration
- ✅ **Vector Database**: Conversational memory with embeddings
- ✅ **Enterprise Features**: Authentication, multi-tenant, RBAC

---

## 👥 Team

**B.Tech Computer Science and Engineering**  
**Indian Institute of Information Technology Kottayam**

- Arjun Deshmukh (2022BCS0084)
- Rishi Pramod (2022BCS0089)
- Harsh Jain (2022BCS0231)
- Lakshmi Sreya (2022BCD0031)

**Supervisor:** Dr. Sara Renjit

---

## 📊 Project Stats

- **Lines of Code**: 8,000+
- **Specialized Tools**: 22
- **API Endpoints**: 10+
- **Database Tables**: 4 core tables
- **Tool Categories**: 6
- **Visualization Types**: 4+
- **Average Investigation Time**: 2-5 seconds

---

## 🔒 Configuration

### Environment Variables (`backend/config.env`)

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Google Gemini API
GEMINI_API_KEY=your_api_key_here

# Application
DEBUG=True
CORS_ORIGINS=["http://localhost:5173", "http://localhost:3000"]
```

---

## 📚 Documentation

- **`PROJECT_README.md`**: Comprehensive documentation (1000+ lines)
- **`ARCHITECTURE.md`**: Detailed architecture diagrams
- **`ANOMALY_DETECTION_GUIDE.md`**: Anomaly detection algorithms
- **`BTP_Report_Files/`**: Academic report (LaTeX)

---

## 🐛 Troubleshooting

### Common Issues

**Backend won't start:**
```bash
# Check if port 8000 is available
netstat -ano | findstr :8000
# Install dependencies
pip install -r requirements.txt
```

**Frontend build fails:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
```

**Database connection error:**
- Verify `DATABASE_URL` in `config.env`
- Check PostgreSQL is running
- Test connection with `psql` command

**Gemini API error:**
- Verify `GEMINI_API_KEY` is correct
- Check API quota at https://ai.google.dev/

---

## 🤝 Contributing

This is an academic project. For questions or suggestions:
- **Institution**: Indian Institute of Information Technology Kottayam
- **Location**: Kottayam-686635, Kerala, India

---

## 📜 License

Academic project for B.Tech degree requirements. All rights reserved by the project team and IIIT Kottayam.

---

## 🙏 Acknowledgments

- Google Gemini Team for the LLM API
- FastAPI & React communities for excellent frameworks
- Chart.js for visualization capabilities
- IIIT Kottayam for academic support

---

## ⭐ Quick Links

- **Live Demo**: *(Coming Soon)*
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Frontend**: http://localhost:5173

---

**Built with ❤️ by Team Agentic AI @ IIIT Kottayam**

*Last Updated: November 2025*
