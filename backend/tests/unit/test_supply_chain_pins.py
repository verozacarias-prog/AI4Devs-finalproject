"""Cases 1 to 3 of issue #82, from the description of its pull request: what a build downloads
is fixed by its content, not by a name that can start pointing somewhere else."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

REPOSITORY = Path(__file__).resolve().parents[3]
DOCKERFILE = REPOSITORY / "Dockerfile"
COMPOSE = REPOSITORY / "docker-compose.yml"
E2E_COMPOSE = REPOSITORY / "frontend" / "e2e" / "compose.e2e.yml"
PIPELINE = REPOSITORY / ".github" / "workflows" / "app-quality.yml"

BASE_IMAGE = re.compile(r"^\s*FROM\s+(\S+)", re.MULTILINE)
SERVICE_IMAGE = re.compile(r"^\s*image:\s*(\S+)", re.MULTILINE)
PINNED = re.compile(r"@sha256:[0-9a-f]{64}$")
PIP_INSTALL = re.compile(r"pip install[^\n]*")


def _images(path: Path, pattern: re.Pattern[str]) -> list[str]:
    return pattern.findall(path.read_text())


def _pgvector_image(path: Path) -> str:
    images = [image for image in _images(path, SERVICE_IMAGE) if image.startswith("pgvector/")]
    assert len(images) == 1, f"expected one pgvector image in {path.name}, found {images}"
    return images[0]


@pytest.mark.parametrize(
    ("path", "pattern"),
    [
        (DOCKERFILE, BASE_IMAGE),
        (COMPOSE, SERVICE_IMAGE),
        (E2E_COMPOSE, SERVICE_IMAGE),
        (PIPELINE, SERVICE_IMAGE),
    ],
    ids=["Dockerfile", "docker-compose", "compose-e2e", "app-quality"],
)
def test_every_image_is_pinned_by_digest(path: Path, pattern: re.Pattern[str]) -> None:
    """Case 1."""
    images = _images(path, pattern)

    # Without this, a pattern that stops matching would pass without checking anything.
    assert images, f"found no image in {path.name}"
    assert [image for image in images if not PINNED.search(image)] == []


def test_the_pipeline_tests_against_the_database_image_of_compose() -> None:
    """Case 2. Dependabot may update only one of the two copies, and they must not drift."""
    assert _pgvector_image(PIPELINE) == _pgvector_image(COMPOSE)


def test_the_image_installs_its_dependencies_checking_their_hashes() -> None:
    """Case 3."""
    installs = PIP_INSTALL.findall(DOCKERFILE.read_text())

    assert installs, "found no pip install in the Dockerfile"
    assert [line for line in installs if "--require-hashes" not in line] == []
