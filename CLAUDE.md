# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

`lazyscribe` is a lightweight Python library for ML experiment logging. It stores experiments in a single JSON file per project, only writing on successful completion (errors don't produce partial entries). Core abstractions: `Project`, `Experiment`, `Repository`, `Artifact`.

## Development Environment

Uses `uv` for package management and virtual environments.

```bash
uv sync --locked --all-extras --dev   # install all deps including dev/test/docs/qa
```

## Common Commands

```bash
# Linting and formatting
uv run ruff check .
uv run ruff format .

# Type checking
uv run mypy lazyscribe

# Tests (all)
uv run pytest tests --cov=./ --cov-report=xml

# Single test
uv run pytest tests/test_experiment.py::test_function_name -v

# Docs
make docs
```

## Pre-Commit Hooks

```bash
pre-commit install --install-hooks   # set up hooks
pre-commit run --all-files           # run manually
```

Hooks run on every commit: ruff (--fix), ruff-format, mypy, uv pip-compile, uv-lock, pyproject-fmt, trailing-whitespace, debug-statements, end-of-file-fixer. Commit-msg stage: conventional-pre-commit (allowed types: feat, fix, test, refactor, perf, docs, style, build, ci, revert, chore, upgrade, review, bump).

## Code Style

- **Linter/formatter**: ruff (configured in `pyproject.toml`)
- **Type checking**: mypy in strict mode (`strict = true`, `warn_return_any = true`)
- **Docstrings**: numpy convention
- **No relative imports**: all imports must be absolute (`TID252` rule enforced)
- **Type annotations required** on all code (ANN rules), except in `tests/`

## Architecture

### Core Data Flow

`Project` manages a list of `Experiment` objects and writes them to a single JSON file. Experiments are created via `Project.log(name)` context manager — the experiment is only appended to the project when the context exits cleanly. `Project.save()` writes both the JSON manifest and any pending artifact files.

### Dirty Flag Pattern

Both `Experiment` and `Artifact` use a `dirty: bool` field. New objects start dirty; loading from JSON sets dirty=False. `Project.save()` and `Repository.save()` only write objects where `dirty=True`, then reset the flag.

### Read-Only vs Mutable

`Project` modes: `r` (read-only), `a` (append new experiments, existing are read-only), `w` (write, no loading), `w+` (editable). Existing experiments loaded in `r`/`a` mode become `ReadOnlyExperiment` (an `attrs` `@frozen` subclass). Same pattern for `ReadOnlyTest`.

### Artifact Plugin System

Artifact handlers extend `lazyscribe.artifacts.base.Artifact` (an `attrs` `@define` class). They are discovered via entry points (`lazyscribe.artifact_type` group) or as direct `Artifact` subclasses. Built-in handlers: `json`, `pickle`. Each handler must implement `construct()`, `read()`, and `write()` class methods. Class-level attributes define `alias`, `suffix`, `binary`, and `output_only`.

### Repository

`Repository` holds versioned artifacts (not experiments). Multiple versions of the same artifact can coexist. Loading uses `asof` or `exact` version matching; artifacts can have expiry datetimes. `Experiment.promote_artifact()` moves an artifact from an ephemeral experiment to the versioned repository.

### Project Merging

`Project.merge()` uses a linked list merge algorithm (sorted by experiment timestamps) to combine two projects, then de-duplicates by slug, keeping the most recent version.

### Dependency Tracking

Experiments can declare upstream experiment dependencies stored as `{short_slug: Experiment}` dict. Serialized as `"project_path|experiment_slug"` strings in JSON. The module-level `registry` singleton (`lazyscribe.registry.registry`) maps project names to `Project` objects to resolve cross-project dependencies without re-loading.

### fsspec Integration

All file I/O uses `fsspec`, so both `Project` and `Repository` support any fsspec-compatible filesystem (local, S3, GCS, etc.) via `storage_options` kwargs and URL-based `fpath`.

## Git Workflow

- **Branches**: `main` (stable releases) and feature branches.
- Version managed via `uv` (`version_provider = "uv"` in `[tool.commitizen]`)

## Dependency Management

- `requirements.txt` and `dev-requirements.txt` are used for pinned/locked dependencies (referenced by edgetest and docs CI)
- Core deps: `attrs`, `fsspec`, `python-slugify` (plus `tomli` for Python 3.10)
- Optional extras: `tests`, `qa`, `docs`, `build`, `dev` (all of the above)
