# Docker setup

Follow the [root README](README.md#run-with-docker-compose) for maintained setup
instructions, environment configuration, ports, and metrics persistence.

Both images use Python 3.12 on Alpine 3.24. Internal ports are 8080 for the
backend and 5000 for the frontend. Health checks wait for readiness. The named
volume stores `/app/metrics` across container replacements.

The component `build.sh` scripts build for the local machine by default. Set
`PLATFORM=linux/amd64` or `PLATFORM=linux/arm64` to choose a platform, and
`IMAGE_TAG=local` or a version to choose a tag. They build without publishing.
Use CI for scanned publication. `PUSH=1` explicitly enables a manual push; it
does not perform a vulnerability scan.
