# Verification: 26 September 2026

These checks cover the local workshop fixes based on Git commit `52ba466`.
They do not claim a new GitHub Actions run or Docker Hub publication.

## Image security

Both final Dockerfiles were built for ARM64 (this Mac) and AMD64 (GitHub CI).
Trivy 0.74.0 scanned exported image archives for operating-system and Python
vulnerabilities, with `--severity HIGH,CRITICAL --exit-code 1`. No ignore file
or unfixed-vulnerability exclusion was used.

| Image | Platform | HIGH | CRITICAL |
| --- | --- | ---: | ---: |
| Backend | linux/arm64 | 0 | 0 |
| Frontend | linux/arm64 | 0 | 0 |
| Backend | linux/amd64 | 0 | 0 |
| Frontend | linux/amd64 | 0 | 0 |

[image-scan-summary.json](image-scan-summary.json) records image identifiers,
source-file hashes, scan-report hashes, and the scan policy. These results apply
to those builds and the vulnerability database at scan time. Future builds must
pass their own scans. LOW and MEDIUM findings were outside this gate.

The original `.trivyignore` exceptions were removed. Alpine replaces the affected
Debian runtime; FastAPI/Starlette are upgraded; pip and its bundled dependencies
are removed from runtime images after application dependencies are installed.
The application uses its existing custom validators; installing new Guardrails
Hub packages requires rebuilding the image.

## Application and configuration checks

- All **72 backend unit tests** passed inside the final ARM64 runtime.
  Existing dependency deprecation warnings remain.
- All **17 Promptfoo cases** passed against the upgraded local backend:
  classification 4/4, sentiment 5/5, summarization 3/3, and intent 5/5.
  The run used Node 22.23.3; the preinstalled Node 22.17.1 was below Promptfoo's
  current minimum, so a verified temporary Node binary was used.
- Ruff passed for both components, using each component as the working directory,
  matching the CI layout.
- Actionlint 1.7.12 passed all four workflows.
- Kubeconform 0.8.0 validated all **9 Kubernetes resources** with strict schemas.
- Shell syntax and Git whitespace checks passed.
- The deployment helper rejects an empty Ollama key before contacting a cluster.

## Docker Compose

Both containers reached healthy status. The frontend was exposed on port 5001
because macOS occupied port 5000; the backend used port 8080.

A live classification request travelled through the frontend proxy, backend,
and configured Ollama model, returning HTTP 200 with the expected response
fields. The resulting saved request count survived forced replacement of both
containers. The named volume preserves `/app/metrics`.

## Kubernetes

An isolated Minikube 1.39.0 cluster ran Kubernetes 1.37.0 with the Docker driver.
Its kubeconfig and Minikube data were kept in temporary storage; the user's
default Kubernetes configuration was not changed.

The scanned native images were tagged `local`, loaded into the cluster, and
deployed with `scripts/deploy-kubernetes.sh`. Both deployments reached 1/1 ready
replicas and the metrics persistent volume claim reached `Bound`.

A live classification request through the Kubernetes frontend reached the
backend across namespaces and returned HTTP 200. Its saved metrics survived a
backend deployment restart. The temporary cluster was stopped after verification.

## Remaining publication checks

These local checks were completed before publication. For the commit carrying
these fixes, verify both image workflows complete their Docker Hub login and
publication steps, and inspect the uploaded Trivy artifacts. A local green scan
cannot verify the repository's Docker Hub token permissions or remote publication.

The earlier DeepEval run passed 92 evaluation checks and 8 judge integration
tests at commit `52ba466`; those are historical results. This change does not
alter the judge or evaluation criteria. The complete DeepEval judge suite was
not rerun locally.

Optional Langfuse tracing was not tested against a configured Langfuse project.
Its Kubernetes environment references and optional secret fields were validated.
