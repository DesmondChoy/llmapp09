# Workflows and vulnerability policy

The four workflows and required secrets are described in [README.md](README.md).
Both image pipelines build, scan, and publish the exact scanned image.
Trivy Action is pinned to the v0.36.0 commit and runs Trivy v0.74.0. Scan output
is retained as a JSON artifact even when the scan fails. HIGH and CRITICAL
findings block publication, including unfixed findings. `.trivyignore` has no exceptions.

The previous Debian-based images failed with 38 HIGH operating-system findings
each. Removing the old ignore list also exposed vulnerable backend Starlette
and pip-bundled packages. Images now use Python 3.12 on Alpine 3.24, upgrade
Alpine packages, and remove pip after installation. FastAPI is upgraded and
Starlette has an explicit security floor. Install additional Guardrails Hub
validators at build time.

Any future exception must identify the package, application exposure, reason
for accepting the finding, and a review date. A failing scan does not establish
successful publication.

Verify changes by running Ruff, backend tests, image builds and scans, workflow
and manifest validation, and frontend-to-backend requests. Check that metrics
survive container replacement. After pushing, inspect Actions results and Docker
Hub publication, and run both evaluation workflows when application behavior changes.

Image jobs use AMD64 runners. Native ARM Minikube deployment is documented in
the root README. Image workflow filters include `.trivyignore`; evaluation
filters include Compose. Image workflows support version tags and manual dispatch.

Official references: [Trivy Action](https://github.com/aquasecurity/trivy-action),
[Python images](https://hub.docker.com/_/python).
Actual results: [verification evidence](docs/verification.md).
