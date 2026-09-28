FROM python:3.12-slim

WORKDIR /opt/deepanalyze

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc g++ pandoc curl \
    && rm -rf /var/lib/apt/lists/*

COPY third_party/deepanalyze /opt/deepanalyze

RUN python -m pip install --no-cache-dir \
    numpy pandas openpyxl scikit-learn seaborn matplotlib plotly statsmodels \
    requests websockets python-multipart uvicorn fastapi openai pypandoc

# The upstream API defaults to localhost because its documented quickstart runs
# vLLM and the API on one host. The BA Agent stack runs them as isolated
# services, so point the API at the model service without altering the submodule.
RUN sed -i 's#http://localhost:8000/v1#http://deepanalyze-model:8000/v1#g' API/config.py

WORKDIR /opt/deepanalyze/API

EXPOSE 8100 8200

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=5 \
    CMD curl -fsS http://127.0.0.1:8200/health || exit 1

CMD ["python", "start_server.py"]
