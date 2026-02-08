# NOP - Node Orchestration Platform

> AI-powered workflow automation platform with visual block-based editor

## MANDATORY: Execute START Phase Immediately

**STOP. Before doing ANYTHING else, execute these steps IN ORDER:**

1. **Load session skill**: `skill(name="session")`
2. **Load knowledge skill**: `skill(name="knowledge")`  
3. **Load knowledge graph**: `bash("head -100 project_knowledge.json")`
4. **Create TODO list** using AKIS format: `○ [agent:phase:skill] Task [context]`
5. **Announce**: `AKIS v7.4 [complexity]. Skills: [list]. Graph: [X entities]. [N] tasks. Ready.`

**DO NOT skip this. DO NOT answer the user's question first. Execute START phase FIRST.**

---

## Project Overview

NOP is a fullstack application for building and executing automated workflows using AI agents and integrations.

## Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | Python 3.11, FastAPI, async SQLAlchemy, PostgreSQL |
| Frontend | React 18, TypeScript, Zustand, React Flow |
| Infrastructure | Docker, Docker Compose |
| Testing | pytest (backend), Jest (frontend) |

## Quick Start

| Mode | Command |
|------|---------|
| Dev | `docker-compose -f docker/docker-compose.dev.yml up -d` |
| Prod | `docker-compose up -d` |
| Backend test | `cd backend && python -m pytest` |
| Frontend test | `cd frontend && npm test` |

## Project Structure

```
backend/           # FastAPI backend
  app/
    api/v1/       # REST endpoints
    models/       # SQLAlchemy models
    services/     # Business logic
    schemas/      # Pydantic schemas
frontend/          # React frontend
  src/
    components/   # React components
    pages/        # Page components
    store/        # Zustand stores
    hooks/        # Custom hooks
docker/            # Docker configurations
docs/              # Documentation
log/workflow/      # Session workflow logs
.opencode/         # OpenCode configuration
  agents/         # Custom agents (@akis, @code, @architect, etc.)
  skills/         # Skill definitions
  commands/       # Custom commands (/debug, /review, etc.)
```

## AKIS Workflow System (v7.4)

This project uses AKIS (Agent Knowledge & Instruction System) for structured development.

### 8 Quality Gates

| Gate | Check | Violation Cost |
|------|-------|----------------|
| G0 | Load project_knowledge.json at START | +13k tokens |
| G1 | Use todo tracking | Lost tracking |
| G2 | Load skill BEFORE editing | +5.2k tokens |
| G3 | Complete START phase | Lost context |
| G4 | Complete END phase with workflow log | Lost traceability |
| G5 | Verify syntax after EVERY edit | +8.5 min rework |
| G6 | Only ONE task in progress | Confusion |
| G7 | Use parallel agents for 6+ tasks | +14 min/session |

### G0: Knowledge in Memory

**Read first 100 lines of project_knowledge.json ONCE at START:**
```
Line 1:     HOT_CACHE (top 20 entities + paths)
Line 2:     DOMAIN_INDEX (81 backend, 74 frontend file paths)
Line 4:     GOTCHAS (43 known issues + solutions)
Lines 7-12: Layer entities
Lines 13-93: Layer relations
```

### Workflow Phases

1. **START**: Load knowledge → Read skills → Create TODO → Announce
2. **WORK**: Mark task → Load skill → Edit → Verify → Complete
3. **END**: Create log → Run scripts → Ask to push

## Agents

| Agent | Use For | Triggers |
|-------|---------|----------|
| @akis | Workflow orchestration (primary) | session start, workflow |
| @code | Implementation tasks | implement, create, write |
| @architect | Design and blueprints | design, architecture, plan |
| @debugger | Bug fixes and tracing | error, bug, traceback |
| @reviewer | Security and quality audits | review, audit, security |
| @documentation | Doc updates | docs, readme, explain |
| @research | Best practices research | research, compare |
| @devops | Docker and infrastructure | deploy, docker, ci/cd |

### Delegation Rules

| Criteria | Action |
|----------|--------|
| 3+ files | MANDATORY delegation |
| 6+ tasks | Use parallel agent pairs |
| Different domains | Split by frontend/backend |

## Skills

| Skill | Domain | Load When |
|-------|--------|-----------|
| backend-api | Python, FastAPI, SQLAlchemy | Editing .py in backend/ |
| frontend-react | React, TypeScript, Zustand | Editing .tsx, .jsx |
| debugging | Error tracing, gotchas | Errors, tracebacks |
| docker | Containers, deployment | Dockerfile, docker-compose |
| testing | pytest, Jest | Test files |
| security | OWASP, auth patterns | Security review |
| knowledge | Project knowledge queries | Architecture questions |
| session | Workflow management | Session start/end |

## Critical Gotchas

| Category | Pattern | Solution |
|----------|---------|----------|
| JSONB | Nested object won't save | Use `flag_modified(obj, 'field')` |
| API | 307 redirect on POST | Add trailing slash to URL |
| Auth | 401 on valid token | Check `nop-auth` key, not `auth_token` |
| State | React state stale in async | Capture state before async call |
| JSX | Comment syntax error | Use `{/* */}` not `//` |
| Docker | Old code in container | Use `--build --force-recreate` |

## Commands

| Command | Description |
|---------|-------------|
| `/load-knowledge` | Load project knowledge graph |
| `/health-check` | Run tests and checks |
| `/debug` | Debug with gotcha lookup |
| `/review` | Security and quality review |
| `/start-session` | Start AKIS workflow |
| `/end-session` | End with proper cleanup |

## Configuration Files

| File | Purpose |
|------|---------|
| `.opencode/agents/` | Agent definitions |
| `.opencode/skills/` | Skill definitions |
| `.opencode/commands/` | Custom commands |
| `project_knowledge.json` | Knowledge graph |
| `.github/copilot-instructions.md` | Legacy GitHub Copilot config |

## Performance Metrics (100k Simulation)

| Metric | Without AKIS | With AKIS | Improvement |
|--------|--------------|-----------|-------------|
| API Calls | 37 | 16 | **-48%** |
| Tokens | 21k | 9k | **-55%** |
| Time | 53 min | 8 min | **-56%** |
| Success | 87% | 94% | **+7%** |
