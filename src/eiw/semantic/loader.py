"""Semantic package loader with v2 support.

Supports both legacy and v2 semantic package formats.
"""

from __future__ import annotations

from datetime import date
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from eiw.semantic.v2 import (
    SemanticPackageV2,
    MetricDefinition,
    DimensionDefinition,
    PackageIdentity,
)


def load_semantic_package_v2(path: Path) -> SemanticPackageV2:
    """Load a v2 semantic package from YAML.

    Args:
        path: Path to the semantic-package.yaml file

    Returns:
        Validated SemanticPackageV2

    Raises:
        ValidationError: If package validation fails
        FileNotFoundError: If file doesn't exist
    """
    raw = path.read_bytes()
    parsed = yaml.safe_load(raw)

    # Handle both v2 format (package key) and legacy format
    if "package" not in parsed:
        raise ValueError(f"Invalid semantic package: missing 'package' key in {path}")

    # Validate the package
    try:
        package = SemanticPackageV2.model_validate(parsed)
    except Exception as e:
        raise ValueError(f"Semantic package validation failed for {path}: {e}") from e

    # Add content hash
    package.content_hash = sha256(raw).hexdigest()

    return package


def load_any_semantic_package(path: Path) -> SemanticPackageV2:
    """Load any semantic package format.

    Args:
        path: Path to the semantic-package.yaml file

    Returns:
        SemanticPackageV2

    Raises:
        ValidationError: If package validation fails
    """
    return load_semantic_package_v2(path)


def get_package_domains(packages_dir: Path) -> list[str]:
    """Get list of available domain packages.

    Args:
        packages_dir: Root directory containing domain packages

    Returns:
        List of domain IDs
    """
    domains = []
    if packages_dir.exists():
        for subdir in packages_dir.iterdir():
            if subdir.is_dir() and (subdir / "semantic-package.yaml").exists():
                domains.append(subdir.name)
    return sorted(domains)


def load_domain_package(packages_dir: Path, domain_id: str) -> SemanticPackageV2:
    """Load a specific domain package.

    Args:
        packages_dir: Root directory containing domain packages
        domain_id: Domain identifier (e.g., "finance", "sales_operations")

    Returns:
        SemanticPackageV2 for the domain

    Raises:
        FileNotFoundError: If domain doesn't exist
        ValidationError: If package validation fails
    """
    package_path = packages_dir / domain_id / "semantic-package.yaml"
    if not package_path.exists():
        raise FileNotFoundError(
            f"Domain package not found: {domain_id} at {package_path}"
        )
    return load_semantic_package_v2(package_path)


# Legacy support
from eiw.semantic.package import (
    SemanticPackage as SemanticPackageV1,
    load_semantic_package as load_semantic_package_v1,
)

SemanticPackage = SemanticPackageV2  # Default to v2
load_semantic_package = load_semantic_package_v2  # Default to v2
