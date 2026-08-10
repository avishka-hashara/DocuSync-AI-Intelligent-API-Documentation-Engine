# DocuSync AI: Intelligent API Documentation Engine

> An automated, AI-powered documentation generator designed to seamlessly parse codebases, understand complex API structures, and generate precise, human-readable documentation. 

---

## Project Overview

**DocuSync AI** bridges the gap between development and documentation. By utilizing Abstract Syntax Tree (AST) parsing combined with advanced AI models, it automatically analyzes your backend code to generate, update, and serve comprehensive API documentation. 

The system features a robust Python backend for code analysis and AI processing, alongside a modern Next.js frontend for an intuitive, real-time user experience via WebSockets.

---

## Key Features

*   **Intelligent AST Parsing:** Deep code analysis through native Python AST parsing to understand endpoints, models, and relationships.
*   **AI-Powered Generation:** Leverages Large Language Models (LLMs) to draft context-aware, accurate descriptions for your API routes.
*   **Real-Time Sync:** WebSockets (`ws_manager.py`) ensure that documentation updates are pushed to the client instantly.
*   **Full-Stack Architecture:** Containerized, microservices-ready setup with dedicated frontend, backend, and worker nodes.
*   **Modern UI/UX:** Built with Next.js and Tailwind CSS for a seamless, responsive documentation viewing and management experience.

---

## Architecture & Tech Stack

### Frontend
*   **Framework:** Next.js (React)
*   **Styling:** Tailwind CSS
*   **Language:** TypeScript 

### Backend
*   **Language:** Python
*   **Database:** PostgreSQL (`database.py`, `models.py`)
*   **Core Modules:** 
    *   `ast_parser.py`: Extracts structural data from code.
    *   `test_ai.py` / `ingest.py`: AI integration and data ingestion.
    *   `ws_manager.py`: Handles real-time client-server communication.

### Infrastructure
*   **Containerization:** Docker & Docker Compose (`docker-compose.yml`, `docker-compose.prod.yml`)
*   **Version Control:** Git

---

## Project Structure

```text
DocuSync-AI-Intelligent-API-Documentation-Engine/
├── backend/                  # Python backend services
│   ├── ast_parser.py         # Code syntax tree parser
│   ├── database.py           # Database connection & sessions
│   ├── ingest.py             # Data ingestion pipeline
│   ├── main.py               # Main application entry point
│   ├── models.py             # Database models/schemas
│   ├── ws_manager.py         # WebSocket management
│   ├── requirements.txt      # Python dependencies
│   └── Dockerfile            # Backend container configuration
├── frontend/                 # Next.js frontend application
│   ├── src/app/              # Next.js app router & pages
│   ├── package.json          # Node.js dependencies
│   ├── tailwind.config.ts    # Tailwind styling configuration
│   └── Dockerfile            # Frontend container configuration
├── worker/                   # Background job processors
├── docker-compose.yml        # Local development setup
└── docker-compose.prod.yml   # Production deployment setup

```

---

## Getting Started

### Prerequisites

Ensure you have the following installed on your local machine:

* **Docker** and **Docker Compose**
* **Node.js** (v18+ recommended)
* **Python** (3.10+ recommended)
* **PostgreSQL** (if running locally without Docker)

### Installation & Execution

**1. Clone the repository**

```bash
git clone [https://github.com/your-org/DocuSync-AI-Intelligent-API-Documentation-Engine.git](https://github.com/your-org/DocuSync-AI-Intelligent-API-Documentation-Engine.git)
cd DocuSync-AI-Intelligent-API-Documentation-Engine

```

**2. Configure Environment Variables**
Create a `.env` file in the root directory (and inside `/backend` and `/frontend` as needed).

```env
# Example Backend .env
DATABASE_URL=postgresql://user:password@localhost:5432/docusync
AI_API_KEY=your_ai_service_api_key

# Example Frontend .env
NEXT_PUBLIC_API_URL=http://localhost:8000

```

**3. Run with Docker Compose (Recommended)**
To spin up the entire stack (Frontend, Backend, Database, and Worker):

```bash
docker-compose up --build

```

**4. Access the Application**

* **Frontend:** Navigate to `http://localhost:3000`
* **Backend API:** Navigate to `http://localhost:8000` (or `http://localhost:8000/docs` for standard Swagger UI)

---

## Testing

The backend includes a comprehensive suite of tests to ensure stability and accuracy in AI generation and database operations.

To run the backend tests locally:

```bash
cd backend
python -m pytest test_db.py test_ai.py test_postgres.py test_import.py

```

---

## Contributing

We welcome contributions to DocuSync AI!

1. Fork the repository.
2. Create a new branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

```

```
