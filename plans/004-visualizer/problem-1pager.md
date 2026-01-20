# Problem 1-Pager: Visualizer Agent + JSON Schema

## Background
The demo pipeline ends with a Visualizer step, but today it is only a mock. We also need a stable JSON contract so the future GUI can render visual components reliably (CLI is not the rendering target).

## Problem
There is no real Visualizer agent and no concrete JSON schema for UI components. This blocks end-to-end validation of the final stage and makes front-end integration ambiguous.

## Goal
- Define a concrete JSON schema for the Visualizer output.
- Implement an OpenAI Agents SDK Visualizer that maps Writer output into that schema.
- Provide a standalone Visualizer CLI and tests with observable input/output payloads.

## Non-goals
- Building any actual UI/GUI renderer.
- json-render specific implementation or UI design work.
- Improving other agents beyond wiring Visualizer.

## Constraints
- Must keep compatibility with `VisualOutput`/`VisualComponent` in `main.py`.
- Use OpenAI Agents SDK (Python) for the Visualizer.
- Output must be JSON-first and ASCII-safe, with clear error reporting.
- Tests should be demo E2E + agent unit test, printing payloads by default.
