# ACA on Arc — Demo Apps

A set of container apps demonstrating **Azure Container Apps on an Arc-enabled k3s cluster**, built and deployed to a connected environment (`nvidiartx-sff-env`) on an on-prem single-node k3s cluster.

## Apps

### `add-numbers`
A Flask web app that adds two numbers and displays the sum. The **v2** version also calls the `tinyllama-fact` service to show an AI-generated fun fact about the result in a text box.

- Port: `8080` (gunicorn)
- Public (external) ingress
- Env vars: `FACT_SERVICE_URL` (internal URL of the fact service), `FACT_TIMEOUT`

### `tinyllama-fact`
A CPU-only LLM inference service running **TinyLlama-1.1B-Chat** (GGUF Q4_K_M) via `llama-cpp-python`'s OpenAI-compatible server.

- Port: `8000`
- Internal ingress only (consumed by `add-numbers`)
- CPU-only; compiled with AVX2/FMA/F16C (no AVX-512) for broad CPU compatibility
- The model is baked into the image at build time
- **GPU variant**: `Dockerfile.gpu` builds a CUDA image (targets RTX 5060 / Blackwell `sm_120`) that offloads all layers to an NVIDIA GPU. Deploy with `k8s/tinyllama-gpu-deploy.yaml` as a plain k8s workload (ACA-on-Arc cannot request GPUs).

### `camera-stream`
A plain-Kubernetes app (not ACA) that mounts a USB camera (`/dev/video0`) via `hostPath` + privileged securityContext and serves a live MJPEG stream over HTTP. ACA cannot mount host devices, so this runs as a raw k8s Deployment.

- Port: `8080`
- Requires `hostPath` device mount + `privileged: true`

## Build

Each app builds with Azure Container Registry (no local Docker needed):

```bash
az acr build --registry <your-acr> --image <name>:<tag> --file Dockerfile .
```

## Deploy (ACA apps)

```bash
az containerapp create \
  --resource-group <rg> --name <name> \
  --environment <connected-env-id> --environment-type connected \
  --image <acr>.azurecr.io/<name>:<tag> \
  --target-port <port> --ingress <external|internal> \
  --registry-server <acr>.azurecr.io --registry-username <user> --registry-password <pass>
```

## Notes

- `tinyllama-fact` and `add-numbers` run on the ACA Arc connected environment.
- `camera-stream` runs as a plain k8s Deployment because ACA does not support `hostPath`, device mounts, or privileged containers.

## Kubernetes manifests (`k8s/`)

- `nvidia-device-plugin.yaml` — NVIDIA device plugin DaemonSet (exposes `nvidia.com/gpu`). Configured with `runtimeClassName: nvidia` and `NVIDIA_VISIBLE_DEVICES=all` so NVML loads correctly on k3s.
- `gpu-test.yaml` — sample CUDA vectoradd pod to validate GPU scheduling (`Test PASSED`).
- `tinyllama-gpu-deploy.yaml` — Deployment + Service for the GPU TinyLlama variant, requesting `nvidia.com/gpu: 1` in the `gpu-workloads` namespace.
