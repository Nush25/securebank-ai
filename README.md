# SecureBank AI

**A local-first, RAG-powered banking assistant built with Generative AI.**

SecureBank AI is an intelligent banking assistant that answers questions using a knowledge base of banking documents. It uses Retrieval-Augmented Generation (RAG) to retrieve relevant information before generating responses, helping keep answers grounded in the available sources.

The application combines a Streamlit interface, FastAPI backend, local LLM inference with Ollama, FAISS vector search, and Supabase authentication.

## Features

- **RAG-based question answering:** Retrieves relevant information from banking documents before generating answers.
- **Local LLM inference:** Uses Ollama to run language models locally.
- **Semantic document search:** Uses embeddings and FAISS for similarity-based retrieval.
- **Source-aware responses:** Displays supporting sources and relevant excerpts.
- **User authentication:** Supports registration, login, email verification, and logout through Supabase Auth.
- **Conversation history:** Stores chat conversations locally using SQLite.
- **Modern interface:** Streamlit-based chat interface with light and dark themes.
- **REST API:** FastAPI backend with an interactive API documentation page.

## Tech Stack

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Frontend | Streamlit |
| Backend | FastAPI |
| LLM Runtime | Ollama |
| Language Model | Qwen |
| Embeddings | Nomic Embed Text |
| Vector Database | FAISS |
| Authentication | Supabase Auth |
| Local Database | SQLite |
| API Communication | REST, HTTP, JSON |

## Architecture

1. **User Interface:** Users interact with the assistant through the Streamlit chat interface.
2. **Authentication:** Supabase Auth handles user registration, login, and session authentication.
3. **API Layer:** Streamlit communicates with the FastAPI backend.
4. **Document Processing:** Banking documents are loaded, split into chunks, and converted into embeddings.
5. **Retrieval:** FAISS searches for relevant document chunks based on the user's question.
6. **Generation:** The retrieved context is passed to the local Ollama language model.
7. **Response:** The assistant generates an answer and presents supporting source information.
8. **History:** Conversations are stored locally using SQLite.

## Project Structure

```text
SecureBankingAssistant/
│
├── backend/
│   ├── app/
│   │   ├── core/
│   │   ├── routes/
│   │   ├── schemas/
│   │   └── services/
│   └── main.py
│
├── frontend/
│   ├── app.py
│   └── auth_client.py
│
├── data/
│   └── documents/
│       ├── banking_fundamentals.txt
│       └── banking_policy.txt
│
├── tests/
│
├── requirements.txt
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Nush25/securebank-ai.git
cd securebank-ai
```

### 2. Create a virtual environment

```bash
python -m venv venv
```

Activate it on Windows PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
SUPABASE_URL=your_supabase_project_url
SUPABASE_PUBLISHABLE_KEY=your_supabase_publishable_key
APP_ENV=local
```

Replace the placeholders with your own Supabase project values.

**Never commit your actual `.env` file or authentication secrets to GitHub.**

### 5. Set up Ollama

Install Ollama and download the required models:

```bash
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

Make sure Ollama is running before starting the application.

The model configuration in the application should match the model names installed locally.

### 6. Run the backend

Open a terminal in the project directory:

```bash
python -m uvicorn backend.main:app --reload
```

Backend API:

```text
http://127.0.0.1:8000
```

Interactive API documentation:

```text
http://127.0.0.1:8000/docs
```

### 7. Run the frontend

Open another terminal, activate the virtual environment, and run:

```bash
python -m streamlit run frontend/app.py
```

The Streamlit application will open in your browser.

## Security Considerations

- Authentication is handled through Supabase Auth.
- Protected backend endpoints require authentication.
- Conversation access is scoped to the authenticated user.
- Local chat history and generated data are excluded from version control.
- Ollama provides local model inference.
- Do not enter real banking credentials, PINs, OTPs, or sensitive financial information.

## Disclaimer

SecureBank AI is an educational and portfolio project. It uses sample banking documents and is not connected to real banking systems. Its responses should not be treated as official financial advice or banking instructions.

## Author

**Anushka Patil**

- GitHub: [@Nush25](https://github.com/Nush25)

---

*Built as a practical exploration of Retrieval-Augmented Generation, Large Language Models, API development, and AI application engineering.*