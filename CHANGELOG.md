# Changelog

## v0.9.5-rc.2 - Local Installation Acceptance

- Advanced the RC version line to `0.9.5-rc.2`.
- Added installed-app local acceptance covering install, first start, real model checks, SolidWorks checks, real workflows, stability, error scenarios, diagnostics, uninstall, reinstall, and final EXE delivery package generation.
- Added redacted rc.2 evidence packaging for local installation acceptance.
- No AI Capability, Recipe, SolidWorks module, low-level API navigation, Workbench architecture, or verified geometry path was added or expanded.

## v0.9.5-rc.1 - Release Candidate Freeze

- Unified release version metadata across root package, desktop package, and backend API.
- Rebuilt backend and desktop packaged artifacts for the RC line.
- Added installer first-start validation from a fresh user-data directory.
- Added redacted RC evidence package generation with SHA256 hashes for release artifacts.
- Updated release documentation to distinguish real validation evidence from mock-only development tests.
- No AI Capability, Recipe, SolidWorks module, Workbench architecture, or geometry path was added or expanded.

## v0.9.4 - End-to-End Usable App

- Rebuilt packaged EXE artifacts and validated the installed application from startup through real model configuration, SolidWorks preflight, approval-gated execution, visual review, and task history.
- Added separate text and vision model configuration for OpenAI-compatible providers.
- Added real vision-model connection testing and screenshot/CAD-preview visual validation through `doubao-seed-2.0-pro`.
- Added `scripts/v094_e2e_usable_app_validation.mjs` for reproducible packaged evidence.
- Preserved the Workbench information architecture and did not add new AI capabilities or SolidWorks low-level entry points.

## v0.9.3 - Geometry Parity

- Restored `mounting_plate` four-corner through-hole geometry parity.
- Verified real SolidWorks execution with `hole_features_restored=true` and `geometry_parity_verified=true`.
- Added long-stability validation evidence for 20 consecutive real `mounting_plate` runs.

## v0.9.1 - Stabilization and Release Hardening

- Cleaned release hygiene rules for generated directories and local environments.
- Added release notes, validation summary, and release checklist documentation.
- Fixed the npm audit high finding by pinning Electron to `42.5.0`.
- Added a custom Electron Builder icon path to avoid the default Electron icon.
- Added clean-clone verification, generated-file cleanup, SolidWorks mounting-plate long-stability, and error-scenario validation scripts.
- Added release hardening tests for documentation, recipe matrix coverage, cleanup policy, icon configuration, and Electron pinning.

## v0.9.0 - AI Capability Workbench

- Completed the AI Capability Workbench validation target with 27 capabilities, 14 recipes, and 16 MCP tools.
- Validated backend tests, frontend component tests, Playwright smoke, packaged EXE runtime, real LLM connection, visual checks, and real SolidWorks mounting-plate evidence.
