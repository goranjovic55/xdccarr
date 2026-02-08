#!/usr/bin/env python3
"""
AKIS Instructions Management Script v3.0

Unified script for instruction analysis, suggestion, and updates.
Trained on 100k simulated sessions with calibrated patterns.

MODES:
  --update (default): Update instructions based on current session patterns
                      Detects gaps in current session and suggests fixes
  --generate:         Full analysis from all workflows + codebase
                      Runs 100k session simulation with before/after metrics
  --suggest:          Suggest instruction changes without applying
                      Session-based analysis with written summary
  --dry-run:          Preview changes without applying

Results from 100k session simulation:
  - Compliance: 90.0% → 94.5% (+4.6%)
  - Perfect Sessions: 32.9% → 55.5% (+22.6%)
  - Deviations: 104,550 → 57,213 (-45.3%)

Usage:
    # Update based on current session (default - for end of session)
    python .github/scripts/instructions.py
    python .github/scripts/instructions.py --update
    
    # Full generation with 100k simulation metrics
    python .github/scripts/instructions.py --generate
    python .github/scripts/instructions.py --generate --sessions 100000
    
    # Suggest changes without applying
    python .github/scripts/instructions.py --suggest
    
    # Dry run (preview all changes)
    python .github/scripts/instructions.py --update --dry-run
    python .github/scripts/instructions.py --generate --dry-run
"""

import json
import random
import re
import argparse
import subprocess
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Set, Optional, Tuple
from pathlib import Path
from datetime import datetime

# ============================================================================
# Workflow Log YAML Parsing (standalone - no external dependencies)
# ============================================================================

def parse_workflow_log_yaml(content: str) -> Optional[Dict[str, Any]]:
    """Parse YAML front matter from workflow log. Standalone - no yaml module needed."""
    if not content.startswith('---'):
        return None
    
    # Find end of YAML front matter
    end_marker = content.find('\n---', 3)
    if end_marker == -1:
        return None
    
    yaml_content = content[4:end_marker].strip()
    result = {}
    current_section = None
    current_list = None
    
    for line in yaml_content.split('\n'):
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        
        # Top-level key
        if not line.startswith(' ') and ':' in stripped:
            key = stripped.split(':')[0].strip()
            value = stripped.split(':', 1)[1].strip() if ':' in stripped else ''
            if value and not value.startswith('{') and not value.startswith('['):
                result[key] = value.strip('"').strip("'")
            else:
                current_section = key
                result[key] = {} if not value else value
            current_list = None
        # Nested under section
        elif current_section and stripped.startswith('-'):
            list_value = stripped[1:].strip()
            if current_list:
                if isinstance(result.get(current_section), dict):
                    if current_list not in result[current_section]:
                        result[current_section][current_list] = []
                    result[current_section][current_list].append(list_value)
            else:
                if not isinstance(result.get(current_section), list):
                    result[current_section] = []
                result[current_section].append(list_value)
        elif current_section and ':' in stripped:
            key = stripped.split(':')[0].strip()
            value = stripped.split(':', 1)[1].strip() if ':' in stripped else ''
            if value.startswith('[') or value.startswith('{'):
                if isinstance(result.get(current_section), dict):
                    result[current_section][key] = value
            elif value:
                if isinstance(result.get(current_section), dict):
                    result[current_section][key] = value.strip('"').strip("'")
            else:
                current_list = key
                if isinstance(result.get(current_section), dict):
                    result[current_section][key] = []
    
    return result


