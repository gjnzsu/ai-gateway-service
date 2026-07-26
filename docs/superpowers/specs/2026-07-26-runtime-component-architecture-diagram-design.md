# Runtime Component Architecture Diagram Design

## Purpose

Add one concise architecture diagram that shows the runtime relationship
between the platform gateways, the AI guardrail POC, and model runtimes.

## Scope

The diagram contains component names only:

- Client
- API Gateway
- AI Gateway
- AI Guardrail Service
- Regex Detector
- NER Model
- Qwen Model
- Model Provider

Infrastructure components such as GKE, Cloud Build, Artifact Registry,
Kubernetes resources, and networking are excluded.

## Layout

Use a left-to-right primary flow:

`Client → API Gateway → AI Gateway → Model Provider`

Branch from `AI Gateway` to `AI Guardrail Service`. Branch from
`AI Guardrail Service` to `Regex Detector`, `NER Model`, and `Qwen Model`.

The diagram does not show functions, endpoints, parameters, implementation
details, deployment details, or production enforcement behavior.

## Deliverables

- An editable draw.io source file under `docs/architecture/`.
- A rendered PNG preview under `docs/architecture/`.
- A short README architecture reference to the rendered diagram.

## Acceptance

- All eight approved runtime components are visible.
- The primary flow is readable from left to right.
- Arrows do not cross unrelated components.
- No infrastructure or function-level detail appears.
- The PNG is readable at documentation scale.
