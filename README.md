# RELVY TAKEHOME MVP

Relvy Takehome project: Allows user to upload their logs (in .json or .ndjson format) and get insights from an AI assistant. The logs uploaded are preprocessed to minimize API Costs

## Features

- **React Frontend**: Modern, responsive UI with drag-and-drop file upload
- **Intelligent Log Filtering**: multi-stage filtering
- **LLM Analysis**: GPT-4o mini integration with conversation context
- **Real-time Chat**: Ask multiple questions about uploaded logs
- **Cost Tracking**: Display LLM usage costs and token consumption

## Architecture

```
Frontend (React + Vite)     Backend (FastAPI + Python)
┌─────────────────────┐    ┌──────────────────────────┐
│ • File Upload       │    │ • Enhanced Log Filter    │
│ • Chat Interface    │────│ • GPT-4o Mini Service    │
│ • Conversation UI   │    │ • Conversation Context   │
└─────────────────────┘    └──────────────────────────┘
```

## Prerequisites

- **Node.js** (v16 or higher)
- **Python** (v3.8 or higher)
- **OpenAI API Key**

## Setup Instructions

### Backend Setup

1. **Navigate to backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create environment file:**
   ```bash
   # Create .env file in backend/ directory
   echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
   ```

5. **Start the backend server:**
   ```bash
   python main.py
   ```

### Frontend Setup

1. **Navigate to frontend directory:**
   ```bash
   cd frontend
   ```

2. **Install dependencies:**
   ```bash
   npm install
   ```

3. **Start the development server:**
   ```bash
   npm run dev
   ```

## Usage

1. **Upload Log File**: Drag and drop a `.json` or `.ndjson` file
2. **Ask Questions**: Type queries like "What errors do you see?" or "Why is the cart service crashing?"
3. **Get Insights**: Receive AI-powered analysis with cost breakdown

## Filtering & LLM Analysis Approach

### Multi-Stage Intelligent Filtering

#### 1. **Schema Normalization**
```python
# Defensive field extraction from various log formats
service_name = log.get('serviceName') or log.get('containerName') or 'unknown'
severity = extract_severity_from_message(log.get('body', ''))
```

#### 2. **Hot-Event Prefiltering**
- Error/warning detection in log messages
- HTTP status code analysis (4xx, 5xx)
- Exception pattern matching
- Critical keyword identification

#### 3. **Trace Context Grouping**
```python
# Group related logs by trace_id and time windows
windows = create_trace_windows(filtered_logs, window_size_seconds=30)
```

#### 4. **Template De-duplication**
- Extract log message templates
- Group similar messages
- Reduce noise from repetitive logs

#### 5. **Prompt-Aware Relevance Scoring**
```python
# Match user query against log content
query_terms = parse_query_advanced("cart service is crashing")
relevance_score = calculate_prompt_match_score(log, query_terms)
```

#### 6. **Importance Scoring**
- Severity-based weighting
- Error frequency analysis
- Service criticality assessment
- Time-based relevance

#### 7. **Structured Window Output**
```python
# Generate mini-summaries for each log window
{
  "summary": "3 errors, 2 warnings; cart-service (5x)",
  "logs": [...most_important_logs...]
}
```

**Built with using React, FastAPI, and OpenAI GPT-4o mini**
