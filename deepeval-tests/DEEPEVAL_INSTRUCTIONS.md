# Project Structure

  deepeval-tests/
  ├── requirements.txt        # Python dependencies
  ├── api_client.py           # HTTP client for all 4 API endpoints
  ├── judge.py               # Ollama Cloud judge
  ├── conftest.py             # Shared metric factories and fixtures
  ├── test_classify.py        # 5 inputs × 3 metrics = 15 tests
  ├── test_sentiment.py       # 5 inputs × 4 metrics = 20 tests
  ├── test_summarize.py       # 5 inputs × 5 metrics = 25 tests
  └── test_intent.py          # 8 inputs × 4 metrics = 32 tests
  
  Total: 92 evaluation tests across all 4 endpoints.
  
  Endpoints Covered
  Endpoint: POST /api/ai/classify
  Test File: test_classify.py
  Inputs: 5 (tech, sports, food, finance, health)
  Metrics: Schema, Correctness, Relevancy
  ────────────────────────────────────────
  Endpoint: POST /api/ai/sentiment
  Test File: test_sentiment.py
  Inputs: 5 (positive, negative, neutral, mixed, positive)
  Metrics: Schema, Correctness, Emotion Detection, Relevancy
  ────────────────────────────────────────
  Endpoint: POST /api/ai/summarize
  Test File: test_summarize.py
  Inputs: 5 (AI/healthcare, climate, remote work, JWST, EVs)
  Metrics: Schema, Correctness, Conciseness, Faithfulness, Relevancy
  ────────────────────────────────────────
  Endpoint: POST /api/ai/intent
  Test File: test_intent.py
  Inputs: 8 (2× question, command, request, statement each)
  Metrics: Schema, Category Accuracy, Primary Intent, Relevancy
  Metrics Used

  - JSON Schema Compliance (GEval) -- validates response structure matches the DTO
  - Output Correctness (GEval) -- validates the analysis is accurate for the input
  - Answer Relevancy (GEval) -- validates response relevance to input
  - Endpoint-specific metrics (GEval):
    - Classification: label/category accuracy
    - Sentiment: emotion detection accuracy
    - Summarize: conciseness + faithfulness (no hallucinated facts)
    - Intent: category accuracy + primary intent accuracy

## Run locally

From the `llmapp09` repository root, install the evaluation dependencies:

```bash
python -m pip install -r deepeval-tests/requirements.txt
export OLLAMA_API_KEY="your-ollama-api-key"
export OLLAMA_BASE_URL="https://ollama.com"
export DEEPEVAL_OLLAMA_MODEL="gemma4:31b"
export DEEPEVAL_PER_TASK_TIMEOUT_SECONDS_OVERRIDE=900
docker compose up -d llm-multiroute
cd deepeval-tests
deepeval test run test_classify.py test_sentiment.py test_summarize.py test_intent.py -v
```

The tests call the application on port 8080. The judge calls Ollama Cloud using
`OLLAMA_API_KEY` and `OLLAMA_BASE_URL`, which defaults to `https://ollama.com`.
`DEEPEVAL_OLLAMA_MODEL` defaults to `gemma4:31b`. No OpenAI API key or local
Ollama installation is needed.

Ollama Cloud does not support enforced JSON schemas. The judge includes the
required schema in its prompt and validates the returned JSON before DeepEval
uses it. Invalid responses fail the evaluation rather than receiving a score.

Judge requests allow up to three attempts for timeouts, connection failures,
and HTTP 429, 500, 502, 503, or 504. Retries wait 2 seconds and then 4 seconds.
Each attempt uses a 10-second connection timeout and 120-second read timeout.
After the third failure, the request error fails the test. Authentication errors,
certificate errors, invalid JSON, and schema errors fail immediately. Scores do
not trigger retries. Warning logs report the error type and attempt number
without including prompts, credentials, or response bodies.

The 900-second DeepEval per-test deadline accommodates retries while generating
GEval evaluation steps and scoring. Its default 180-second deadline can cut
retries short. CI sets this override and retains its 60-minute job limit.

## GitHub Actions

Add `OLLAMA_API_KEY` as a repository Actions secret. `OLLAMA_BASE_URL` is an
optional secret; the workflow defaults to `https://ollama.com`. To choose another
cloud judge, set the repository Actions variable `DEEPEVAL_OLLAMA_MODEL`.

The workflow checks the judge integration, builds the application backend, and
runs all four suites. Both application requests and judge requests consume
Ollama Cloud usage. Changing the judge can change scores; previous OpenAI scores
are not directly comparable.

## Check the integration without model calls

```bash
python -m pytest deepeval-tests/unit -q
```

Run this command from the repository root. These checks cover authentication,
request routing, response validation, and judge selection across the four suites.
They also check recovery, retry exhaustion, backoff, and immediate failure for
errors that retries cannot resolve. These tests stub requests and waiting.
