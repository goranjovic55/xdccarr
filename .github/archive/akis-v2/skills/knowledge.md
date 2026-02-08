# Knowledge

## When to Use
- Start of any task (CONTEXT phase)
- During work (query as needed)
- Before committing (LEARN phase)

## Avoid
- ❌ Loading everything upfront → ✅ Index map, query as needed
- ❌ Duplicate entities → ✅ Check existing first
- ❌ Stale observations → ✅ Update timestamps

## Overview

Maintain `project_knowledge.json` as institutional memory and `docs/` for detailed documentation. Index at start, query during work, update before commit.

**Line 1 = Domain map** for quick navigation to entities and documentation.

---

## CONTEXT Phase (Start of Task)

**1. Read line 1 (domain map):**
```bash
head -1 project_knowledge.json | python3 -m json.tool
```

**2. Index available context:**
- Check `domains` for knowledge line ranges
- Use `quickNav` for common task shortcuts
- Identify relevant documentation in `docs/` based on domain
- Note applicable skills in `.github/skills/`

**3. Query specific sections as needed throughout work** (don't load everything)

---

## Format (JSONL)

**Map (line 1):**
```json
{"type":"map","domains":{"Frontend":"Line 5+","Backend":"Line 50+"},"quickNav":{"Scans":"..."}}
```

**Entity:**
```json
{"type":"entity","name":"Module.Component","entityType":"service","observations":["desc","upd:YYYY-MM-DD"]}
```

**Relation:**
```json
{"type":"relation","from":"A","to":"B","relationType":"USES|IMPLEMENTS|DEPENDS_ON"}
```

**Codegraph:**
```json
{"type":"codegraph","name":"file.ext","nodeType":"module","dependencies":["X"],"dependents":["Y"]}
```

---

## Entity Types

- `service` - Backend service, API
- `component` - Frontend component
- `module` - Logical module
- `infrastructure` - Docker, networking
- `feature` - User-facing feature
- `tool` - Script, utility

---

## Relation Types

- `USES` - A calls/imports B
- `IMPLEMENTS` - A implements interface B
- `DEPENDS_ON` - A requires B to function
- `EXTENDS` - A extends B
- `CONTAINS` - A contains B

---

## During Work (All Phases)

**Query knowledge as needed:**
- Check `project_knowledge.json` for entity details
- Read relevant docs from `docs/` when encountering unknowns
- Reference skills for patterns

**Add entities manually:**
- New services, components, features
- Architecture decisions
- Integration points

**Example:**
```json
{"type":"entity","name":"CVEScanner","entityType":"service","observations":["NVD API integration","upd:2026-01-03"]}
{"type":"relation","from":"VulnScanService","to":"CVEScanner","relationType":"USES"}
```

---

## LEARN Phase (Before Commit)

**1. Generate codemap (auto-updates map):**
```bash
python .github/scripts/generate_codemap.py
```

**2. Apply documentation updates (automatic):**
```bash
python .github/scripts/update_docs.py
```

**3. Add manual entities:**
- New features
- Architectural changes
- Integration points

**4. Update observations:**
```json
{"type":"entity","name":"ExistingService","entityType":"service","observations":["original desc","enhanced X","upd:2026-01-03"]}
```

---

## Query Patterns

**Find entity:**
```bash
grep '"name":"ModuleName"' project_knowledge.json
```

**Find dependencies:**
```bash
grep '"from":"ModuleName"' project_knowledge.json
```

**Find dependents:**
```bash
grep '"to":"ModuleName"' project_knowledge.json
```

**Recent updates:**
```bash
grep 'upd:2026-01' project_knowledge.json
```
**CONTEXT phase**: Index map, identify relevant docs/skills
- **During work**: Query knowledge and docs as needed (not all upfront)
- **LEARN phase**: Update knowledge and documentation automatically
- Check for existing entities before creating
- Add observations with dates (upd:YYYY-MM-DD)
- Keep descriptions concise
- Use consistent naming (PascalCase for entities)

---

## Common Mistakes

❌ Loading everything at start → context overflow  
✅ Index map, query as needed

❌ Creating duplicate entities  
✅ Query project_knowledge.json first

❌ Missing update timestamps  
✅ Add `upd:YYYY-MM-DD` to observations

❌ Forgetting documentation updates  
✅ Run update_docs.py in LEARN phase

❌ Vague observations  
✅ Specific, dated observations

❌ Missing relations  
✅ Document integration points

## Related Skills
- `documentation.md` - Workflow logging, doc updates
- `debugging.md` - Troubleshooting
