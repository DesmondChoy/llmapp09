# Frontend Kubernetes deployment

Follow [Deploy to Minikube](../README.md#deploy-to-minikube).

The manifest defines namespace `llm-frontend`, a Deployment, Service, and
ConfigMap. The frontend listens on 5000 and reaches the backend through
`llm-multiroute-service.llm-multiroute-backend.svc.cluster.local:8080`.

The default image is `insipidity/llm-frontend-python:latest`; the deployment
script can select another tag. Use `5001:5000` for local port forwarding if
port 5000 is already occupied.
