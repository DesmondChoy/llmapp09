# Backend Kubernetes deployment

Follow [Deploy to Minikube](../README.md#deploy-to-minikube).

The manifest defines a namespace, single-replica Deployment, Service, ConfigMap,
and persistent volume claim. It references an externally created
`llm-multiroute-secret`. Real credentials never belong in the manifest.
The deployment script creates or updates the Secret from a local environment
file before applying workloads. Optional Langfuse keys use the same Secret.

The metrics volume is mounted at `/app/metrics`. Recreate updates keep one
writer to these JSON files. Model names, Ollama URL, temperature, and Langfuse
host are set in the ConfigMap. The default image is
`insipidity/llm-multiroute:latest`; the script can select another tag.
