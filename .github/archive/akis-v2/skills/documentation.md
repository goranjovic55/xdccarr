# Documentation

## When to Use
- Creating workflow logs
- Writing README files
- Documenting APIs
- After completing features

## Avoid
- ❌ Stale documentation → ✅ Update with code changes
- ❌ No examples → ✅ Include code samples
- ❌ Verbose explanations → ✅ Keep concise

## Overview

Keep documentation clear, current, and close to code. Workflow logs for history, READMEs for usage, inline for complexity.

**Document Placement:** Always integrate new documentation intelligently into existing structure - never create random files in random places. Follow standardized naming and directory conventions.

**Use Templates:** All new docs and skills follow standardized templates from `.github/templates/`:
- Skills: `skill.md`
- Features: `feature-doc.md`
- Guides: `guide-doc.md`
- Workflow logs: `workflow-log.md`

---

## Documentation Directory Structure

**Standard Structure** (adapt to project needs):

```
docs/
├── INDEX.md              # Master index (always update when adding docs)
├── guides/               # User-facing guides and deployment
│   ├── QUICK_START.md
│   ├── DEPLOYMENT.md
│   └── CONFIGURATION.md
├── features/             # Feature-specific documentation
│   ├── FEATURE_NAME.md
│   └── IMPLEMENTED_FEATURES.md
├── technical/            # API references and technical specs
│   └── API_reference.md
├── architecture/         # System design and ADRs
│   └── ARCH_system.md
├── design/               # UI/UX specifications (if applicable)
│   └── UI_UX_SPEC.md
├── development/          # Contributing, testing, roadmap
│   ├── CONTRIBUTING.md
│   ├── TESTING.md
│   └── ROADMAP.md
├── analysis/             # Current project analysis
└── archive/              # Historical documentation
    └── category-YYYY-MM-DD/
```

**Variations by Project Type:**
- **Backend API**: Focus on `technical/` (API docs) and `guides/` (deployment)
- **Frontend App**: Add `design/` for UI components and patterns
- **Library/SDK**: Focus on `technical/` (API reference) and examples
- **CLI Tool**: Focus on `guides/` (usage) and examples
- **Full-Stack**: Use complete structure

---

## File Naming Convention

**Standardized Format:**
- Primary docs: `CATEGORY_NAME.md` (e.g., `DEPLOYMENT.md`, `AGENTS_C2.md`)
- Features: `FEATURE_NAME.md` (e.g., `STORM_FEATURE.md`)
- Guides: `GUIDE_PURPOSE.md` (e.g., `QUICK_START.md`)
- Specs: `SPEC_CATEGORY.md` (e.g., `UI_UX_SPEC.md`)

**Use uppercase with underscores** for all documentation files to maintain consistency.

---

## Intelligent Document Placement

### When Creating New Documentation

1. **Check existing structure first:**
   ```bash
   # Review current docs
   ls docs/*/
   # Check INDEX.md for coverage
   cat docs/INDEX.md
   ```

2. **Determine correct category:**
   - User guides, deployment → `docs/guides/`
   - Feature documentation → `docs/features/`
   - API references, specs → `docs/technical/`
   - System design, ADRs → `docs/architecture/`
   - UI/UX, design systems → `docs/design/`
   - Contributing, testing → `docs/development/`
   - Temporary analysis → `docs/analysis/`

3. **Check for existing related docs:**
   - Can content be **merged** into existing doc?
   - Is there overlap with another document?
   - Should old versions be archived first?

4. **Use standardized naming:**
   - Follow existing patterns
   - Uppercase with underscores
   - Descriptive, concise names

5. **Update INDEX.md immediately:**
   - Add entry in appropriate section
   - Include description and audience
   - Link to related documents
   - Update last modified date

### When Updating Existing Documentation

1. **Archive old versions if major rewrite:**
   ```bash
   mkdir -p docs/archive/category-YYYY-MM-DD/
   mv docs/OLD_DOC.md docs/archive/category-YYYY-MM-DD/
   ```

2. **Consolidate duplicates:**
   - Identify scattered documentation on same topic
   - Merge into single source of truth
   - Archive old versions
   - Update cross-references

3. **Update INDEX.md:**
   - Note consolidation
   - Update links
   - Add changelog entry

### Consolidation Guidelines

**When to consolidate:**
- Multiple docs cover same topic
- Documentation scattered across directories
- Old versions exist alongside new versions
- Similar content in different locations

**How to consolidate:**
1. Identify authoritative/newest version
2. Archive older/duplicate versions to `docs/archive/category-YYYY-MM-DD/`
3. Merge unique content from old docs into primary doc
4. Update INDEX.md with consolidated structure
5. Add cross-references to archived versions
6. Update any external links

