# UET Mardan Prospectus Assistant

A React + Vite frontend with a FastAPI backend for a RAG-powered university prospectus assistant.

## Local setup

1. Install dependencies:

```bash
cd "c:\Users\Tooba Munir\Downloads\filessssss"
npm install
pip install -r requirements.txt
```

2. Put your prospectus PDF in the project root, for example:

```bash
c:\Users\Tooba Munir\Downloads\filessssss\UG-Porspectus-2024-25.pdf
```

3. Index the PDF:

```bash
python ingestion_pipeline.py --source "UG-Porspectus-2024-25.pdf"
```

4. Start the backend:

```bash
python -m uvicorn server:app --reload --port 8000
```

5. Start the frontend:

```bash
npm run dev
```

Open `http://localhost:5173/` in the browser.

## Important notes

- Keep secrets out of version control. `.env` is ignored by `.gitignore`.
- If the app still cannot answer questions, make sure the prospectus is indexed successfully.









