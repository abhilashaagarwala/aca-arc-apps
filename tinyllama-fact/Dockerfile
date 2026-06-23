FROM python:3.11-slim

# Build toolchain (to compile llama-cpp-python against glibc) + curl for the model
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl build-essential cmake git \
    && rm -rf /var/lib/apt/lists/*

# Compile llama-cpp-python from source (glibc-compatible). Disable GGML_NATIVE so the
# build agent's -march=native (AVX-512) isn't baked in; the target node (Intel Core 5 120)
# supports only up to AVX2/FMA/F16C. Enabling those keeps good speed without illegal-instruction crashes.
ENV CMAKE_ARGS="-DGGML_NATIVE=OFF -DGGML_AVX=ON -DGGML_AVX2=ON -DGGML_FMA=ON -DGGML_F16C=ON -DGGML_AVX512=OFF"
RUN pip install --no-cache-dir "llama-cpp-python[server]==0.3.2"

# Bake the TinyLlama 1.1B Chat GGUF (Q4_K_M, ~669MB) into the image
RUN mkdir -p /models && \
    curl -fL -o /models/tinyllama.gguf \
    https://huggingface.co/TheBloke/TinyLlama-1.1B-Chat-v1.0-GGUF/resolve/main/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf

ENV MODEL=/models/tinyllama.gguf
ENV PORT=8000
EXPOSE 8000

# CPU-only OpenAI-compatible server. n_ctx kept small for speed on CPU.
CMD ["sh", "-c", "python -m llama_cpp.server --model ${MODEL} --host 0.0.0.0 --port ${PORT} --n_ctx 1024 --n_threads 4"]
