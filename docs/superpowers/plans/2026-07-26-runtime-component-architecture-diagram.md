# Runtime Component Architecture Diagram Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an editable and rendered architecture diagram showing the approved runtime components around API Gateway, AI Gateway, and AI Guardrail Service.

**Architecture:** Use a left-to-right primary flow from Client through API Gateway and AI Gateway to Model Provider. Add a branch from AI Gateway to AI Guardrail Service, which fans out to Regex Detector, NER Model, and Qwen Model.

**Tech Stack:** draw.io `mxGraphModel` XML, draw.io Desktop CLI, PNG, Markdown.

## Global Constraints

- Show component names only.
- Include exactly: Client, API Gateway, AI Gateway, AI Guardrail Service, Regex Detector, NER Model, Qwen Model, and Model Provider.
- Exclude GKE, Kubernetes, Cloud Build, Artifact Registry, networking, functions, endpoints, and parameters.
- Keep the primary flow readable from left to right.
- Do not let connectors cross unrelated components.

---

### Task 1: Add the Runtime Component Architecture Diagram

**Files:**
- Create: `docs/architecture/runtime-component-architecture.drawio`
- Create: `docs/architecture/runtime-component-architecture.drawio.png`
- Modify: `README.md`

**Interfaces:**
- Consumes: `docs/superpowers/specs/2026-07-26-runtime-component-architecture-diagram-design.md`
- Produces: an editable draw.io source, an embedded-diagram PNG preview, and a README reference.

- [ ] **Step 1: Create the draw.io source**

Create a single-page `mxGraphModel` with:

- a title, `Runtime Component Architecture`;
- rounded component boxes using consistent typography;
- primary-row positions for Client, API Gateway, AI Gateway, and Model Provider;
- a lower branch for AI Guardrail Service;
- a final lower row for Regex Detector, NER Model, and Qwen Model;
- orthogonal arrows for every approved relationship;
- no edge labels, function names, parameters, or infrastructure components.

- [ ] **Step 2: Validate the XML**

Run:

```powershell
[xml](Get-Content -Raw docs/architecture/runtime-component-architecture.drawio) | Out-Null
```

Expected: exit code `0` with no output.

- [ ] **Step 3: Export the PNG**

Locate draw.io Desktop and run:

```powershell
& 'C:\Program Files\draw.io\draw.io.exe' `
  -x -f png -e -b 16 `
  -o docs/architecture/runtime-component-architecture.drawio.png `
  docs/architecture/runtime-component-architecture.drawio
```

Expected: exit code `0` and a non-empty PNG with embedded diagram XML.

- [ ] **Step 4: Inspect the rendered diagram**

Open the PNG and confirm:

- all eight component names are visible;
- the primary flow reads left to right;
- the guardrail branch is visually separate;
- no text is clipped;
- no connector crosses an unrelated component.

- [ ] **Step 5: Add the README reference**

Replace the existing text-only diagrams in the `Architecture` section with:

```markdown
## Architecture

![Runtime component architecture](docs/architecture/runtime-component-architecture.drawio.png)

The editable source is available at
[docs/architecture/runtime-component-architecture.drawio](docs/architecture/runtime-component-architecture.drawio).
```

- [ ] **Step 6: Verify scope and repository state**

Run:

```powershell
git diff --check
git status --short
```

Expected: only the draw.io source, PNG preview, README, and this plan are changed or newly tracked.

- [ ] **Step 7: Commit**

Run:

```powershell
git add README.md docs/architecture/runtime-component-architecture.drawio docs/architecture/runtime-component-architecture.drawio.png docs/superpowers/plans/2026-07-26-runtime-component-architecture-diagram.md
git commit -m "docs: add runtime component architecture diagram"
```

Expected: one documentation commit containing no runtime code changes.
