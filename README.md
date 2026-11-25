# KestrelSQL

**A lightweight SQL database engine built from scratch using Python, with a Flask-powered web interface.**

KestrelSQL is a custom SQL engine that processes SQL commands, manages tables and records, and executes queries through a browser-based SQL editor. It is designed to explore the fundamentals of database systems, SQL parsing, query execution, and data manipulation without relying on an external database engine for its core operations.

## Overview

KestrelSQL provides a custom query-processing pipeline that analyzes SQL statements and delegates execution to specialized modules.

Users can write SQL queries in an interactive web interface, execute them, and inspect query results and execution time.

## Features

- **SQL Query Execution:** Execute SQL statements through a browser-based editor.
- **Data Definition Language (DDL):** Create and manage database tables.
- **Data Manipulation Language (DML):** Insert, update, and delete records.
- **Data Query Language (DQL):** Retrieve records using SELECT queries.
- **Filtering and Sorting:** Support for WHERE, ORDER BY, and LIMIT clauses.
- **Aggregate Operations:** Perform aggregate calculations and grouped queries.
- **Conditional Processing:** Handle query conditions and filtering logic.
- **Transaction Control:** Dedicated module for transaction-related commands.
- **Execution Timing:** Display query execution time in the interface.
- **Flask API:** Connect the frontend to the Python SQL execution engine.

## Tech Stack

| Component | Technology |
|---|---|
| Backend | Python |
| Web Framework | Flask |
| Frontend | HTML, CSS, JavaScript |
| Query Processing | Custom SQL parser and execution logic |
| Containerization | Docker |
| Deployment | Railway |

## Project Structure

```text
kestrel/
│
├── api.py
├── main.py
├── processing.py
├── database.py
│
├── sql_modules/
│   ├── ddl.py
│   ├── dml.py
│   ├── dql.py
│   ├── conditions.py
│   ├── constraints.py
│   ├── aggregate.py
│   ├── tcl.py
│   └── dcl.py
│
├── templates/
│   └── index.html
│
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```

## How It Works

KestrelSQL follows a modular query-execution architecture:

1. **Query Input:** The user enters an SQL statement in the web interface.
2. **API Request:** The frontend sends the query to the Flask backend.
3. **Query Analysis:** The processing module analyzes the SQL command and identifies its operation.
4. **Command Execution:** The corresponding SQL module handles the requested operation.
5. **Database Operations:** The database module manages the underlying table and record structures.
6. **Query Response:** The API returns the execution result, errors, and timing information to the frontend.

## Supported SQL Operations

The engine is organized into separate modules for different SQL operations.

| Category | Operations |
|---|---|
| DDL | CREATE TABLE, DROP TABLE |
| DML | INSERT, UPDATE, DELETE |
| DQL | SELECT |
| Filtering | WHERE, AND, OR |
| Aggregation | COUNT, SUM, AVG, MIN, MAX |
| Grouping | GROUP BY, HAVING |
| Sorting | ORDER BY |
| Limiting | LIMIT |
| Transaction Control | TCL module |
| Access Control | DCL module |

*Note: The engine implements a subset of SQL functionality. Support for individual commands and clauses depends on the current implementation.*

## Getting Started

### Prerequisites

- Python 3.10 or later
- pip
- Git

### 1. Clone the Repository

```bash
git clone https://github.com/Ananya-vastare/kestrel.git
cd kestrel
```

### 2. Create a Virtual Environment

**Windows:**

```powershell
py -m venv .venv
.venv\Scripts\activate
```

**Linux / macOS:**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the Application

```bash
python api.py
```

Open the local application in your browser at:

```text
http://127.0.0.1:5000
```

## Running with Docker

Build the Docker image:

```bash
docker build -t kestrelsql .
```

Run the container:

```bash
docker run -p 8080:8080 -e PORT=8080 kestrelsql
```

Open:

```text
http://localhost:8080
```

## Current Limitations

- Database records are stored in memory and are not persistent across application restarts.
- The engine supports a subset of SQL rather than the complete SQL standard.
- It is intended as a learning and demonstration project, not as a production-ready database replacement.

## Future Improvements

- Persistent database storage.
- Expanded SQL syntax and query support.
- Query optimization and execution planning.
- Improved constraint and transaction handling.
- Indexing and performance benchmarking.
- More comprehensive error handling and test coverage.

## BENCHMARK
<img width="537" height="833" alt="Screenshot 2026-11-25 184739" src="https://github.com/user-attachments/assets/9283431b-c0e7-4c66-9f19-9ddc035e77c2" />

## Author

**Ananya Ravikiran Vastare**

- GitHub: [Ananya-vastare](https://github.com/Ananya-vastare)

---

*KestrelSQL — Exploring database internals, one query at a time.*
