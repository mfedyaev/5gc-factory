# 2. Go for the network function

Status: Accepted

Date: 2026-09-25

## Context

Each network function is a small HTTP service on the control plane. A local model writes the source. That model runs at low quantization with a small context window, so the file has to stay short enough to fit in one completion.

## Decision

The role model is the [free5GC](https://github.com/free5gc/free5gc) control plane, which is Go. A network function here is one Go module. The source is a single `main` package: the listener starts in `main`, and path parameters are read with `PathValue`. One compact file is what that model can write.

## Consequences

None.