**Example consolidation:**
```bash
# Before: Multiple docs scattered across root
FEATURE_PAGE_DOCUMENTATION.md
FEATURE_SCREENSHOTS.md
FEATURE_IMPLEMENTATION.md
FEATURE_ADVANCED_OPTIONS.md

# After: Single comprehensive doc
docs/features/FEATURE_NAME.md        # Consolidated primary doc
docs/archive/feature-docs-YYYY-MM-DD/ # Historical versions
```

---

## Workflow Logs

**When:** Tasks >15 min or significant changes

**Location:** `log/workflow/YYYY-MM-DD_HHMMSS_task.md`

**Template:** `.github/templates/workflow-log.md`

**Create during COMPLETE phase:**
```bash
# Copy template and rename
cp .github/templates/workflow-log.md log/workflow/$(date +%Y-%m-%d_%H%M%S)_task-name.md
```

**Include:**
- Task objective
- Approach/decisions
- Changes made
- Verification steps
- Lessons learned

**Example:**
```markdown
# Task: Add CVE Scanner Integration

## Context
Need real CVE data from NVD API instead of mock data.

## Approach
- Integrate NVD API 2.0
- Add version detection
- Cache CVE results

## Changes
- backend/app/services/cve_scanner.py
- Added CVE caching (24h TTL)
- Version string normalization

## Verification
- [x] Unit tests pass
- [x] Integration test with real API
- [x] Version detection accurate

## Lessons
- NVD API rate limit: 5 req/sec
- Version normalization critical for matching
```

---

## README Files

**Purpose:** Quick start, setup, usage

**Structure:**
```markdown
# Project/Component Name

Brief description (1-2 sentences)

## Setup
Installation/build steps

## Usage
Basic examples

## Configuration
Environment variables, options

## Development
How to contribute, run tests
```

**Keep current:**
- Update when features change
- Add new endpoints/components
- Document breaking changes
- Include examples

---

## Inline Documentation

**When to use:**
- Complex algorithms
- Non-obvious business logic
- Workarounds/hacks
- Integration points

**Keep concise:**
```python
# ✅ Good
def normalize_version(version: str) -> str:
    """Normalize version string for CVE matching.
    
    Handles: 1.2.3, v1.2.3, 1.2.3-beta
    Returns: 1.2.3
    """
    ...

# ❌ Too verbose
def normalize_version(version: str) -> str:
    """
    This function takes a version string and normalizes it.
    It can handle many different formats including...
    First we check if it starts with v...
    Then we split on dash...
    """
    ...
```

**TypeScript/JavaScript:**
```typescript
/**
 * Fetch CVE data with automatic retry
 * @param cveId - CVE identifier (e.g., "CVE-2024-1234")
 * @returns CVE details or null if not found
 */
async function fetchCVE(cveId: string): Promise<CVEData | null> {
  ...
}
```

---

## API Documentation

**FastAPI (automatic):**
```python
@router.post("/scan", response_model=ScanResult)
async def create_scan(
    scan: ScanCreate,
    db: Session = Depends(get_db)
) -> ScanResult:
    """
    Create new vulnerability scan.
    
    - **target**: IP or hostname
    - **scan_type**: quick, full, custom
    - Returns scan ID and status
    """
    ...
```

**Access:** `http://localhost:8000/docs`

**Keep updated:**
- Response models accurate
- Example values realistic
- Error codes documented

---

## Architecture Docs

**Location:** `docs/architecture/`

**When to create:**
- Major design decisions
- System architecture changes
- Integration patterns
- Data models

**Format (ADR - Architecture Decision Record):**
```markdown
# ADR-001: Use NVD API 2.0

## Status
Accepted

## Context
Need real CVE data. Options: NVD API 1.0, 2.0, or scraping.

## Decision
Use NVD API 2.0 with caching.

## Consequences
- Rate limited (5 req/sec)
- Need caching layer
- Better data quality
- Official source
```

---

## Feature Documentation

**Location:** `docs/features/`

**Template:** `.github/templates/feature-doc.md`

**Include:**
- Feature description
- User flow
- Screenshots (if UI)
- Configuration
- Limitations

**Generic Template:**
```markdown
# [Feature Name]

[Brief description of what it does]

## Usage
[Step-by-step instructions or code examples]

## Configuration
[Environment variables, settings, options]

## Limitations
[Known limitations or constraints]

## Related
[Links to related features or documentation]
```

---

## Session-Driven Documentation Updates

**When:** During LEARN phase at end of session