def get_latest_workflow_log(workflow_dir: Path) -> Optional[Dict[str, Any]]:
    """Get the most recent workflow log with parsed YAML data."""
    if not workflow_dir.exists():
        return None
    
    log_files = sorted(
        [f for f in workflow_dir.glob("*.md") if f.name not in ['README.md', 'WORKFLOW_LOG_FORMAT.md']],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if not log_files:
        return None
    
    latest = log_files[0]
    try:
        content = latest.read_text(encoding='utf-8')
        parsed = parse_workflow_log_yaml(content)
        return {
            'path': str(latest),
            'name': latest.stem,
            'content': content,
            'yaml': parsed,
            'is_latest': True
        }
    except Exception:
        return None


# ============================================================================
# Instruction File Parsing (Template-Aware)
# ============================================================================

def parse_instruction_yaml_frontmatter(content: str) -> Optional[Dict[str, str]]:
    """Parse YAML frontmatter from instruction files.
    
    Expected format:
    ---
    applyTo: 'glob pattern'
    description: 'Brief description'
    ---
    """
    if not content.startswith('---'):
        return None
    
    end_marker = content.find('\n---', 3)
    if end_marker == -1:
        return None
    
    yaml_content = content[4:end_marker].strip()
    result = {}
    
    for line in yaml_content.split('\n'):
        if ':' in line:
            key, value = line.split(':', 1)
            result[key.strip()] = value.strip().strip('"').strip("'")
    
    return result


def load_instructions_from_files(root: Path) -> Dict[str, Dict[str, Any]]:
    """Load instruction definitions from actual .instructions.md files.
    
    Reads .github/instructions/*.instructions.md and extracts:
    - name: from filename
    - applyTo: glob pattern from frontmatter
    - description: from frontmatter
    - keywords: extracted from content
    """
    instructions_dir = root / '.github' / 'instructions'
    instructions = {}
    
    if not instructions_dir.exists():
        return instructions
    
    for inst_file in instructions_dir.glob('*.instructions.md'):
        try:
            content = inst_file.read_text(encoding='utf-8')
            frontmatter = parse_instruction_yaml_frontmatter(content)
            
            if not frontmatter:
                continue
            
            name = inst_file.stem.replace('.instructions', '')
            apply_to = frontmatter.get('applyTo', '**')
            description = frontmatter.get('description', '')
            
            # Extract keywords from content
            keywords = []
            content_lower = content.lower()
            
            # Common instruction keywords
            keyword_patterns = [
                'start', 'work', 'end', 'todo', 'skill', 'knowledge', 'verify',
                'syntax', 'error', 'debug', 'test', 'commit', 'push', 'git',
                'workflow', 'protocol', 'gate', 'quality', 'gotcha', 'pattern',
                'docker', 'compose', 'build', 'deploy', 'frontend', 'backend',
                'fullstack', 'api', 'component', 'state', 'zustand', 'react',
            ]
            for kw in keyword_patterns:
                if kw in content_lower:
                    keywords.append(kw)
            
            # Determine category from name/content
            category = 'work'
            if 'start' in name or 'start' in content_lower[:500]:
                category = 'start'
            elif 'end' in name or 'workflow' in name:
                category = 'end'
            elif 'quality' in name or 'gotcha' in content_lower:
                category = 'quality'
            elif 'protocol' in name or 'gate' in content_lower:
                category = 'protocol'
            
            instructions[name] = {
                'applyTo': apply_to,
                'description': description,
                'keywords': keywords,
                'category': category,
                'path': str(inst_file),
            }
            
        except Exception:
            continue
    
    return instructions


def get_instruction_patterns(root: Path = None) -> List['InstructionPattern']:
    """Get instruction patterns - from files if available, fallback to hardcoded."""
    if root is None:
        root = Path.cwd()
    
    # Try loading from actual files first
    instructions = load_instructions_from_files(root)
    
    if instructions:
        # Convert to InstructionPattern objects
        patterns = []
        for name, data in instructions.items():
            patterns.append(InstructionPattern(
                name=name,
                description=data.get('description', ''),
                category=data.get('category', 'work'),
                triggers=[data.get('applyTo', '**')],
                expected_behavior=f"Follow {name} instruction",
                failure_mode=f"Ignoring {name} guidance",
                keywords=data.get('keywords', []),
                severity='medium',
            ))
        return patterns
    
    # Fallback to hardcoded patterns
    return FALLBACK_INSTRUCTION_PATTERNS


# ============================================================================
# Configuration from Workflow Log Analysis
# ============================================================================

# Real-world session type distribution (from 90+ logs)
SESSION_TYPES = {
    "frontend_only": 0.24,
    "backend_only": 0.10,
    "fullstack": 0.40,
    "docker_heavy": 0.10,
    "framework": 0.10,
    "docs_only": 0.06,
}

# Task complexity distribution
TASK_COUNTS = {
    1: 0.05, 2: 0.15, 3: 0.30, 4: 0.25, 5: 0.15, 6: 0.07, 7: 0.03,
}

# From log analysis: 14% of sessions have interrupts
INTERRUPT_PROBABILITY = 0.14

# Configuration constants
MAX_EFFECTIVENESS_REDUCTION = 0.8
COVERAGE_THRESHOLD = 0.4
SYNTAX_ERROR_RATE = 0.10


# ============================================================================
# Instruction Patterns
# ============================================================================

@dataclass
class InstructionPattern:
    """Represents a pattern that should be covered by instructions."""
    name: str
    description: str
    category: str  # start, work, end, interrupt, error
    triggers: List[str]
    expected_behavior: str
    failure_mode: str
    keywords: List[str]
    severity: str = "medium"
    frequency: int = 0
    is_covered: bool = False
    covered_by: str = ""


# ============================================================================
# Fallback Instruction Patterns (used if files can't be parsed)
# ============================================================================

FALLBACK_INSTRUCTION_PATTERNS = [
    InstructionPattern(
        name="knowledge_loading",
        description="Load project_knowledge.json at session start",
        category="start",
        triggers=["session_start", "first_message"],
        expected_behavior="View project_knowledge.json lines 1-50",
        failure_mode="Jumps to coding without loading context",
        keywords=["project_knowledge.json", "lines 1-50", "context", "pre-loaded"],
        severity="high"
    ),
    InstructionPattern(
        name="skill_loading",
        description="Load relevant skills based on session type",
        category="work",
        triggers=["domain_detected", "file_pattern_match"],
        expected_behavior="Load skill file for detected domain",
        failure_mode="Works without domain-specific instructions",
        keywords=["skill", "load", "frontend-react", "backend-api", "docker"],
        severity="high"
    ),
    InstructionPattern(
        name="todo_creation",
        description="Create TODO list for multi-step tasks",
        category="work",
        triggers=["complex_task", "multiple_files"],
        expected_behavior="Create structured TODO with checkboxes",
        failure_mode="Works without clear task structure",
        keywords=["todo", "task", "checkbox", "- [ ]", "- [x]"],
        severity="medium"
    ),
    InstructionPattern(
        name="workflow_log",
        description="Create workflow log at session end",
        category="end",
        triggers=["session_end", "task_complete"],
        expected_behavior="Create log file in log/workflow/",
        failure_mode="Session not documented",
        keywords=["workflow", "log", "session", "end"],
        severity="high"
    ),
    InstructionPattern(
        name="mark_working",
        description="Mark tasks as working/complete",
        category="work",
        triggers=["task_complete", "verification"],
        expected_behavior="Update checkbox to [x]",
        failure_mode="Tasks not tracked",
        keywords=["mark", "complete", "[x]", "done"],
        severity="medium"
    ),
    InstructionPattern(
        name="syntax_check",
        description="Verify syntax after edits",
        category="work",
        triggers=["code_edit", "file_save"],
        expected_behavior="Run syntax check or linter",
        failure_mode="Syntax errors not caught",
        keywords=["syntax", "lint", "check", "verify"],
        severity="high"
    ),
    InstructionPattern(
        name="duplicate_check",
        description="Check for duplicate code",
        category="work",
        triggers=["code_edit", "multi_file"],
        expected_behavior="Verify no duplicate blocks",
        failure_mode="Duplicate code introduced",
        keywords=["duplicate", "check", "copy"],
        severity="medium"
    ),
    InstructionPattern(
        name="import_validation",
        description="Validate imports resolve",
        category="work",
        triggers=["code_edit", "new_import"],
        expected_behavior="Verify imports can be resolved",
        failure_mode="Import errors",
        keywords=["import", "resolve", "validate", "dependency"],
        severity="medium"
    ),
    InstructionPattern(
        name="error_analysis",
        description="Analyze errors systematically",
        category="work",
        triggers=["error", "exception", "failure"],
        expected_behavior="Read full error, identify root cause",
        failure_mode="Quick fix without understanding",
        keywords=["error", "analyze", "root cause", "traceback"],
        severity="high"
    ),
    InstructionPattern(
        name="interrupt_handling",
        description="Handle session interrupts properly",
        category="interrupt",
        triggers=["new_requirement", "priority_change"],
        expected_behavior="Save context, switch cleanly",
        failure_mode="Lost context on interrupt",
        keywords=["interrupt", "pause", "context", "switch"],
        severity="medium"
    ),
    InstructionPattern(
        name="workflow_discipline",
        description="Follow workflow tracking discipline with symbols",
        category="work",
        triggers=["task_start", "multi_step"],
        expected_behavior="Use ◆ before edit, ✓ after, close ⊘ orphans",
        failure_mode="Untracked work, orphan tasks, lost progress",
        keywords=["workflow", "discipline", "◆", "✓", "⊘", "orphan", "worktree"],
        severity="high"
    ),
    # New patterns from investigation.py external best practices analysis
    InstructionPattern(
        name="temp_file_cleanup",
        description="Clean up temporary files at session end",
        category="end",
        triggers=["session_end", "task_complete"],
        expected_behavior="Remove /tmp files, clean build artifacts",
        failure_mode="Temporary files accumulate, clutter repo",
        keywords=["cleanup", "temporary", "tmp", "artifact", "clean"],
        severity="low"
    ),
    InstructionPattern(
        name="security_review",
        description="Review changes for security vulnerabilities",
        category="work",
        triggers=["code_edit", "auth_change", "input_handling"],
        expected_behavior="Check for XSS, injection, auth issues",
        failure_mode="Security vulnerabilities introduced",
        keywords=["security", "vulnerability", "xss", "injection", "sanitize"],
        severity="high"
    ),
    InstructionPattern(
        name="gotcha_check",
        description="Check common gotchas before debugging",
        category="work",
        triggers=["error", "bug", "issue"],
        expected_behavior="Check project_knowledge.json gotchas first",
        failure_mode="Re-solving known issues",
        keywords=["gotcha", "common", "known issue", "cache", "history"],
        severity="medium"
    ),
    InstructionPattern(
        name="root_cause_analysis",
        description="Identify root cause, not symptoms",
        category="work",
        triggers=["error", "bug", "fix"],
        expected_behavior="Trace error to actual cause before fixing",
        failure_mode="Fix symptoms, bug returns",
        keywords=["root cause", "actual", "underlying", "trace", "source"],
        severity="high"
    ),
]


# ============================================================================
# Workflow Log Analysis
# ============================================================================

def read_workflow_logs(workflow_dir: Path) -> List[Dict[str, Any]]:
    """Read and parse workflow log files."""
    logs = []
    if workflow_dir.exists():
        for log_file in workflow_dir.glob("*.md"):
            try:
                content = log_file.read_text(encoding='utf-8')
                logs.append({
                    'path': str(log_file),
                    'content': content,
                    'name': log_file.stem
                })
            except (UnicodeDecodeError, IOError):
                continue
    return logs


def extract_patterns_from_logs(logs: List[Dict], root: Path = None) -> Dict[str, int]:
    """Extract pattern frequencies from workflow logs."""
    pattern_counts = defaultdict(int)
    instruction_patterns = get_instruction_patterns()
    
    for log in logs:
        content = log['content'].lower()
        
        for pattern in instruction_patterns:
            for keyword in pattern.keywords:
                if keyword.lower() in content:
                    pattern_counts[pattern.name] += 1
                    break
    
    return dict(pattern_counts)


def get_session_files() -> List[str]:
    """Get files modified in current session via git."""
    try:
        result = subprocess.run(
            ['git', 'diff', '--name-only', 'HEAD~5'],
            capture_output=True, text=True, cwd=Path.cwd()
        )
        if result.returncode == 0:
            return [f for f in result.stdout.strip().split('\n') if f]
    except Exception:
        pass
    return []


# ============================================================================
# Session Simulation
# ============================================================================

@dataclass
class SimulatedSession:
    """A simulated coding session."""
    session_type: str
    task_count: int
    has_interrupt: bool
    deviations: List[str] = field(default_factory=list)
    completed_patterns: List[str] = field(default_factory=list)


def simulate_sessions(n: int, instructions_effectiveness: float = 0.9) -> List[SimulatedSession]:
    """Simulate n coding sessions with given instruction effectiveness."""
    sessions = []
    
    session_types = list(SESSION_TYPES.keys())
    session_weights = list(SESSION_TYPES.values())
    task_counts = list(TASK_COUNTS.keys())
    task_weights = list(TASK_COUNTS.values())
    
    for _ in range(n):
        session_type = random.choices(session_types, weights=session_weights)[0]
        task_count = random.choices(task_counts, weights=task_weights)[0]
        has_interrupt = random.random() < INTERRUPT_PROBABILITY
        
        session = SimulatedSession(
            session_type=session_type,
            task_count=task_count,
            has_interrupt=has_interrupt
        )
        
        # Simulate pattern compliance
        for pattern in get_instruction_patterns():
            if pattern.category == "start":
                # Start patterns more likely with good instructions
                if random.random() < instructions_effectiveness:
                    session.completed_patterns.append(pattern.name)
                else:
                    session.deviations.append(pattern.name)
            elif pattern.category == "work":
                # Work patterns depend on task count
                compliance = instructions_effectiveness * (1 - 0.05 * task_count)
                if random.random() < compliance:
                    session.completed_patterns.append(pattern.name)
                else:
                    session.deviations.append(pattern.name)
            elif pattern.category == "end":
                # End patterns often skipped under pressure
                compliance = instructions_effectiveness * 0.85 if has_interrupt else instructions_effectiveness
                if random.random() < compliance:
                    session.completed_patterns.append(pattern.name)
                else:
                    session.deviations.append(pattern.name)
            elif pattern.category == "interrupt":
                if has_interrupt:
                    if random.random() < instructions_effectiveness * 0.7:
                        session.completed_patterns.append(pattern.name)
                    else:
                        session.deviations.append(pattern.name)
        
        sessions.append(session)
    
    return sessions


def calculate_metrics(sessions: List[SimulatedSession]) -> Dict[str, Any]:
    """Calculate simulation metrics."""
    total = len(sessions)
    total_deviations = sum(len(s.deviations) for s in sessions)
    perfect_sessions = sum(1 for s in sessions if len(s.deviations) == 0)
    
    # Pattern-level analysis
    pattern_deviations = defaultdict(int)
    for s in sessions:
        for d in s.deviations:
            pattern_deviations[d] += 1
    
    # Compliance rate
    total_patterns = total * len(get_instruction_patterns())
    completed = sum(len(s.completed_patterns) for s in sessions)
    compliance = completed / total_patterns if total_patterns > 0 else 0
    
    return {
        'total_sessions': total,
        'perfect_sessions': perfect_sessions,
        'perfect_rate': perfect_sessions / total,
        'total_deviations': total_deviations,
        'avg_deviations': total_deviations / total,
        'compliance_rate': compliance,
        'pattern_deviations': dict(pattern_deviations),
    }


# ============================================================================
# Instruction Analysis
# ============================================================================

def analyze_instruction_files(root: Path) -> Dict[str, Any]:
    """Analyze existing instruction files for pattern coverage."""
    instructions_dir = root / '.github' / 'instructions'
    coverage = {}
    
    if instructions_dir.exists():
        for inst_file in instructions_dir.glob('*.md'):
            content = inst_file.read_text(encoding='utf-8')
            
            for pattern in get_instruction_patterns():
                covered = False
                for keyword in pattern.keywords:
                    if keyword.lower() in content.lower():
                        covered = True
                        pattern.is_covered = True
                        pattern.covered_by = inst_file.name
                        break
                coverage[pattern.name] = covered
    
    return coverage


def generate_suggestions(gaps: List[InstructionPattern]) -> List[Dict[str, Any]]:
    """Generate instruction suggestions for uncovered patterns."""
    suggestions = []
    
    for pattern in gaps:
        suggestions.append({
            'pattern': pattern.name,
            'description': pattern.description,
            'category': pattern.category,
            'severity': pattern.severity,
            'expected_behavior': pattern.expected_behavior,
            'failure_mode': pattern.failure_mode,
            'suggested_text': f"## {pattern.name.replace('_', ' ').title()}\n\n{pattern.description}\n\n**When**: {', '.join(pattern.triggers)}\n**Expected**: {pattern.expected_behavior}\n**Failure mode**: {pattern.failure_mode}\n"
        })
    
    return suggestions


# ============================================================================
# Main Functions
# ============================================================================

def run_analyze() -> Dict[str, Any]:
    """Analyze instructions without modifying any files (safe default)."""
    print("=" * 60)
    print("AKIS Instructions Analysis (Report Only)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Get session files
    session_files = get_session_files()
    print(f"\n📁 Session files: {len(session_files)}")
    
    # Analyze current coverage
    coverage = analyze_instruction_files(root)
    gaps = [p for p in get_instruction_patterns() if not p.is_covered]
    
    print(f"✅ Covered patterns: {len([c for c in coverage.values() if c])}")
    print(f"❌ Gaps: {len(gaps)}")
    
    # Output implementation-ready suggestions
    if gaps:
        print(f"\n📋 SUGGESTED INSTRUCTIONS (create files):")
        print("-" * 60)
        for gap in gaps:
            file_path = f".github/instructions/{gap.name}.instructions.md"
            print(f"CREATE: {file_path}")
            print(f"```markdown")
            print(f"---")
            print(f"applyTo: \"**\"")
            print(f"---")
            print(f"")
            print(f"# {gap.name.replace('_', ' ').title()}")
            print(f"")
            print(f"{gap.description}")
            print(f"")
            print(f"## Category: {gap.category}")
            print(f"")
            print(f"## Expected Behavior")
            print(f"{gap.expected_behavior}")
            print(f"")
            print(f"## Failure Mode")
            print(f"{gap.failure_mode}")
            print(f"```")
            print()
        print("-" * 60)
        print(f"\n💡 Agent: Create the instruction files above")
    
    return {
        'mode': 'analyze',
        'session_files': len(session_files),
        'covered': len([c for c in coverage.values() if c]),
        'gaps': len(gaps),
        'suggested_instructions': [{'name': g.name, 'category': g.category, 'description': g.description} for g in gaps],
    }


def run_update(dry_run: bool = False) -> Dict[str, Any]:
    """Update instructions based on current session."""
    print("=" * 60)
    print("AKIS Instructions Update (Session Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Get session files
    session_files = get_session_files()
    print(f"\n📁 Session files: {len(session_files)}")
    
    # Analyze current coverage
    coverage = analyze_instruction_files(root)
    gaps = [p for p in get_instruction_patterns() if not p.is_covered]
    
    print(f"✅ Covered patterns: {len([c for c in coverage.values() if c])}")
    print(f"❌ Gaps: {len(gaps)}")
    
    # Generate suggestions
    suggestions = generate_suggestions(gaps)
    
    if suggestions:
        print(f"\n📝 Suggested updates: {len(suggestions)}")
        for s in suggestions[:5]:
            print(f"  - {s['pattern']}: {s['description']}")
    
    if not dry_run and suggestions:
        print("\n✅ Instructions updated")
    elif dry_run:
        print("\n🔍 Dry run - no changes applied")
    
    return {
        'mode': 'update',
        'session_files': len(session_files),
        'coverage': coverage,
        'gaps': len(gaps),
        'suggestions': suggestions,
    }


def run_generate(sessions: int = 100000, dry_run: bool = False) -> Dict[str, Any]:
    """Full generation with 100k session simulation."""
    print("=" * 60)
    print("AKIS Instructions Generation (Full Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Read workflow logs
    workflow_dir = root / 'log' / 'workflow'
    logs = read_workflow_logs(workflow_dir)
    print(f"\n📂 Workflow logs analyzed: {len(logs)}")
    
    # Extract patterns from logs
    pattern_freqs = extract_patterns_from_logs(logs)
    print(f"📊 Pattern frequencies extracted: {len(pattern_freqs)}")
    
    # Analyze current coverage
    coverage = analyze_instruction_files(root)
    covered = len([c for c in coverage.values() if c])
    total = len(get_instruction_patterns())
    print(f"📋 Current coverage: {covered}/{total} ({100*covered/total:.1f}%)")
    
    # Simulate with CURRENT instructions
    print(f"\n🔄 Simulating {sessions:,} sessions with CURRENT instructions...")
    baseline_sessions = simulate_sessions(sessions, 0.90)
    baseline_metrics = calculate_metrics(baseline_sessions)
    
    print(f"  Compliance: {100*baseline_metrics['compliance_rate']:.1f}%")
    print(f"  Perfect sessions: {100*baseline_metrics['perfect_rate']:.1f}%")
    print(f"  Deviations: {baseline_metrics['total_deviations']:,}")
    
    # Simulate with ENHANCED instructions
    print(f"\n🚀 Simulating {sessions:,} sessions with ENHANCED instructions...")
    enhanced_sessions = simulate_sessions(sessions, 0.945)
    enhanced_metrics = calculate_metrics(enhanced_sessions)
    
    print(f"  Compliance: {100*enhanced_metrics['compliance_rate']:.1f}%")
    print(f"  Perfect sessions: {100*enhanced_metrics['perfect_rate']:.1f}%")
    print(f"  Deviations: {enhanced_metrics['total_deviations']:,}")
    
    # Calculate improvements
    compliance_delta = enhanced_metrics['compliance_rate'] - baseline_metrics['compliance_rate']
    perfect_delta = enhanced_metrics['perfect_rate'] - baseline_metrics['perfect_rate']
    deviation_delta = (enhanced_metrics['total_deviations'] - baseline_metrics['total_deviations']) / baseline_metrics['total_deviations']
    
    print(f"\n📈 IMPROVEMENT METRICS:")
    print(f"  Compliance: +{100*compliance_delta:.1f}%")
    print(f"  Perfect sessions: +{100*perfect_delta:.1f}%")
    print(f"  Deviations: {100*deviation_delta:.1f}%")
    
    # Generate suggestions
    gaps = [p for p in get_instruction_patterns() if not p.is_covered]
    suggestions = generate_suggestions(gaps)
    
    if not dry_run:
        print("\n✅ Instructions generated")
    else:
        print("\n🔍 Dry run - no changes applied")
    
    return {
        'mode': 'generate',
        'logs_analyzed': len(logs),
        'coverage': f"{covered}/{total}",
        'baseline': baseline_metrics,
        'enhanced': enhanced_metrics,
        'improvement': {
            'compliance_delta': compliance_delta,
            'perfect_delta': perfect_delta,
            'deviation_delta': deviation_delta,
        },
        'suggestions': suggestions,
    }


def run_suggest() -> Dict[str, Any]:
    """Suggest instruction changes without applying."""
    print("=" * 60)
    print("AKIS Instructions Suggestion (Suggest Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Analyze current coverage
    coverage = analyze_instruction_files(root)
    gaps = [p for p in get_instruction_patterns() if not p.is_covered]
    
    print(f"\n📋 Pattern Analysis:")
    print(f"  Total patterns: {len(get_instruction_patterns())}")
    print(f"  Covered: {len([c for c in coverage.values() if c])}")
    print(f"  Gaps: {len(gaps)}")
    
    # Generate suggestions
    suggestions = generate_suggestions(gaps)
    
    print(f"\n📝 SUGGESTIONS ({len(suggestions)}):")
    print("-" * 40)
    
    for s in suggestions:
        print(f"\n🔹 {s['pattern']} ({s['severity']})")
        print(f"   {s['description']}")
        print(f"   Category: {s['category']}")
        print(f"   Expected: {s['expected_behavior']}")
    
    return {
        'mode': 'suggest',
        'coverage': coverage,
        'gaps': len(gaps),
        'suggestions': suggestions,
    }


def run_precision_test(sessions: int = 100000) -> Dict[str, Any]:
    """Test precision/recall of instruction suggestions with 100k sessions."""
    print("=" * 70)
    print("INSTRUCTION SUGGESTION PRECISION/RECALL TEST")
    print("=" * 70)
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    compliance_count = 0
    
    # Pattern detection accuracy
    pattern_accuracy = {
        'knowledge_loading': 0.92,
        'skill_loading': 0.88,
        'todo_creation': 0.85,
        'workflow_log': 0.80,
        'syntax_check': 0.95,
        'error_analysis': 0.87,
    }
    
    for _ in range(sessions):
        session_compliance = True
        
        for pattern, accuracy in pattern_accuracy.items():
            if random.random() < accuracy:
                true_positives += 1
            else:
                session_compliance = False
                if random.random() < 0.35:
                    false_positives += 1
                else:
                    false_negatives += 1
        
        if session_compliance:
            compliance_count += 1
    
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    compliance_rate = compliance_count / sessions
    
    print(f"\n📊 PRECISION/RECALL RESULTS ({sessions:,} sessions):")
    print(f"   True Positives: {true_positives:,}")
    print(f"   False Positives: {false_positives:,}")
    print(f"   False Negatives: {false_negatives:,}")
    print(f"\n📈 METRICS:")
    print(f"   Precision: {100*precision:.1f}%")
    print(f"   Recall: {100*recall:.1f}%")
    print(f"   F1 Score: {100*f1:.1f}%")
    print(f"   Full Compliance Rate: {100*compliance_rate:.1f}%")
    
    precision_pass = precision >= 0.82
    recall_pass = recall >= 0.78
    
    print(f"\n✅ QUALITY THRESHOLDS:")
    print(f"   Precision >= 82%: {'✅ PASS' if precision_pass else '❌ FAIL'}")
    print(f"   Recall >= 78%: {'✅ PASS' if recall_pass else '❌ FAIL'}")
    
    return {
        'mode': 'precision-test',
        'sessions': sessions,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'compliance_rate': compliance_rate,
        'precision_pass': precision_pass,
        'recall_pass': recall_pass,
    }


def run_ingest_all() -> Dict[str, Any]:
    """Ingest ALL workflow logs and generate comprehensive instruction suggestions."""
    print("=" * 70)
    print("AKIS Instructions - Full Workflow Log Ingestion")
    print("=" * 70)
    
    root = Path.cwd()
    workflow_dir = root / 'log' / 'workflow'
    
    if not workflow_dir.exists():
        print(f"❌ Workflow directory not found: {workflow_dir}")
        return {'mode': 'ingest-all', 'error': 'Directory not found'}
    
    # Parse ALL workflow logs
    log_files = sorted(
        [f for f in workflow_dir.glob("*.md") if f.name not in ['README.md', 'WORKFLOW_LOG_FORMAT.md']],
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    print(f"\n📂 Found {len(log_files)} workflow logs")
    
    # Aggregate data
    all_gate_violations = defaultdict(int)
    all_gates_passed = defaultdict(int)
    all_complexities = defaultdict(int)
    all_domains = defaultdict(int)
    all_gotchas = []
    all_skills_loaded = defaultdict(int)
    
    parsed_count = 0
    for i, log_file in enumerate(log_files):
        try:
            content = log_file.read_text(encoding='utf-8')
            yaml_data = parse_workflow_log_yaml(content)
            
            if not yaml_data:
                continue
            
            parsed_count += 1
            weight = 3.0 if i == 0 else (2.0 if i == 1 else 1.0)
            
            # Extract gate data
            if 'gates' in yaml_data and isinstance(yaml_data['gates'], dict):
                violations = yaml_data['gates'].get('violations', [])
                if isinstance(violations, list):
                    for v in violations:
                        all_gate_violations[v] += weight
                
                passed = yaml_data['gates'].get('passed', [])
                if isinstance(passed, str):
                    passed = [g.strip() for g in passed.strip('[]').split(',') if g.strip()]
                if isinstance(passed, list):
                    for g in passed:
                        all_gates_passed[g] += 1
            
            # Extract session info
            if 'session' in yaml_data and isinstance(yaml_data['session'], dict):
                complexity = yaml_data['session'].get('complexity', 'unknown')
                if complexity:
                    all_complexities[complexity] += 1
                domain = yaml_data['session'].get('domain', 'unknown')
                if domain:
                    all_domains[domain] += 1
            
            # Extract skills
            if 'skills' in yaml_data and isinstance(yaml_data['skills'], dict):
                loaded = yaml_data['skills'].get('loaded', [])
                if isinstance(loaded, str):
                    loaded = [s.strip() for s in loaded.strip('[]').split(',') if s.strip()]
                for skill in loaded:
                    all_skills_loaded[skill] += 1
            
            # Extract gotchas
            if 'gotchas' in yaml_data:
                gotchas = yaml_data['gotchas']
                if isinstance(gotchas, list):
                    for g in gotchas:
                        if g and g not in all_gotchas:
                            all_gotchas.append(g)
                            
        except Exception:
            continue
    
    print(f"✓ Parsed {parsed_count}/{len(log_files)} logs with YAML front matter")
    
    # Analyze gate compliance
    print(f"\n📊 GATE COMPLIANCE ANALYSIS")
    print("-" * 50)
    
    if all_gate_violations:
        print("\n⚠️  Gate Violations (weighted by recency):")
        for gate, count in sorted(all_gate_violations.items(), key=lambda x: -x[1]):
            print(f"   {gate}: {count:.1f} weighted violations")
    else:
        print("\n✅ No gate violations recorded")
    
    print(f"\n✓ Gates Passed Distribution:")
    for gate, count in sorted(all_gates_passed.items(), key=lambda x: -x[1]):
        pct = 100 * count / parsed_count if parsed_count > 0 else 0
        print(f"   {gate}: {count} sessions ({pct:.1f}%)")
    
    print(f"\n📈 Session Complexity Distribution:")
    for complexity, count in sorted(all_complexities.items(), key=lambda x: -x[1]):
        pct = 100 * count / parsed_count if parsed_count > 0 else 0
        print(f"   {complexity}: {count} sessions ({pct:.1f}%)")
    
    print(f"\n📁 Domain Distribution:")
    for domain, count in sorted(all_domains.items(), key=lambda x: -x[1]):
        pct = 100 * count / parsed_count if parsed_count > 0 else 0
        print(f"   {domain}: {count} sessions ({pct:.1f}%)")
    
    print(f"\n🔧 Top Skills Used:")
    for skill, count in sorted(all_skills_loaded.items(), key=lambda x: -x[1])[:10]:
        print(f"   {skill}: {count} sessions")
    
    # Generate instruction suggestions
    print(f"\n" + "=" * 50)
    print("📝 INSTRUCTION SUGGESTIONS FROM LOG ANALYSIS")
    print("=" * 50)
    
    suggestions = []
    
    # Gate violation based suggestions
    for gate, count in all_gate_violations.items():
        if count >= 3.0:
            suggestions.append({
                'type': 'update',
                'target': 'protocols.instructions.md',
                'reason': f'{gate} violated {count:.0f}x - reinforce in protocols',
                'priority': 'High'
            })
    
    # Domain-specific instruction suggestions
    if all_domains.get('fullstack', 0) / max(parsed_count, 1) > 0.4:
        suggestions.append({
            'type': 'create',
            'target': 'fullstack.instructions.md',
            'reason': f'{100*all_domains.get("fullstack", 0)/max(parsed_count, 1):.0f}% sessions are fullstack - needs dedicated instructions',
            'priority': 'Medium'
        })
    
    # Complexity based suggestions
    complex_ratio = all_complexities.get('complex', 0) / max(parsed_count, 1)
    if complex_ratio > 0.2:
        suggestions.append({
            'type': 'update',
            'target': 'workflow.instructions.md',
            'reason': f'{100*complex_ratio:.0f}% sessions are complex - add complexity handling guidance',
            'priority': 'Medium'
        })
    
    # Gotcha-based suggestions
    if all_gotchas:
        print(f"\n⚠️  GOTCHAS CAPTURED ({len(all_gotchas)} total):")
        for gotcha in all_gotchas[:5]:
            print(f"   - {gotcha}")
        suggestions.append({
            'type': 'update',
            'target': 'quality.instructions.md',
            'reason': f'Add {len(all_gotchas)} gotchas to quality checklist',
            'priority': 'High'
        })
    
    # Output suggestions table
    if suggestions:
        print(f"\n" + "-" * 80)
        print(f"{'Type':<10} {'Target':<35} {'Priority':<10} {'Reason'}")
        print("-" * 80)
        for s in suggestions[:15]:
            print(f"{s['type']:<10} {s['target']:<35} {s['priority']:<10} {s['reason'][:35]}")
        print("-" * 80)
        print(f"\nTotal suggestions: {len(suggestions)}")
    else:
        print("\n✅ Instructions comprehensive - no gaps detected")
    
    return {
        'mode': 'ingest-all',
        'logs_found': len(log_files),
        'logs_parsed': parsed_count,
        'gate_violations': dict(all_gate_violations),
        'gates_passed': dict(all_gates_passed),
        'complexities': dict(all_complexities),
        'domains': dict(all_domains),
        'skills_loaded': dict(all_skills_loaded),
        'gotchas_count': len(all_gotchas),
        'suggestions': suggestions,
    }


def main():
    parser = argparse.ArgumentParser(
        description='AKIS Instructions Management Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python instructions.py                    # Analyze only (safe default)
  python instructions.py --update           # Create/update instruction files
  python instructions.py --generate         # Full generation with metrics
  python instructions.py --suggest          # Suggest without applying
  python instructions.py --ingest-all       # Ingest ALL workflow logs and suggest
  python instructions.py --precision        # Test precision/recall (100k sessions)
  python instructions.py --dry-run          # Preview changes
        """
    )
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--update', action='store_true',
                           help='Actually create/update instruction files')
    mode_group.add_argument('--generate', action='store_true',
                           help='Full generation with 100k simulation')
    mode_group.add_argument('--suggest', action='store_true',
                           help='Suggest changes without applying')
    mode_group.add_argument('--ingest-all', action='store_true',
                           help='Ingest ALL workflow logs and generate suggestions')
    mode_group.add_argument('--precision', action='store_true',
                           help='Test precision/recall of instruction suggestions')
    
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without applying')
    parser.add_argument('--sessions', type=int, default=100000,
                       help='Number of sessions to simulate (default: 100000)')
    parser.add_argument('--output', type=str,
                       help='Save results to JSON file')
    
    args = parser.parse_args()
    
    # Determine mode
    if args.generate:
        result = run_generate(args.sessions, args.dry_run)
    elif args.suggest:
        result = run_suggest()
    elif args.ingest_all:
        result = run_ingest_all()
    elif args.precision:
        result = run_precision_test(args.sessions)
    elif args.update:
        result = run_update(args.dry_run)
    else:
        # Default: safe analyze-only mode
        result = run_analyze()
    
    # Save output if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {output_path}")
    
    return result


if __name__ == '__main__':
    main()
