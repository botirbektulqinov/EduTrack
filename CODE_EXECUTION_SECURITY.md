# Code Execution Preview Security

## Current State

EduTrack currently runs Python code preview through a local subprocess in `GradingService`. The implementation enforces a short timeout and returns structured errors for invalid code, but it is not a hardened sandbox.

Current tests cover:

- Timeout returns a safe error.
- Invalid code returns a structured failure.

## Production Risks

- Code runs on the application host.
- No network isolation is enforced.
- No per-execution container boundary exists.
- No strict memory, process, filesystem, or syscall policy is enforced.
- Output size is not capped at the platform boundary.
- Malicious code could consume local resources until timeout.

## Required Production Sandbox

A production-ready implementation should execute every preview in an isolated worker/container with Docker or microVM isolation, network disabled, CPU and memory limits, wall-clock timeout, read-only filesystem, no host mounts, non-root user, process count limit, output size cap, language allowlist, Redis/API rate limiting, audit logging, and a worker pool separate from the API process.

## Recommended Implementation Path

1. Introduce a `CodeExecutionService` interface.
2. Move the current subprocess runner behind a development-only `LocalPythonExecutionService`.
3. Add a production `ContainerExecutionService`.
4. Reject code preview in production unless the configured executor is sandboxed.
5. Add integration tests for timeout, output cap, language allowlist, and blocked network access.