**How:** Run `python .github/scripts/update_docs.py`

**Process:**
1. Script analyzes session changes (commits, files, workflow log)
2. Suggests documentation updates based on impact
3. Agent reviews suggestions and applies approved updates
4. Updates are lightweight and focused

**Principles:**
- **Minimal updates only** - only update sections directly affected
- **No bloat** - keep changes concise and targeted
- **Avoid duplication** - check existing docs before adding
- **Update dates** - add date when making significant updates
- **Preserve structure** - don't reorganize, just update content

**Example workflow:**
```bash
# During LEARN phase
python .github/scripts/update_docs.py

# Review output (JSON with suggestions)
# Apply approved updates to affected docs
# Note updates in workflow log
```

**What to update:**
- API docs when endpoints change
- UI/UX docs when components change
- Deployment docs when infrastructure changes
- Feature lists when adding features
- README when user-facing changes occur

**What NOT to update:**
- Docs unrelated to session changes
- Docs that are still accurate
- Minor implementation details
- Internal refactoring details

---

## Cross-Session Workflow Analysis

**When:** 
- **Automatically**: Every 10 sessions (prompted in COMPLETE phase)
- **Manually**: User can trigger anytime

**Purpose:** **Maintenance task** - Analyze ALL sessions independently to identify patterns and improve AKIS framework

**Session Tracking:** Uses `.github/scripts/session_tracker.py` to track session numbers and automatically prompt for maintenance

**Important:** This is **NOT part of the regular session LEARN phase**. This is a separate maintenance workflow that runs after session completion when maintenance is due.

**How:** Use the AKIS Workflow Analyzer as a standalone maintenance task

**Process:**
1. **Check if maintenance is due** (automatic in COMPLETE phase):
   ```bash
   python .github/scripts/session_tracker.py check-maintenance
   ```

2. **Run analyzer script**:
   ```bash
   python .github/scripts/analyze_workflows.py --output markdown
   ```

3. Review analysis output:
   - Skill candidates (recurring patterns across sessions)
   - Documentation needs (frequently updated areas)
   - Instruction improvements (common decisions)
   - Knowledge updates (cross-session entities)

4. Follow prompt: `.github/prompts/akis-workflow-analyzer.md`

5. Implement approved improvements:
   - Create/update skills based on patterns
   - Organize and update documentation
   - Enhance framework instructions
   - Update knowledge base

6. **Mark maintenance as complete**:
   ```bash
   python .github/scripts/session_tracker.py mark-maintenance-done
   ```

**Workflow phases:**
```
CONTEXT → ANALYZE → REVIEW → IMPLEMENT → VERIFY → DOCUMENT → COMPLETE
```

**Difference from single-session LEARN phase:**
- **Single session (baked into LEARN)**: Analyzes current session only, updates knowledge/skills for that session
- **Multi-session maintenance (this workflow)**: Analyzes sessions since last maintenance (typically 10), standardizes patterns, cleans documentation, adjusts instructions

**What it provides:**
- Pattern analysis across all sessions
- Skill creation suggestions (frequency-based)
- Documentation organization recommendations
- Instruction standardization proposals
- Knowledge base improvements

**Example output:**
```
Pattern Analysis:
- frontend-ui: 12 sessions
- api-endpoints: 8 sessions
- docker-deployment: 5 sessions

Skill Candidates:
- ui-consistency.md (12 sessions, high priority)
- api-debugging.md (8 sessions, high priority)

Documentation Needs:
- API Reference (high priority)
- Component Library Guide (medium priority)
```

**Use cases:**
- Standardizing skills across project
- Organizing scattered documentation
- Codifying frequently-made decisions
- Tracking frequently-modified areas
- Framework continuous improvement

---

## Best Practices

**Do:**
- Update docs with code changes
- Use examples
- Keep concise
- Link related docs
- Date significant updates

**Don't:**
- Duplicate information
- Write obvious comments
- Let docs go stale
- Over-document simple code
- Skip workflow logs for complex tasks

---

## Checklist

Before commit:
- [ ] Workflow log created (if >15 min task)
- [ ] README updated (if user-facing change)
- [ ] API docs current (if endpoint changed)
- [ ] Inline docs for complex logic
- [ ] Architecture docs (if design decision)

Documentation review:
- [ ] Clear and concise
- [ ] Examples provided
- [ ] Up to date
- [ ] No duplicates
- [ ] Properly linked

## Related Skills
- `knowledge.md` - Project knowledge management
- `git-workflow.md` - Commit documentation

## Related Prompts
- `.github/prompts/akis-workflow-analyzer.md` - Cross-session analysis and framework improvement
