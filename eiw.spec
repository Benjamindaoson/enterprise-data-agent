# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Enterprise Data Agent EXE packaging.

Build command:
    pyinstaller eiw.spec --clean
"""

import sys
import os
from pathlib import Path

# Project root - use cwd as fallback when __file__ is not available
_project_root = Path.cwd()
try:
    _project_root = Path(__file__).parent.resolve()
except (NameError, TypeError):
    pass
project_root = _project_root
src_dir = project_root / "src"

from PyInstaller.building.build_main import Analysis, PYZ, EXE, COLLECT
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None

# Explicitly collect ALL files from the eiw package so they're bundled
eiw_datas = collect_data_files("eiw", include_py_files=True)

# Collect hidden imports
hiddenimports = [
    # FastAPI and dependencies
    "uvicorn",
    "uvicorn.logging",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "starlette",
    "fastapi",
    "pydantic",
    "pydantic_settings",

    # Database
    "sqlalchemy",
    "psycopg",

    # LLM Providers
    "anthropic",
    "openai",

    # Observability
    "opentelemetry",
    "opentelemetry.sdk",
    "prometheus_client",

    # Core modules
    "eiw",
    "eiw.app",
    "eiw.agent",
    "eiw.agent.executor",
    "eiw.agent.executors",
    "eiw.agent.governance",
    "eiw.agent.intent",
    "eiw.agent.planner",
    "eiw.agent.provider",
    "eiw.agent.router",
    "eiw.agent.runtime",
    "eiw.agent.state",
    "eiw.agent.supervisor",
    "eiw.agent.tools",
    "eiw.agent.provider_wrapper",
    "eiw.billing",
    "eiw.billing.service",
    "eiw.evaluation",
    "eiw.hitl",
    "eiw.hitl.api",
    "eiw.hitl.models",
    "eiw.hitl.service",
    "eiw.observability",
    "eiw.observability.grafana",
    "eiw.observability.langfuse",
    "eiw.observability.logging",
    "eiw.observability.otel",
    "eiw.rate_limiter",
    "eiw.persistence",
    "eiw.nl2sql",
    "eiw.workspace",
    "eiw.workspace.analysis",
    "eiw.workspace.data",
    "eiw.workspace.store",
    "eiw.nl2sql.parser",
    "eiw.nl2sql.policy",
    "eiw.nl2sql.service",
    "eiw.nl2sql.repair",
]

# Datas: include static files and data
datas = list(eiw_datas)

# Add static web files
static_dir = src_dir / "eiw" / "web" / "static"
if static_dir.exists():
    datas.append((str(static_dir), "eiw/web/static"))

# Add evaluation cases
evaluation_dir = project_root / "evaluation"
if evaluation_dir.exists():
    datas.append((str(evaluation_dir), "evaluation"))

# Add sample data
sample_data_dir = project_root / "data"
if sample_data_dir.exists():
    datas.append((str(sample_data_dir), "data"))


a = Analysis(
    ["src/eiw/__main__.py"],
    pathex=[str(project_root), str(src_dir)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # GUI frameworks
        "tkinter",
        "matplotlib",
        # Unused data science packages (not needed for this app)
        "numpy",
        "pandas",
        "scipy",
        "IPython",
        "notebook",
        # Exclude heavy ML frameworks (not used by EIW)
        "torch",
        "torchvision",
        "torchaudio",
        "transformers",
        "datasets",
        "tensorflow",
        "onnxruntime",
        "sklearn",
        "numba",
        "llvmlite",
        # Exclude spacy language models
        "spacy",
        "thinc",
        # Problematic native modules that cause issues with PyInstaller
        "magic",
        "magic.magic",
        "unstructured_inference",
        "pypdfium2",
        "pypdfium2_raw",
        "pypdfium2_cfg",
        "pdfminer",
        "pymupdf",
        "fitz",
        "cv2",
        # Test frameworks
        "test",
        "pytest",
        # Template engines (not using Jinja2)
        "jinja2",
        # Exclude langchain modules not needed by EIW
        "langchain",
        "langchain_community",
        "langchain_classic",
        "langchain_openai",
        "langchain_milvus",
        "langchain_ollama",
        "langgraph",
        "langgraph_sdk",
        "langsmith",
        # Exclude other heavy dependencies not needed
        "chromadb",
        "qdrant_client",
        "pymilvus",
        "unstructured",
        "unstructured_client",
        "docx",
        "fontTools",
        "sympy",
        "networkx",
        "wandb",
        "yfinance",
        "git",
        "gitdb",
        "smmap",
        "plotly",
        "pdfplumber",
        "pypdf",
        "pikepdf",
        "pi_heif",
        "pdf2image",
        "installer",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="EnterpriseDataAgent",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="EnterpriseDataAgent",
)
