# Opinion Analysis Server

This Flask server provides endpoints for processing text segments using a Llama 2 LLM model, saving summaries, and retrieving data points.

## Setup


Start the server with:
```bash
uv run app.py --port 3002
```

The server will run on `localhost:3002`.

## API Endpoints

### POST /opinion-response
Process text segments to extract arguments.

Request body:
```json
{
    "opinionId": "string",
    "segments": ["text1", "text2", ...]
}
```

### POST /summaries
Save segment summaries.

Request body:
```json
[
    {
        "segment": "text1",
        "summary": "summary1"
    },
    ...
]
```

### GET /next-data
Retrieve the next data point from the input JSONL file.

## Data Storage

- Summaries are stored in `summaries.jsonl`
- Input data should be in `data.jsonl` 
