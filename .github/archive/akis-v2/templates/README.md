# AKIS Framework Templates

Standardized templates for maintaining consistency across skills, documentation, and workflow logs.

## Template Usage

### Skills Template

**Location**: `skill.md`

**When to Use**: Creating or updating any skill in `.github/skills/`

**Format**:
- One-line description
- When to Use (4+ scenarios)
- Checklist (6+ items)
- Examples (3+ with code)
- Quick Reference table
- Related links

**Keep Terse**: Target <200 lines, focus on actionable patterns

---

### Feature Documentation Template

**Location**: `feature-doc.md`

**When to Use**: Documenting features in `docs/features/`

**Sections**:
- Overview with key features
- Quick Start (3 steps)
- Usage examples
- Configuration table
- API reference
- Troubleshooting
- Implementation details
- Related docs

---

### Guide Documentation Template

**Location**: `guide-doc.md`

**When to Use**: Creating guides in `docs/guides/`

**Sections**:
- Prerequisites
- Quick Start
- Step-by-step instructions
- Configuration
- Common tasks
- Troubleshooting
- Best practices
- Related resources

---

### Workflow Log Template

**Location**: `workflow-log.md`

**When to Use**: Tasks >15 min during COMPLETE phase

**Sections**:
- Summary
- Changes (created/modified/deleted)
- Decisions table
- Knowledge updates
- Documentation updates
- Skills used/created
- Verification checklist
- Technical details
- Notes

---

## Standardization Principles

1. **Terse and Effective**: Bullet points > paragraphs
2. **Actionable**: Focus on what to do, not theory
3. **Consistent Structure**: Same sections in same order
4. **Cross-Referenced**: Link to related docs/skills
5. **Dated**: Include last updated date
6. **Versioned**: Note document version and status

---

## Template Workflow

### Creating New Skill

1. Copy `skill.md` to `.github/skills/[name].md`
2. Fill in all sections
3. Keep examples minimal and focused
4. Add to instructions table if high-usage pattern
5. Commit with descriptive message

### Creating New Documentation

1. Determine type (feature/guide/technical)
2. Copy appropriate template to `docs/[category]/`
3. Fill in sections with actual content
4. Update `docs/INDEX.md` with new entry
5. Commit and note in workflow log

### Updating Existing Skill/Doc

1. Check if follows current template format
2. If not, reformat using template
3. Update content while maintaining structure
4. Update last modified date
5. Commit changes

---

## Related Files

- `.github/prompts/akis-workflow-analyzer.md` - Multi-session analysis
- `.github/copilot-instructions.md` - Framework instructions
- `.github/skills/documentation.md` - Documentation skill with placement rules
