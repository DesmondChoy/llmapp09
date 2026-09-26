#!/usr/bin/env bash
# Deploy to the explicitly selected local cluster; credentials stay out of Git.
set -euo pipefail
repo_dir="$(cd "$(dirname "$0")/.." && pwd)"
env_file="${1:-$repo_dir/.env}"
context="${KUBE_CONTEXT:-minikube}"
image_tag="${IMAGE_TAG:-latest}"

if [[ ! "$image_tag" =~ ^[a-zA-Z0-9_][a-zA-Z0-9_.-]{0,127}$ ]]; then
  echo 'IMAGE_TAG must be a valid Docker tag.' >&2
  exit 1
fi
if [[ ! -f "$env_file" ]]; then
  echo "Create $env_file from .env.example and set OLLAMA_API_KEY first." >&2
  exit 1
fi
# kubectl --from-env-file uses literal KEY=value lines, not shell expansion.
if ! awk -F= '$1 == "OLLAMA_API_KEY" && length(substr($0,index($0,"=")+1)) > 0 {found=1} END {exit !found}' "$env_file"; then
  echo 'OLLAMA_API_KEY must be nonempty in the environment file.' >&2
  exit 1
fi
kubectl --context "$context" cluster-info >/dev/null
kubectl --context "$context" create namespace llm-multiroute-backend --dry-run=client -o yaml |
  kubectl --context "$context" apply -f -
kubectl --context "$context" -n llm-multiroute-backend create secret generic llm-multiroute-secret \
  --from-env-file="$env_file" --dry-run=client -o yaml |
  kubectl --context "$context" apply -f -

manifest_dir="$(mktemp -d)"
trap 'rm -rf "$manifest_dir"' EXIT
cp "$repo_dir/llm-multiroute/k8s/deployment.yaml" "$manifest_dir/backend.yaml"
cp "$repo_dir/llm-frontend-python/k8s/deployment.yaml" "$manifest_dir/frontend.yaml"
pull_policy=Always
if [[ "$image_tag" != latest ]]; then pull_policy=IfNotPresent; fi
cat > "$manifest_dir/kustomization.yaml" <<EOF
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - backend.yaml
  - frontend.yaml
images:
  - name: insipidity/llm-multiroute
    newTag: "$image_tag"
  - name: insipidity/llm-frontend-python
    newTag: "$image_tag"
patches:
  - target:
      kind: Deployment
    patch: |-
      - op: replace
        path: /spec/template/spec/containers/0/imagePullPolicy
        value: $pull_policy
EOF
kubectl --context "$context" apply -k "$manifest_dir"
# Environment variables do not refresh automatically after Secret/ConfigMap edits.
kubectl --context "$context" -n llm-multiroute-backend rollout restart deployment/llm-multiroute-app
kubectl --context "$context" -n llm-frontend rollout restart deployment/llm-frontend-app
kubectl --context "$context" -n llm-multiroute-backend rollout status deployment/llm-multiroute-app --timeout=180s
kubectl --context "$context" -n llm-frontend rollout status deployment/llm-frontend-app --timeout=180s
