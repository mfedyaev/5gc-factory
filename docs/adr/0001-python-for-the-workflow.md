# 1. Python for the workflow

Status: Accepted

Date: 2026-09-25

## Context

The factory is a program that calls an LLM, pauses for a person, and traces the run. The control-plane network functions are a separate deployable.

## Decision

The workflow is Python. It uses existing libraries: LangGraph for the stage graph and Langfuse for the trace. Python is the usual language of that tooling.

[free5GC](https://github.com/free5gc/free5gc) is the role model for the control-plane network function. It decides the language and the database in the following records, not the workflow language.
