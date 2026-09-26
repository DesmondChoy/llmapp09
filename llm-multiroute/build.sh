#!/usr/bin/env bash
set -euo pipefail
component_dir="$(cd "$(dirname "$0")" && pwd)"
image="insipidity/llm-multiroute"
tag="${IMAGE_TAG:-latest}"
build_args=(--pull -t "$image:$tag" "$component_dir")
if [[ -n "${PLATFORM:-}" ]]; then
  build_args=(--platform "$PLATFORM" "${build_args[@]}")
fi
docker build "${build_args[@]}"
# Publishing is explicit; CI scans images before it publishes them.
if [[ "${PUSH:-0}" == 1 ]]; then docker push "$image:$tag"; fi
