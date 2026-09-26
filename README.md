# LLMSecOps workshop: llmapp09

This repository implements the final CI/CD exercise in
`LLMSecOps_Workshop_v1.0.pdf`, pages 38–52. A Flask frontend calls a FastAPI
backend for classification, sentiment, summarization, and intent using Ollama
Cloud. The backend includes guardrails, saved metrics, and optional Langfuse
tracing. Promptfoo and DeepEval evaluate the application.

## Run with Docker Compose

Requirements: Docker with Compose and an Ollama Cloud API key.
Run commands from this repository's root:

```sh
cp .env.example .env
# Edit .env and set OLLAMA_API_KEY. Do not commit .env.
docker compose up -d --build --wait
docker compose ps
```

Open <http://localhost:5000> and <http://localhost:8080/swagger-ui.html>.
If macOS AirPlay occupies port 5000, set `FRONTEND_PORT=5001` in `.env` and use
<http://localhost:5001>. `BACKEND_PORT` changes the backend's host port;
communication between containers continues to use port 8080.

An existing environment file can be supplied explicitly:

```sh
FRONTEND_PORT=5001 docker compose --env-file ../.env up -d --build --wait
```

Both services have health checks. The frontend waits for a healthy backend.
The `llm-metrics` named volume stores `/app/metrics` and survives container
replacement and `docker compose down`. `docker compose down --volumes` deletes
that saved data. Both services share a Docker network.

Set both Langfuse keys in `.env` to enable tracing. Blank keys leave tracing
unconfigured. Dependencies are installed while building the images; the runtime
images omit pip. Install additional Guardrails validators in the Dockerfile
before pip is removed.

## GitHub Actions

| Workflow | Checks and outputs |
| --- | --- |
| LLM Multiroute CI | Ruff, backend unit tests, image build, Trivy, Docker Hub publication |
| LLM Frontend Python CI | Ruff, image build, Trivy, Docker Hub publication |
| PromptFoo Tests | Four evaluations against a backend started with Compose |
| DeepEval Tests | Judge integration tests and four evaluation suites against the backend |

Configure **Settings → Secrets and variables → Actions**:

| Secret or variable | Purpose |
| --- | --- |
| `DOCKERHUB_TOKEN` secret | Read/write token for Docker account `insipidity` |
| `OLLAMA_API_KEY` secret | Backend inference and DeepEval judge access |
| `OLLAMA_BASE_URL` secret | Ollama endpoint, normally `https://ollama.com` |
| `DEEPEVAL_OLLAMA_MODEL` optional variable | Judge model; defaults to `gemma4:31b` |

DeepEval uses Ollama Cloud, so `OPENAI_API_KEY` is unnecessary. The workshop
allows this alternative on page 23, although page 52 lists the OpenAI key.

Image workflows run for component changes, scanner-policy changes, `v*` tags,
and manual dispatch. Evaluation workflows also run when Compose changes.
Pushes to `main` publish `latest`, `main`, and `sha-<short-commit>` tags after
scanning. A tag such as `v1.0.0` publishes `1.0.0`. Pull requests build and scan
without publishing. CI publishes the exact image that passed the scan.

Trivy blocks on every HIGH or CRITICAL finding, including unfixed findings.
There are currently no ignored vulnerabilities. Each image workflow uploads
`trivy-results.json` even when its scan fails. See [workflow_readme.md](workflow_readme.md).

To run Promptfoo locally, start Compose, use Node 22.22 or newer, and run
`npm run eval` from `promptfoo-tests`. The evaluation configurations use backend
port 8080. DeepEval setup is in
[deepeval-tests/DEEPEVAL_INSTRUCTIONS.md](deepeval-tests/DEEPEVAL_INSTRUCTIONS.md).

## Deploy to Minikube

Install `kubectl` and `minikube`, start Docker, and run:

```sh
minikube start --driver=docker
```

Minikube's default storage provisioner supplies the backend's 1 GiB persistent
volume. GitHub's image jobs build Linux AMD64 images. On an ARM Mac, build and
load native images locally:

```sh
IMAGE_TAG=local bash llm-multiroute/build.sh
IMAGE_TAG=local bash llm-frontend-python/build.sh
minikube image load insipidity/llm-multiroute:local
minikube image load insipidity/llm-frontend-python:local
IMAGE_TAG=local bash scripts/deploy-kubernetes.sh .env
```

For an AMD64 cluster, after CI has published both images:

```sh
bash scripts/deploy-kubernetes.sh .env
```

The script explicitly targets context `minikube`; set `KUBE_CONTEXT` to select
another context deliberately. It creates the backend Secret from the local
environment file, applies both manifests, and waits for both deployments.
Use unquoted `KEY=value` lines. `OLLAMA_API_KEY` must be nonempty.
Optional Langfuse keys come from that Secret. Non-secret Kubernetes model and
host settings are configured in the manifests' ConfigMaps.

The manifests use `latest` with `imagePullPolicy: Always`. Set `IMAGE_TAG` to a
published version, a commit tag shared by both images, or a locally loaded tag
to deploy that tag with `IfNotPresent`. The backend runs one replica; Recreate
updates prevent simultaneous writers to its persistent metrics files.

In separate terminals:

```sh
kubectl --context minikube -n llm-multiroute-backend port-forward svc/llm-multiroute-service 8080:8080
kubectl --context minikube -n llm-frontend port-forward svc/llm-frontend-service 5001:5000
```

Stop Compose first if its host ports conflict. Open <http://localhost:5001>.
The frontend reaches the backend using Kubernetes service DNS across namespaces.

## Workshop requirement mapping

| PDF pages | Implementation |
| --- | --- |
| 43–44: Dockerfiles, Compose, networking, persistence | Two Dockerfiles, Compose, health checks, metrics volume |
| 47: Kubernetes deployment | Both `k8s/deployment.yaml` files and `scripts/deploy-kubernetes.sh` |
| 49–50: Image pipelines, Trivy, Docker Hub | Two image workflows using Docker account `insipidity` |
| 50: Promptfoo and DeepEval | Two evaluation workflows and their test directories |
| 51–52: GitHub repository and secrets | This repository and Actions configuration above |

The PDF uses both `LLM-python` and `llm-multiroute` for the backend. This solution
uses `llm-multiroute`, matching pages 47 and 49. The `llm-python` directory is
retained as workshop reference code.

## Verification evidence

See [docs/verification.md](docs/verification.md) for dated checks, scan results,
and remaining unverified steps. Earlier green workflow runs are historical
evidence; they do not validate later local edits.
