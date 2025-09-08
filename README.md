# Opinion Analysis Server

This Flask server provides endpoints for processing text segments using a Llama 2 LLM model, saving summaries, and retrieving data points.

## Setup

You need to setup Your `GROQ_API_KEY`, `OPENAI_API_KEY` and `ANNOTATION_DATA_FILE` environment variables.

Start the server with:
```bash
uv run app.py --port 3002
```

The server will run on `localhost:3002`.

