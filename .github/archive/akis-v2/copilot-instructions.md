# AKIS v2 - Lightweight Agent Framework

**A**gents (you) • **K**nowledge (context) • **I**nstructions (this file) • **S**kills (patterns)

---

## Every Task Flow

### Start
`Read project_knowledge.json` → Index entities, map available context

**Context Indexing:**
1. Read line 1 of `project_knowledge.json` (map) for domain overview
2. Identify relevant documentation paths in `docs/` based on task domain
3. Note applicable skills in `.github/skills/`
4. Query specific sections as needed **throughout the workflow**

**During Work (All Phases):**
Query `project_knowledge.json`, `docs/`, and skills as needed

### Todo Phases

| Phase | Title Format | When |
|-------|--------------|------|
| CONTEXT | `[CONTEXT] Load knowledge for X` | Always (start) |
| PLAN | `[PLAN] Design approach for X` | Complex tasks |
| IMPLEMENT | `[IMPLEMENT] Build X` | Main work |
| VERIFY | `[VERIFY] Test X` | Always |
| LEARN | `[LEARN] Update knowledge & skills` | Always (after approval) |
| COMPLETE | `[COMPLETE] Log & commit` | Always (end) |

### End (LEARN → COMPLETE)

**LEARN:**
1. Run `python .github/scripts/generate_codemap.py` + add entities to project_knowledge.json
2. Run `python .github/scripts/update_docs.py` → Apply doc updates automatically (lightweight)
3. Run `python .github/scripts/suggest_skill.py` → Analyze session and propose skills
4. **Show skill suggestions to user** → Wait for approval before writing
5. If approved: Create/update `.github/skills/{name}.md` with skill content
6. Pattern obsolete? → Delete skill file

**COMPLETE:**
1. Create `log/workflow/YYYY-MM-DD_HHMMSS_task.md` from template
2. **Session tracking**: Increment counter, check if maintenance due (every 10 sessions), prompt user
3. Commit all changes

---

## Knowledge System

**Format:** `project_knowledge.json` (JSONL)

**Line 1 - Map:** `{"type":"map","domains":{...},"quickNav":{...}}` - Read first for overview

**Types:**
```json
{"type":"entity","name":"Module.Component","entityType":"service","observations":["desc","upd:YYYY-MM-DD"]}
{"type":"relation","from":"A","to":"B","relationType":"USES|IMPLEMENTS|DEPENDS_ON"}
{"type":"codegraph","name":"file.ext","nodeType":"module","dependencies":["X"],"dependents":["Y"]}
```

**Workflow:**
- Read line 1 (map) → Get domain overview & quickNav
- **Query specific domains as needed throughout work** → Use map to locate entities
- Update before commit → Codemap + manual entities (map auto-updates)

---

## Skills

Reference from `.github/skills/` when task matches (query as needed during work):

| Task | Skill |
|------|-------|
| API endpoints, REST | `backend-api.md` |
| React components, UI | `frontend-react.md` |
| UI consistency, styling | `ui-consistency.md` |
| Build/runtime errors | `debugging.md` |
| Knowledge queries, updates | `knowledge.md` |
| Documentation | `documentation.md` |

---

## Workflow Logs

**Required:** Tasks >15 min  
**Location:** `log/workflow/YYYY-MM-DD_HHMMSS_task.md`  
**Template:** `.github/templates/workflow-log.md`  
**Purpose:** Historical record (search to understand past changes)

---

## Quick Workflows

**Simple (<5 min):**
```
CONTEXT → IMPLEMENT → VERIFY → Commit (no log)
```

**Feature (>15 min):**
```
CONTEXT → PLAN → IMPLEMENT → VERIFY
↓ (wait for user approval)
LEARN → COMPLETE
```

**Review Gate:** After VERIFY, show results and wait for user approval before LEARN/COMPLETE

---

## Standards

- Files <500 lines, functions <50 lines
- Type hints required (Python/TypeScript)
- Tests for new features
- Descriptive commit messages
- **Use templates** from `.github/templates/` for all new skills and documentation

---

## Templates

All new content follows standardized templates:

**Skills**: `.github/templates/skill.md`
- Format: When to Use → Checklist → Examples → Quick Reference → Related
- Keep terse (<200 lines)

**Documentation**:
- Features: `.github/templates/feature-doc.md`
- Guides: `.github/templates/guide-doc.md`
- Workflow logs: `.github/templates/workflow-log.md`

**See**: `.github/templates/README.md` for usage guidelines

---

## Folders

- `.project/` → Planning docs, blueprints, ADRs
- `log/workflow/` → Historical work record
- `.github/prompts/` → Specialized workflow prompts

---

## Cross-Session Analysis

**Purpose**: Analyze all workflow logs to standardize skills, organize docs, and improve framework

**Trigger**: Every 10 sessions (automatic in COMPLETE) or manual anytime

**Workflow**: `.github/prompts/akis-workflow-analyzer.md`

**Outputs**: Skill candidates, doc organization, instruction improvements, knowledge updates

---

*Context over Process. Knowledge over Ceremony.*
