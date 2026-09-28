FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN python -m pip install --no-cache-dir "polars>=1.30,<2" "numpy>=2,<3"

WORKDIR /workspace
USER 65534:65534
ENTRYPOINT ["python", "/workspace/runner.py"]
