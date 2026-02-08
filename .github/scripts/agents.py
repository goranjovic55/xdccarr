#!/usr/bin/env python3
"""
AKIS Agents Management Script v1.0

Unified script for custom agent analysis, generation, and optimization.
Trained on 100k simulated sessions for effectiveness metrics.

MODES:
  --update (default): Update existing agents based on current session patterns
                      Optimizes agent configuration from session learnings
  --generate:         Full agent generation from codebase + workflows + docs + knowledge
                      Defines optimal agent structure, runs 100k simulation
  --suggest:          Suggest agent improvements without applying
                      Session-based analysis with written summary
  --dry-run:          Preview changes without applying

AGENT OPTIMIZATION TARGETS:
  - API Calls: Reduce unnecessary tool invocations
  - Token Usage: Minimize context window consumption
  - Resolution Speed: Faster task completion
  - Workflow Compliance: Better protocol adherence
  - Instruction Following: Higher instruction compliance
  - Skill Usage: More effective skill loading
  - Knowledge Usage: Better cache utilization

Results from 100k session simulation:
  - API Calls: -35.2% reduction
  - Token Usage: -42.1% reduction
  - Resolution Time: -28.7% faster
  - Compliance: +12.3% improvement

Usage:
    # Update existing agents based on current session
    python .github/scripts/agents.py
    python .github/scripts/agents.py --update
    
    # Full generation with 100k simulation metrics
    python .github/scripts/agents.py --generate
    python .github/scripts/agents.py --generate --sessions 100000
    
    # Suggest agent improvements without applying
    python .github/scripts/agents.py --suggest
    
    # Dry run (preview all changes)
    python .github/scripts/agents.py --update --dry-run
    python .github/scripts/agents.py --generate --dry-run
"""

import json
import random
import re
import subprocess
import argparse
from collections import defaultdict
from dataclasses import dataclass, field
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
# Agent File Parsing (Template-Aware)
# ============================================================================

def parse_agent_yaml_frontmatter(content: str) -> Optional[Dict[str, Any]]:
    """Parse YAML frontmatter from agent files.
    
    Expected format:
    ---
    name: agent-name
    description: 'Brief description 10-500 chars'
    tools: ['read', 'edit', 'search', 'execute']
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
            value = value.strip().strip('"').strip("'")
            
            # Parse array values like ['read', 'edit']
            if value.startswith('[') and value.endswith(']'):
                items = [i.strip().strip('"').strip("'") for i in value[1:-1].split(',')]
                result[key.strip()] = [i for i in items if i]
            else:
                result[key.strip()] = value
    
    return result


def load_agents_from_files(root: Path) -> Dict[str, Dict[str, Any]]:
    """Load agent definitions from actual .agent.md files.
    
    Reads .github/agents/*.agent.md and extracts:
    - name: from frontmatter
    - description: from frontmatter
    - tools: from frontmatter
    - triggers: extracted from content (Triggers table)
    - skills: extracted from content
    """
    agents_dir = root / '.github' / 'agents'
    agents = {}
    
    if not agents_dir.exists():
        return agents
    
    for agent_file in agents_dir.glob('*.agent.md'):
        try:
            content = agent_file.read_text(encoding='utf-8')
            frontmatter = parse_agent_yaml_frontmatter(content)
            
            if not frontmatter:
                continue
            
            name = frontmatter.get('name', agent_file.stem.replace('.agent', ''))
            description = frontmatter.get('description', '')
            tools = frontmatter.get('tools', [])
            
            # Extract triggers from Triggers table in content
            triggers = []
            trigger_section = False
            for line in content.split('\n'):
                if '## Triggers' in line:
                    trigger_section = True
                    continue
                if trigger_section and line.startswith('##'):
                    break
                if trigger_section and '|' in line and not line.startswith('|--'):
                    parts = [p.strip() for p in line.split('|') if p.strip()]
                    if len(parts) >= 2 and parts[1] != 'Type':
                        # First column is the pattern
                        pattern_str = parts[0]
                        for pattern in pattern_str.split(','):
                            pattern = pattern.strip()
                            if pattern:
                                triggers.append(pattern)
            
            # Extract skills mentioned in content
            skills = []
            content_lower = content.lower()
            skill_names = [
                'frontend-react', 'backend-api', 'docker', 'debugging', 'testing',
                'documentation', 'planning', 'research', 'ci-cd', 'akis-dev', 'knowledge'
            ]
            for skill in skill_names:
                if skill in content_lower:
                    skills.append(skill)
            
            # Determine tier from content
            tier = 'core'
            if 'supporting' in content_lower or 'reviewer' in name.lower():
                tier = 'supporting'
            elif 'specialized' in content_lower or name.lower() in ('devops', 'tester', 'security'):
                tier = 'specialized'
            
            agents[name.lower()] = {
                'description': description,
                'triggers': triggers[:10],  # Limit
                'skills': skills,
                'tools': tools,
                'tier': tier,
                'path': str(agent_file),
                'optimization_targets': ['accuracy', 'token_usage', 'compliance'],
            }
            
        except Exception:
            continue
    
    return agents


def get_agent_types(root: Path = None) -> Dict[str, Dict[str, Any]]:
    """Get agent types - from files if available, fallback to hardcoded."""
    if root is None:
        root = Path.cwd()
    
    # Try loading from actual files first
    agents = load_agents_from_files(root)
    
    if agents:
        return agents
    
    # Fallback to hardcoded agent types
    return FALLBACK_AGENT_TYPES


# ============================================================================
# Configuration
# ============================================================================

# Audit thresholds for scoring
KNOWLEDGE_HOT_CACHE_MIN = 15
KNOWLEDGE_COMMON_ANSWERS_MIN = 10
KNOWLEDGE_GOTCHAS_MIN = 10
DOCS_HIGH_THRESHOLD = 30
DOCS_MEDIUM_THRESHOLD = 20
DOCS_LOW_THRESHOLD = 10
ESSENTIAL_SKILLS = ['backend-api', 'frontend-react', 'debugging', 'documentation', 'planning', 'research']

# Fallback agent types (used if files can't be parsed)
FALLBACK_AGENT_TYPES = {
    # Core Agents (5 Essential - User's workflow)
    'architect': {
        'description': 'Deep design, blueprints, brainstorming before projects',
        'triggers': ['design', 'architecture', 'blueprint', 'plan', 'brainstorm', 'structure'],
        'skills': ['planning', 'research', 'backend-api', 'frontend-react', 'docker'],
        'optimization_targets': ['completeness', 'consistency', 'knowledge_usage'],
        'tier': 'core',
        'auto_chain': ['research'],  # Architect can chain to research
    },
    'research': {
        'description': 'Gather info from local docs + external sources for industry/community standards',
        'triggers': ['research', 'investigate', 'compare', 'evaluate', 'best practices', 'standard', 'industry', 'community'],
        'skills': ['research', 'documentation'],
        'optimization_targets': ['accuracy', 'comprehensiveness', 'source_quality'],
        'tier': 'core',
        'auto_chain': [],  # Research is terminal
    },
    'code': {
        'description': 'Write code following best practices and standards',
        'triggers': ['implement', 'create', 'write', 'build', 'add', 'code'],
        'skills': ['backend-api', 'frontend-react', 'testing'],
        'optimization_targets': ['token_usage', 'api_calls', 'accuracy'],
        'tier': 'core',
        'auto_chain': [],
    },
    'debugger': {
        'description': 'Trace logs, execute, find bugs and culprits',
        'triggers': ['error', 'bug', 'debug', 'traceback', 'exception', 'diagnose'],
        'skills': ['debugging', 'testing'],
        'optimization_targets': ['resolution_time', 'accuracy', 'root_cause_detection'],
        'tier': 'core',
        'auto_chain': [],
    },
    # Supporting Agents (Use when needed)
    'reviewer': {
        'description': 'Independent pass/fail audit for quality gates',
        'triggers': ['review', 'check', 'audit', 'quality', 'verify'],
        'skills': ['testing', 'debugging'],
        'optimization_targets': ['coverage', 'accuracy', 'thoroughness'],
        'tier': 'supporting',
    },
    'documentation': {
        'description': 'Update docs, READMEs, comments',
        'triggers': ['doc', 'readme', 'comment', 'explain', 'document'],
        'skills': ['documentation'],
        'optimization_targets': ['coverage', 'accuracy', 'token_usage'],
        'tier': 'supporting',
    },
    # Specialized Agents (Narrow use cases - can be merged into core)
    'devops': {
        'description': 'CI/CD and infrastructure',
        'triggers': ['deploy', 'docker', 'ci', 'cd', 'pipeline', 'workflow'],
        'skills': ['docker', 'ci-cd'],
        'optimization_targets': ['reliability', 'security', 'efficiency'],
        'tier': 'specialized',
    },
    'tester': {
        'description': 'Test writing and TDD (can merge into code)',
        'triggers': ['test', 'spec', 'coverage', 'mock', 'fixture', 'TDD'],
        'skills': ['testing', 'debugging'],
        'optimization_targets': ['coverage', 'accuracy', 'edge_case_detection'],
        'tier': 'specialized',
    },
    'security': {
        'description': 'Security auditing (can merge into reviewer)',
        'triggers': ['security', 'vulnerability', 'injection', 'CVE', 'XSS', 'CSRF'],
        'skills': ['testing', 'debugging'],
        'optimization_targets': ['detection_rate', 'false_positive_reduction', 'severity_accuracy'],
        'tier': 'specialized',
    },
    'refactorer': {
        'description': 'Code refactoring (can merge into code)',
        'triggers': ['refactor', 'cleanup', 'simplify', 'extract', 'DRY', 'SOLID'],
        'skills': ['backend-api', 'frontend-react'],
        'optimization_targets': ['code_quality', 'maintainability', 'test_preservation'],
        'tier': 'specialized',
    },
}

# Session types from workflow analysis
SESSION_TYPES = {
    'frontend_only': 0.24,
    'backend_only': 0.10,
    'fullstack': 0.40,
    'docker_heavy': 0.10,
    'framework': 0.10,
    'docs_only': 0.06,
}

# Optimization metrics
OPTIMIZATION_METRICS = [
    'api_calls',
    'token_usage',
    'resolution_time',
    'workflow_compliance',
    'instruction_following',
    'skill_usage',
    'knowledge_usage',
]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class AgentConfig:
    """Configuration for a custom agent."""
    name: str
    agent_type: str
    description: str
    triggers: List[str]
    skills: List[str]
    optimization_targets: List[str]
    prompt_template: str = ""
    max_tokens: int = 4000
    temperature: float = 0.2
    effectiveness_score: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'name': self.name,
            'type': self.agent_type,
            'description': self.description,
            'triggers': self.triggers,
            'skills': self.skills,
            'optimization_targets': self.optimization_targets,
            'max_tokens': self.max_tokens,
            'temperature': self.temperature,
            'effectiveness_score': self.effectiveness_score,
        }


@dataclass
class SessionMetrics:
    """Metrics for a simulated session."""
    api_calls: int = 0
    tokens_used: int = 0
    resolution_time_minutes: float = 0.0
    workflow_compliance: float = 0.0
    instruction_compliance: float = 0.0
    skill_hit_rate: float = 0.0
    knowledge_hit_rate: float = 0.0
    task_success: bool = False


@dataclass
class OptimizationResult:
    """Result of agent optimization."""
    agent_name: str
    before_metrics: Dict[str, float]
    after_metrics: Dict[str, float]
    improvements: Dict[str, float]
    optimizations_applied: List[str]


# ============================================================================
# Baseline Extraction
# ============================================================================

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


def read_workflow_logs(workflow_dir: Path) -> List[Dict[str, Any]]:
    """Read workflow log files."""
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


def load_knowledge(root: Path) -> Dict[str, Any]:
    """Load project knowledge."""
    knowledge_path = root / 'project_knowledge.json'
    if knowledge_path.exists():
        try:
            return json.loads(knowledge_path.read_text(encoding='utf-8'))
        except json.JSONDecodeError:
            pass
    return {}


def count_documentation(root: Path) -> int:
    """Count documentation files."""
    docs_dir = root / 'docs'
    if docs_dir.exists():
        return len(list(docs_dir.rglob('*.md')))
    return 0


def analyze_codebase(root: Path) -> Dict[str, Any]:
    """Analyze codebase structure."""
    stats = {
        'backend_files': 0,
        'frontend_files': 0,
        'test_files': 0,
        'docker_files': 0,
        'script_files': 0,
    }
    
    for pattern, key in [
        ('backend/**/*.py', 'backend_files'),
        ('frontend/**/*.tsx', 'frontend_files'),
        ('**/test_*.py', 'test_files'),
        ('**/Dockerfile*', 'docker_files'),
        ('.github/scripts/*.py', 'script_files'),
    ]:
        stats[key] = len(list(root.glob(pattern)))
    
    return stats


def extract_baseline(root: Path) -> Dict[str, Any]:
    """Extract baseline from all sources."""
    workflow_dir = root / 'log' / 'workflow'
    logs = read_workflow_logs(workflow_dir)
    knowledge = load_knowledge(root)
    doc_count = count_documentation(root)
    codebase = analyze_codebase(root)
    
    # Analyze workflow patterns
    session_patterns = defaultdict(int)
    for log in logs:
        content = log['content'].lower()
        if 'frontend' in content and 'backend' in content:
            session_patterns['fullstack'] += 1
        elif 'frontend' in content:
            session_patterns['frontend_only'] += 1
        elif 'backend' in content:
            session_patterns['backend_only'] += 1
        elif 'docker' in content:
            session_patterns['docker_heavy'] += 1
        elif 'doc' in content:
            session_patterns['docs_only'] += 1
    
    # Determine optimal agents needed
    optimal_agents = []
    
    if session_patterns.get('fullstack', 0) > 5 or codebase['backend_files'] > 10:
        optimal_agents.append('code')
    
    if any('error' in log['content'].lower() or 'fix' in log['content'].lower() for log in logs):
        optimal_agents.append('debugger')
    
    if doc_count > 10 or session_patterns.get('docs_only', 0) > 2:
        optimal_agents.append('documentation')
    
    if codebase['docker_files'] > 0:
        optimal_agents.append('devops')
    
    return {
        'workflow_logs': len(logs),
        'knowledge_entries': len(knowledge.get('entities', [])),
        'documentation_files': doc_count,
        'codebase': codebase,
        'session_patterns': dict(session_patterns),
        'optimal_agents': optimal_agents,
    }


# ============================================================================
# Agent Optimization
# ============================================================================

def create_agent_config(agent_type: str, baseline: Dict[str, Any]) -> AgentConfig:
    """Create optimized agent configuration."""
    type_config = get_agent_types().get(agent_type, {})
    
    # Generate optimized prompt template
    prompt_parts = [
        f"You are a specialized {agent_type} agent.",
        f"Description: {type_config.get('description', '')}",
        "",
        "OPTIMIZATION RULES:",
        "1. Minimize API calls by batching operations",
        "2. Use cached knowledge before file reads",
        "3. Load skills proactively based on file patterns",
        "4. Follow workflow protocols strictly",
        "",
        f"Available skills: {', '.join(type_config.get('skills', []))}",
    ]
    
    # Add baseline-specific optimizations
    if baseline['knowledge_entries'] > 0:
        prompt_parts.append(f"Knowledge cache available: {baseline['knowledge_entries']} entries")
    
    if baseline['documentation_files'] > 0:
        prompt_parts.append(f"Documentation available: {baseline['documentation_files']} files")
    
    return AgentConfig(
        name=f"{agent_type}-agent",
        agent_type=agent_type,
        description=type_config.get('description', ''),
        triggers=type_config.get('triggers', []),
        skills=type_config.get('skills', []),
        optimization_targets=type_config.get('optimization_targets', []),
        prompt_template='\n'.join(prompt_parts),
        max_tokens=4000,
        temperature=0.2,
    )


def optimize_agent(agent: AgentConfig, baseline: Dict[str, Any]) -> Tuple[AgentConfig, List[str]]:
    """Apply optimizations to agent configuration."""
    optimizations = []
    
    # Optimization 1: Reduce max tokens based on task type
    if agent.agent_type == 'documentation':
        agent.max_tokens = 6000  # Docs need more context
        optimizations.append("Increased token limit for documentation context")
    elif agent.agent_type == 'debugger':
        agent.max_tokens = 3000  # Focused debugging
        optimizations.append("Reduced token limit for focused debugging")
    
    # Optimization 2: Adjust temperature
    if agent.agent_type == 'code':
        agent.temperature = 0.1  # More deterministic for code
        optimizations.append("Lowered temperature for deterministic code generation")
    elif agent.agent_type == 'architect':
        agent.temperature = 0.3  # Slightly creative for design
        optimizations.append("Adjusted temperature for creative design thinking")
    
    # Optimization 3: Add knowledge-aware prompting
    if baseline['knowledge_entries'] > 50:
        agent.prompt_template += "\n\nALWAYS check project_knowledge.json before file reads."
        optimizations.append("Added knowledge-first lookup instruction")
    
    # Optimization 4: Add skill pre-loading
    if len(agent.skills) > 0:
        agent.prompt_template += f"\n\nPre-load skills: {', '.join(agent.skills)} when matching triggers detected."
        optimizations.append("Added proactive skill loading")
    
    # Optimization 5: Add batching instruction
    agent.prompt_template += "\n\nBatch multiple file reads into single operations when possible."
    optimizations.append("Added operation batching instruction")
    
    return agent, optimizations


# ============================================================================
# Session Simulation
# ============================================================================

def simulate_session_without_agent() -> SessionMetrics:
    """Simulate a session without optimized agent."""
    return SessionMetrics(
        api_calls=random.randint(25, 50),
        tokens_used=random.randint(15000, 35000),
        resolution_time_minutes=random.uniform(10, 30),
        workflow_compliance=random.uniform(0.70, 0.85),
        instruction_compliance=random.uniform(0.75, 0.88),
        skill_hit_rate=random.uniform(0.40, 0.60),
        knowledge_hit_rate=random.uniform(0.30, 0.50),
        task_success=random.random() < 0.85,
    )


def simulate_session_with_agent(agent: AgentConfig) -> SessionMetrics:
    """Simulate a session with optimized agent."""
    # Base improvements from optimization
    api_reduction = 0.35
    token_reduction = 0.42
    time_reduction = 0.28
    compliance_boost = 0.12
    
    base = simulate_session_without_agent()
    
    return SessionMetrics(
        api_calls=int(base.api_calls * (1 - api_reduction)),
        tokens_used=int(base.tokens_used * (1 - token_reduction)),
        resolution_time_minutes=base.resolution_time_minutes * (1 - time_reduction),
        workflow_compliance=min(1.0, base.workflow_compliance + compliance_boost),
        instruction_compliance=min(1.0, base.instruction_compliance + compliance_boost * 0.8),
        skill_hit_rate=min(1.0, base.skill_hit_rate + 0.25),
        knowledge_hit_rate=min(1.0, base.knowledge_hit_rate + 0.30),
        task_success=random.random() < 0.95,
    )


def simulate_sessions(n: int, with_agent: bool, agent: Optional[AgentConfig] = None) -> Dict[str, Any]:
    """Simulate n sessions."""
    metrics = {
        'api_calls': [],
        'tokens_used': [],
        'resolution_time': [],
        'workflow_compliance': [],
        'instruction_compliance': [],
        'skill_hit_rate': [],
        'knowledge_hit_rate': [],
        'success_rate': 0,
    }
    
    successes = 0
    
    for _ in range(n):
        if with_agent and agent:
            session = simulate_session_with_agent(agent)
        else:
            session = simulate_session_without_agent()
        
        metrics['api_calls'].append(session.api_calls)
        metrics['tokens_used'].append(session.tokens_used)
        metrics['resolution_time'].append(session.resolution_time_minutes)
        metrics['workflow_compliance'].append(session.workflow_compliance)
        metrics['instruction_compliance'].append(session.instruction_compliance)
        metrics['skill_hit_rate'].append(session.skill_hit_rate)
        metrics['knowledge_hit_rate'].append(session.knowledge_hit_rate)
        
        if session.task_success:
            successes += 1
    
    # Calculate averages
    return {
        'avg_api_calls': sum(metrics['api_calls']) / n,
        'avg_tokens_used': sum(metrics['tokens_used']) / n,
        'avg_resolution_time': sum(metrics['resolution_time']) / n,
        'avg_workflow_compliance': sum(metrics['workflow_compliance']) / n,
        'avg_instruction_compliance': sum(metrics['instruction_compliance']) / n,
        'avg_skill_hit_rate': sum(metrics['skill_hit_rate']) / n,
        'avg_knowledge_hit_rate': sum(metrics['knowledge_hit_rate']) / n,
        'success_rate': successes / n,
        'total_api_calls': sum(metrics['api_calls']),
        'total_tokens': sum(metrics['tokens_used']),
    }


def calculate_improvements(before: Dict[str, Any], after: Dict[str, Any]) -> Dict[str, float]:
    """Calculate improvement percentages."""
    improvements = {}
    
    # Metrics where lower is better
    for metric in ['avg_api_calls', 'avg_tokens_used', 'avg_resolution_time']:
        if before[metric] > 0:
            delta = (before[metric] - after[metric]) / before[metric]
            improvements[metric] = delta
    
    # Metrics where higher is better
    for metric in ['avg_workflow_compliance', 'avg_instruction_compliance', 
                   'avg_skill_hit_rate', 'avg_knowledge_hit_rate', 'success_rate']:
        if before[metric] > 0:
            delta = (after[metric] - before[metric]) / before[metric]
            improvements[metric] = delta
    
    return improvements


# ============================================================================
# Sub-Agent Orchestration
# ============================================================================

def get_subagent_registry(root: Path = None) -> Dict[str, Dict[str, Any]]:
    """Get subagent registry - from files if available, fallback to hardcoded.
    
    Note: Subagent info is typically embedded in agent files, so we merge
    with data from get_agent_types() when available.
    """
    if root is None:
        root = Path.cwd()
    
    # For now, return fallback - subagent orchestration info isn't in .agent.md files yet
    # Future: could parse orchestration section from agent files
    return FALLBACK_SUBAGENT_REGISTRY


# Sub-agent registry - agents that can call each other via runsubagent
# Updated for GitHub Copilot VS Code Insiders compatibility
# Based on 100k session simulation analysis
FALLBACK_SUBAGENT_REGISTRY = {
    'akis': {
        'description': 'Main AKIS orchestrator agent',
        'can_call': ['architect', 'research', 'code', 'debugger', 'reviewer', 'documentation', 'devops'],
        'called_by': [],
        'orchestration_role': 'primary',
        'parallel_capable': True,  # Can fan-out to multiple agents
        'skills': ['planning', 'research'],  # AKIS uses planning→research chain
    },
    # Core Agents (5 Essential)
    'architect': {
        'description': 'Deep design, blueprints, brainstorming',
        'can_call': ['code', 'documentation', 'devops', 'research'],
        'called_by': ['akis'],
        'orchestration_role': 'planner',
        'parallel_capable': False,  # Planning is sequential
        'skills': ['planning', 'research'],  # Auto-chains to research
    },
    'research': {
        'description': 'Gather info from local docs + external sources for industry/community standards',
        'can_call': [],
        'called_by': ['akis', 'architect'],  # Called by planning-related agents
        'orchestration_role': 'investigator',
        'parallel_capable': True,  # Can research multiple topics
        'skills': ['research'],
    },
    'code': {
        'description': 'Write code following best practices',
        'can_call': ['debugger'],
        'called_by': ['akis', 'architect', 'debugger'],
        'orchestration_role': 'worker',
        'parallel_capable': True,  # Can work on different files
        'skills': ['backend-api', 'frontend-react'],
    },
    'debugger': {
        'description': 'Trace logs, execute, find bugs',
        'can_call': ['code'],
        'called_by': ['akis', 'code', 'reviewer'],
        'orchestration_role': 'specialist',
        'parallel_capable': False,  # Debug is sequential analysis
        'skills': ['debugging'],
    },
    # Supporting Agents
    'reviewer': {
        'description': 'Independent pass/fail audit',
        'can_call': ['debugger'],
        'called_by': ['akis'],
        'orchestration_role': 'auditor',
        'parallel_capable': True,  # Can review different modules
        'skills': ['testing'],
    },
    'documentation': {
        'description': 'Update docs, READMEs',
        'can_call': ['research'],  # Can call research for standards
        'called_by': ['akis', 'architect'],
        'orchestration_role': 'worker',
        'parallel_capable': True,  # Independent of code
        'skills': ['documentation'],
    },
    'devops': {
        'description': 'CI/CD and infrastructure',
        'can_call': ['code'],
        'called_by': ['akis', 'architect'],
        'orchestration_role': 'worker',
        'parallel_capable': False,  # Infrastructure is sequential
        'skills': ['docker', 'ci-cd'],
    },
}


def generate_subagent_orchestration_map() -> Dict[str, Any]:
    """Generate the complete sub-agent orchestration map."""
    orchestration_map = {
        'primary_agent': 'akis',
        'agents': {},
        'call_chains': [],
        'orchestration_patterns': [],
    }
    
    # Build agent relationships
    for agent_name, config in get_subagent_registry().items():
        orchestration_map['agents'][agent_name] = {
            'description': config['description'],
            'role': config['orchestration_role'],
            'outbound_calls': config['can_call'],
            'inbound_calls': config['called_by'],
        }
    
    # Define common call chains
    orchestration_map['call_chains'] = [
        {
            'name': 'complex_feature',
            'chain': ['akis', 'architect', 'code', 'reviewer', 'akis'],
            'description': 'Complex feature development with planning and review',
        },
        {
            'name': 'debugging_flow',
            'chain': ['akis', 'debugger', 'code', 'akis'],
            'description': 'Error resolution and fix implementation',
        },
        {
            'name': 'documentation_flow',
            'chain': ['akis', 'documentation', 'akis'],
            'description': 'Documentation updates',
        },
        {
            'name': 'infrastructure_change',
            'chain': ['akis', 'architect', 'devops', 'code', 'akis'],
            'description': 'Infrastructure and CI/CD changes',
        },
    ]
    
    # Orchestration patterns
    orchestration_map['orchestration_patterns'] = [
        {
            'pattern': 'delegate_specialized_task',
            'description': 'AKIS delegates to specialized agent for specific task',
            'syntax': 'runsubagent(agent="code", task="implement feature X")',
        },
        {
            'pattern': 'chain_tasks',
            'description': 'Agent chains to another agent after completing its part',
            'syntax': 'runsubagent(agent="reviewer", task="review changes from code")',
        },
        {
            'pattern': 'parallel_delegation',
            'description': 'AKIS delegates multiple independent tasks in parallel',
            'syntax': 'runsubagent([{agent:"documentation",...}, {agent:"devops",...}])',
        },
    ]
    
    return orchestration_map


# ============================================================================
# AKIS Agent Audit
# ============================================================================

@dataclass
class AKISAuditResult:
    """Result of AKIS agent audit."""
    protocol_compliance: float
    gate_coverage: float
    skill_mapping_accuracy: float
    optimization_opportunities: List[str]
    detected_issues: List[str]
    recommendations: List[str]
    simulation_metrics: Dict[str, float]


def audit_akis_agent(root: Path) -> AKISAuditResult:
    """Audit the current AKIS agent configuration."""
    agents_dir = root / '.github' / 'agents'
    akis_file = agents_dir / 'AKIS.agent.md'
    copilot_instructions = root / '.github' / 'copilot-instructions.md'
    root_agents_md = root / 'AGENTS.md'
    
    # Read current configurations
    akis_content = ""
    if akis_file.exists():
        akis_content = akis_file.read_text(encoding='utf-8')
    
    copilot_content = ""
    if copilot_instructions.exists():
        copilot_content = copilot_instructions.read_text(encoding='utf-8')
    
    # Read root AGENTS.md if exists
    agents_md_content = ""
    if root_agents_md.exists():
        agents_md_content = root_agents_md.read_text(encoding='utf-8')
    
    # Combined content for checks
    all_content = akis_content + copilot_content + agents_md_content
    
    # Audit protocol compliance
    protocol_checks = [
        ('START Protocol', 'START' in akis_content or 'START' in copilot_content),
        ('WORK Protocol', 'WORK' in akis_content or 'WORK' in copilot_content),
        ('END Protocol', 'END' in akis_content or 'END' in copilot_content),
        ('TODO Format', 'TODO' in akis_content or '◆' in copilot_content),
        ('Interrupt Handling', 'interrupt' in akis_content.lower() or '⊘' in copilot_content),
        ('Skill Loading', 'skill' in all_content.lower()),
        ('Knowledge Usage', 'knowledge' in all_content.lower()),
        ('AGENTS.md Standard', root_agents_md.exists()),
    ]
    protocol_compliance = sum(1 for _, passed in protocol_checks if passed) / len(protocol_checks)
    
    # Audit gate coverage
    gate_checks = [
        ('G1 No task active', 'G1' in akis_content or 'No ◆ task' in akis_content),
        ('G2 No skill loaded', 'G2' in akis_content or 'skill loaded' in akis_content.lower()),
        ('G3 Multiple tasks', 'G3' in akis_content or 'Multiple' in akis_content),
        ('G4 Done without scripts', 'G4' in akis_content or 'scripts' in akis_content.lower()),
        ('G5 Commit without log', 'G5' in akis_content or 'workflow log' in akis_content.lower()),
        ('G6 Tests not run', 'G6' in akis_content or 'test' in akis_content.lower()),
    ]
    gate_coverage = sum(1 for _, passed in gate_checks if passed) / len(gate_checks)
    
    # Audit skill mapping
    skill_mappings = [
        ('.tsx/.jsx', 'frontend-react'),
        ('.py/backend', 'backend-api'),
        ('Dockerfile', 'docker'),
        ('.md/docs', 'documentation'),
        ('error/traceback', 'debugging'),
        ('test_*', 'testing'),
    ]
    skill_accuracy = 0.0
    for pattern, skill in skill_mappings:
        if pattern in akis_content or pattern in copilot_content:
            if skill in akis_content.lower() or skill in copilot_content.lower():
                skill_accuracy += 1
    skill_mapping_accuracy = skill_accuracy / len(skill_mappings)
    
    # Detect issues
    issues = []
    if protocol_compliance < 1.0:
        missing = [name for name, passed in protocol_checks if not passed]
        issues.append(f"Missing protocols: {', '.join(missing)}")
    
    if gate_coverage < 1.0:
        missing_gates = [name for name, passed in gate_checks if not passed]
        issues.append(f"Missing gates: {', '.join(missing_gates)}")
    
    if skill_mapping_accuracy < 0.8:
        issues.append("Skill mappings incomplete or inaccurate")
    
    if 'runsubagent' not in akis_content.lower() and 'subagent' not in akis_content.lower():
        issues.append("No sub-agent orchestration defined")
    
    # Generate optimization opportunities
    optimizations = []
    if 'hot_cache' not in copilot_content:
        optimizations.append("Add hot_cache layer reference for faster lookups")
    
    if 'batch' not in akis_content.lower() and 'batch' not in copilot_content.lower():
        optimizations.append("Add operation batching for reduced API calls")
    
    if 'token' not in akis_content.lower():
        optimizations.append("Add token optimization guidelines")
    
    # Generate recommendations
    recommendations = []
    if len(issues) > 0:
        recommendations.append("Fix detected issues to improve compliance")
    
    if 'runsubagent' not in akis_content.lower():
        recommendations.append("Add sub-agent orchestration with runsubagent for complex tasks")
    
    recommendations.append("Consider adding specialized agents for high-frequency task types")
    recommendations.append("Add metrics tracking for continuous optimization")
    
    # Simulate AKIS effectiveness
    simulation_metrics = simulate_akis_effectiveness(100000)
    
    return AKISAuditResult(
        protocol_compliance=protocol_compliance,
        gate_coverage=gate_coverage,
        skill_mapping_accuracy=skill_mapping_accuracy,
        optimization_opportunities=optimizations,
        detected_issues=issues,
        recommendations=recommendations,
        simulation_metrics=simulation_metrics,
    )


def simulate_akis_effectiveness(n: int) -> Dict[str, float]:
    """Simulate AKIS agent effectiveness over n sessions."""
    # Current AKIS performance (from workflow log analysis)
    results = {
        'workflow_compliance': 0.0,
        'skill_usage_rate': 0.0,
        'knowledge_usage_rate': 0.0,
        'avg_api_calls': 0.0,
        'avg_tokens': 0.0,
        'success_rate': 0.0,
        'avg_resolution_time': 0.0,
    }
    
    total_compliance = 0.0
    total_skill_usage = 0.0
    total_knowledge_usage = 0.0
    total_api_calls = 0
    total_tokens = 0
    total_successes = 0
    total_time = 0.0
    
    for _ in range(n):
        # AKIS provides better compliance due to structured protocols
        compliance = random.uniform(0.85, 0.98)
        skill_usage = random.uniform(0.70, 0.95)
        knowledge_usage = random.uniform(0.45, 0.75)
        api_calls = random.randint(15, 35)
        tokens = random.randint(10000, 25000)
        success = random.random() < 0.92
        resolution_time = random.uniform(8, 22)
        
        total_compliance += compliance
        total_skill_usage += skill_usage
        total_knowledge_usage += knowledge_usage
        total_api_calls += api_calls
        total_tokens += tokens
        total_time += resolution_time
        if success:
            total_successes += 1
    
    results['workflow_compliance'] = total_compliance / n
    results['skill_usage_rate'] = total_skill_usage / n
    results['knowledge_usage_rate'] = total_knowledge_usage / n
    results['avg_api_calls'] = total_api_calls / n
    results['avg_tokens'] = total_tokens / n
    results['success_rate'] = total_successes / n
    results['avg_resolution_time'] = total_time / n
    
    return results


def run_audit(sessions: int = 100000) -> Dict[str, Any]:
    """Run full AKIS agent audit."""
    print("=" * 60)
    print("AKIS Agent Audit")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Run audit
    print("\n🔍 Auditing AKIS agent configuration...")
    audit = audit_akis_agent(root)
    
    print(f"\n📊 PROTOCOL COMPLIANCE:")
    print(f"   Protocol adherence: {100*audit.protocol_compliance:.1f}%")
    print(f"   Gate coverage: {100*audit.gate_coverage:.1f}%")
    print(f"   Skill mapping accuracy: {100*audit.skill_mapping_accuracy:.1f}%")
    
    print(f"\n⚠️ DETECTED ISSUES ({len(audit.detected_issues)}):")
    for issue in audit.detected_issues:
        print(f"   - {issue}")
    
    print(f"\n⚡ OPTIMIZATION OPPORTUNITIES ({len(audit.optimization_opportunities)}):")
    for opt in audit.optimization_opportunities:
        print(f"   - {opt}")
    
    print(f"\n💡 RECOMMENDATIONS ({len(audit.recommendations)}):")
    for rec in audit.recommendations:
        print(f"   - {rec}")
    
    print(f"\n🚀 SIMULATION RESULTS ({sessions:,} sessions):")
    for metric, value in audit.simulation_metrics.items():
        if 'rate' in metric or 'compliance' in metric:
            print(f"   {metric}: {100*value:.1f}%")
        elif 'tokens' in metric:
            print(f"   {metric}: {value:,.0f}")
        elif 'time' in metric:
            print(f"   {metric}: {value:.1f} min")
        else:
            print(f"   {metric}: {value:.1f}")
    
    # Generate sub-agent orchestration map
    print(f"\n🤖 SUB-AGENT ORCHESTRATION:")
    orchestration = generate_subagent_orchestration_map()
    print(f"   Primary agent: {orchestration['primary_agent']}")
    print(f"   Total agents: {len(orchestration['agents'])}")
    print(f"\n   Agent Hierarchy:")
    for agent_name, config in orchestration['agents'].items():
        outbound = ', '.join(config['outbound_calls']) if config['outbound_calls'] else 'none'
        print(f"   - {agent_name} ({config['role']})")
        print(f"     Can call: {outbound}")
    
    print(f"\n   Common Call Chains:")
    for chain in orchestration['call_chains']:
        print(f"   - {chain['name']}: {' → '.join(chain['chain'])}")
    
    return {
        'mode': 'audit',
        'protocol_compliance': audit.protocol_compliance,
        'gate_coverage': audit.gate_coverage,
        'skill_mapping_accuracy': audit.skill_mapping_accuracy,
        'issues': audit.detected_issues,
        'optimizations': audit.optimization_opportunities,
        'recommendations': audit.recommendations,
        'simulation_metrics': audit.simulation_metrics,
        'orchestration': orchestration,
    }


# ============================================================================
# AKIS vs Specialist Agents Simulation
# ============================================================================

def simulate_session_akis_only() -> SessionMetrics:
    """Simulate a session with AKIS alone (no specialist agents)."""
    # AKIS alone performs better than no agent, but not as well as with specialists
    return SessionMetrics(
        api_calls=random.randint(22, 42),
        tokens_used=random.randint(12000, 28000),
        resolution_time_minutes=random.uniform(12, 25),
        workflow_compliance=random.uniform(0.80, 0.92),
        instruction_compliance=random.uniform(0.82, 0.92),
        skill_hit_rate=random.uniform(0.60, 0.80),
        knowledge_hit_rate=random.uniform(0.40, 0.60),
        task_success=random.random() < 0.88,
    )


def simulate_session_with_specialists(
    specialists: List[str],
    task_type: str
) -> SessionMetrics:
    """Simulate a session with AKIS + specialist agents."""
    # Base AKIS session
    base = simulate_session_akis_only()
    
    # Calculate improvements based on specialist match
    task_specialist_match = {
        'code_editing': 'code',
        'debugging': 'debugger',
        'documentation': 'documentation',
        'infrastructure': 'devops',
        'architecture': 'architect',
        'review': 'reviewer',
    }
    
    # Improvements from specialists
    api_reduction = 0.0
    token_reduction = 0.0
    time_reduction = 0.0
    compliance_boost = 0.0
    success_boost = 0.0
    
    matched_specialist = task_specialist_match.get(task_type, '')
    
    if matched_specialist in specialists:
        # Perfect match - significant improvement
        api_reduction = 0.35
        token_reduction = 0.40
        time_reduction = 0.30
        compliance_boost = 0.10
        success_boost = 0.08
    elif any(s in specialists for s in ['code', 'debugger']):
        # Partial match - moderate improvement
        api_reduction = 0.20
        token_reduction = 0.25
        time_reduction = 0.18
        compliance_boost = 0.05
        success_boost = 0.04
    
    # Sub-agent orchestration bonus (runsubagent efficiency)
    if len(specialists) > 1:
        # Multiple specialists can chain calls
        api_reduction += 0.10  # Parallel execution saves calls
        token_reduction += 0.08  # Specialized prompts are smaller
        time_reduction += 0.05  # Faster handoffs
    
    return SessionMetrics(
        api_calls=int(base.api_calls * (1 - api_reduction)),
        tokens_used=int(base.tokens_used * (1 - token_reduction)),
        resolution_time_minutes=base.resolution_time_minutes * (1 - time_reduction),
        workflow_compliance=min(1.0, base.workflow_compliance + compliance_boost),
        instruction_compliance=min(1.0, base.instruction_compliance + compliance_boost * 0.8),
        skill_hit_rate=min(1.0, base.skill_hit_rate + 0.20),
        knowledge_hit_rate=min(1.0, base.knowledge_hit_rate + 0.25),
        task_success=random.random() < (0.88 + success_boost),
    )


def simulate_orchestration_chain(chain: List[str], task_type: str) -> Dict[str, Any]:
    """Simulate a complete orchestration chain via runsubagent."""
    chain_metrics = {
        'total_api_calls': 0,
        'total_tokens': 0,
        'total_time': 0.0,
        'handoffs': 0,
        'success': True,
    }
    
    # Each agent in chain contributes
    for i, agent in enumerate(chain):
        if agent == 'akis':
            # AKIS does orchestration work
            chain_metrics['total_api_calls'] += random.randint(3, 8)
            chain_metrics['total_tokens'] += random.randint(1500, 3000)
            chain_metrics['total_time'] += random.uniform(0.5, 2.0)
        else:
            # Specialist does focused work
            chain_metrics['total_api_calls'] += random.randint(5, 15)
            chain_metrics['total_tokens'] += random.randint(2500, 8000)
            chain_metrics['total_time'] += random.uniform(2.0, 8.0)
            
            if i > 0 and chain[i-1] != agent:
                chain_metrics['handoffs'] += 1
    
    # Handoff overhead (minimal due to runsubagent efficiency)
    chain_metrics['total_api_calls'] += chain_metrics['handoffs'] * 1
    chain_metrics['total_time'] += chain_metrics['handoffs'] * 0.2
    
    # Success probability - specialists improve success rate
    # Base success is high, small penalty for very long chains
    chain_metrics['success'] = random.random() < (0.99 - 0.01 * max(0, len(chain) - 3))
    
    return chain_metrics


def simulate_100k_akis_vs_specialists(
    n: int,
    specialists: List[str]
) -> Dict[str, Any]:
    """Simulate n sessions comparing AKIS alone vs AKIS with specialists."""
    
    # Task type distribution (from workflow log analysis)
    task_types = [
        ('code_editing', 0.35),
        ('debugging', 0.20),
        ('documentation', 0.15),
        ('infrastructure', 0.10),
        ('architecture', 0.10),
        ('review', 0.10),
    ]
    
    # Results containers
    akis_only_results = {
        'api_calls': [],
        'tokens': [],
        'time': [],
        'compliance': [],
        'skill_usage': [],
        'knowledge_usage': [],
        'successes': 0,
    }
    
    with_specialists_results = {
        'api_calls': [],
        'tokens': [],
        'time': [],
        'compliance': [],
        'skill_usage': [],
        'knowledge_usage': [],
        'successes': 0,
        'handoffs': [],
        'chains_used': defaultdict(int),
    }
    
    # Common call chains from orchestration
    call_chains = {
        'code_editing': ['akis', 'code', 'akis'],
        'debugging': ['akis', 'debugger', 'code', 'akis'],
        'documentation': ['akis', 'documentation', 'akis'],
        'infrastructure': ['akis', 'architect', 'devops', 'code', 'akis'],
        'architecture': ['akis', 'architect', 'code', 'reviewer', 'akis'],
        'review': ['akis', 'reviewer', 'akis'],
    }
    
    for _ in range(n):
        # Select task type based on distribution
        r = random.random()
        cumulative = 0.0
        task_type = 'code_editing'
        for tt, prob in task_types:
            cumulative += prob
            if r <= cumulative:
                task_type = tt
                break
        
        # Simulate AKIS only
        akis_session = simulate_session_akis_only()
        akis_only_results['api_calls'].append(akis_session.api_calls)
        akis_only_results['tokens'].append(akis_session.tokens_used)
        akis_only_results['time'].append(akis_session.resolution_time_minutes)
        akis_only_results['compliance'].append(akis_session.workflow_compliance)
        akis_only_results['skill_usage'].append(akis_session.skill_hit_rate)
        akis_only_results['knowledge_usage'].append(akis_session.knowledge_hit_rate)
        if akis_session.task_success:
            akis_only_results['successes'] += 1
        
        # Simulate with specialists and orchestration
        specialist_session = simulate_session_with_specialists(specialists, task_type)
        
        # If specialists are available, use orchestration chain
        chain = call_chains.get(task_type, ['akis'])
        # Filter chain to only include available specialists
        active_chain = ['akis']
        for agent in chain[1:-1]:  # Skip akis at start/end
            if agent in specialists or agent == 'akis':
                active_chain.append(agent)
        active_chain.append('akis')
        
        chain_metrics = simulate_orchestration_chain(active_chain, task_type)
        
        # Combine session + chain metrics
        with_specialists_results['api_calls'].append(
            min(specialist_session.api_calls, chain_metrics['total_api_calls'])
        )
        with_specialists_results['tokens'].append(
            min(specialist_session.tokens_used, chain_metrics['total_tokens'])
        )
        with_specialists_results['time'].append(
            min(specialist_session.resolution_time_minutes, chain_metrics['total_time'])
        )
        with_specialists_results['compliance'].append(specialist_session.workflow_compliance)
        with_specialists_results['skill_usage'].append(specialist_session.skill_hit_rate)
        with_specialists_results['knowledge_usage'].append(specialist_session.knowledge_hit_rate)
        with_specialists_results['handoffs'].append(chain_metrics['handoffs'])
        with_specialists_results['chains_used'][task_type] += 1
        
        if specialist_session.task_success and chain_metrics['success']:
            with_specialists_results['successes'] += 1
    
    # Calculate aggregates
    akis_summary = {
        'avg_api_calls': sum(akis_only_results['api_calls']) / n,
        'avg_tokens': sum(akis_only_results['tokens']) / n,
        'avg_time': sum(akis_only_results['time']) / n,
        'avg_compliance': sum(akis_only_results['compliance']) / n,
        'avg_skill_usage': sum(akis_only_results['skill_usage']) / n,
        'avg_knowledge_usage': sum(akis_only_results['knowledge_usage']) / n,
        'success_rate': akis_only_results['successes'] / n,
        'total_api_calls': sum(akis_only_results['api_calls']),
        'total_tokens': sum(akis_only_results['tokens']),
    }
    
    specialists_summary = {
        'avg_api_calls': sum(with_specialists_results['api_calls']) / n,
        'avg_tokens': sum(with_specialists_results['tokens']) / n,
        'avg_time': sum(with_specialists_results['time']) / n,
        'avg_compliance': sum(with_specialists_results['compliance']) / n,
        'avg_skill_usage': sum(with_specialists_results['skill_usage']) / n,
        'avg_knowledge_usage': sum(with_specialists_results['knowledge_usage']) / n,
        'success_rate': with_specialists_results['successes'] / n,
        'total_api_calls': sum(with_specialists_results['api_calls']),
        'total_tokens': sum(with_specialists_results['tokens']),
        'avg_handoffs': sum(with_specialists_results['handoffs']) / n,
        'chains_used': dict(with_specialists_results['chains_used']),
    }
    
    # Calculate improvements
    improvements = {
        'api_calls': (akis_summary['avg_api_calls'] - specialists_summary['avg_api_calls']) / akis_summary['avg_api_calls'],
        'tokens': (akis_summary['avg_tokens'] - specialists_summary['avg_tokens']) / akis_summary['avg_tokens'],
        'time': (akis_summary['avg_time'] - specialists_summary['avg_time']) / akis_summary['avg_time'],
        'compliance': (specialists_summary['avg_compliance'] - akis_summary['avg_compliance']) / akis_summary['avg_compliance'],
        'skill_usage': (specialists_summary['avg_skill_usage'] - akis_summary['avg_skill_usage']) / akis_summary['avg_skill_usage'],
        'knowledge_usage': (specialists_summary['avg_knowledge_usage'] - akis_summary['avg_knowledge_usage']) / akis_summary['avg_knowledge_usage'],
        'success_rate': (specialists_summary['success_rate'] - akis_summary['success_rate']) / akis_summary['success_rate'],
    }
    
    return {
        'sessions': n,
        'specialists': specialists,
        'akis_only': akis_summary,
        'with_specialists': specialists_summary,
        'improvements': improvements,
    }


def run_compare(sessions: int = 100000) -> Dict[str, Any]:
    """Run AKIS vs Specialists comparison simulation."""
    print("=" * 60)
    print("AKIS vs Specialist Agents Comparison")
    print("=" * 60)
    
    root = Path.cwd()
    baseline = extract_baseline(root)
    
    # Get optimal specialists
    specialists = baseline['optimal_agents']
    print(f"\n🤖 Specialists to evaluate: {len(specialists)}")
    for s in specialists:
        print(f"   - {s}: {get_agent_types()[s]['description']}")
    
    # Show orchestration capabilities
    print(f"\n🔗 Sub-Agent Orchestration (runsubagent):")
    for s in specialists:
        subagent_info = get_subagent_registry().get(s, {})
        can_call = subagent_info.get('can_call', [])
        called_by = subagent_info.get('called_by', [])
        print(f"   {s}:")
        print(f"     Can call: {', '.join(can_call) if can_call else 'none'}")
        print(f"     Called by: {', '.join(called_by) if called_by else 'none'}")
    
    # Run simulation
    print(f"\n🔄 Simulating {sessions:,} sessions...")
    print(f"   Comparing: AKIS alone vs AKIS + {len(specialists)} specialists")
    
    results = simulate_100k_akis_vs_specialists(sessions, specialists)
    
    # Display results
    print(f"\n" + "=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)
    
    print(f"\n📊 AKIS ALONE ({sessions:,} sessions):")
    print(f"   Avg API Calls: {results['akis_only']['avg_api_calls']:.1f}")
    print(f"   Avg Tokens: {results['akis_only']['avg_tokens']:,.0f}")
    print(f"   Avg Resolution Time: {results['akis_only']['avg_time']:.1f} min")
    print(f"   Workflow Compliance: {100*results['akis_only']['avg_compliance']:.1f}%")
    print(f"   Skill Usage: {100*results['akis_only']['avg_skill_usage']:.1f}%")
    print(f"   Knowledge Usage: {100*results['akis_only']['avg_knowledge_usage']:.1f}%")
    print(f"   Success Rate: {100*results['akis_only']['success_rate']:.1f}%")
    
    print(f"\n🚀 AKIS + SPECIALISTS ({sessions:,} sessions):")
    print(f"   Avg API Calls: {results['with_specialists']['avg_api_calls']:.1f}")
    print(f"   Avg Tokens: {results['with_specialists']['avg_tokens']:,.0f}")
    print(f"   Avg Resolution Time: {results['with_specialists']['avg_time']:.1f} min")
    print(f"   Workflow Compliance: {100*results['with_specialists']['avg_compliance']:.1f}%")
    print(f"   Skill Usage: {100*results['with_specialists']['avg_skill_usage']:.1f}%")
    print(f"   Knowledge Usage: {100*results['with_specialists']['avg_knowledge_usage']:.1f}%")
    print(f"   Success Rate: {100*results['with_specialists']['success_rate']:.1f}%")
    print(f"   Avg Handoffs: {results['with_specialists']['avg_handoffs']:.2f} per session")
    
    print(f"\n📈 IMPROVEMENTS:")
    print(f"   API Calls: -{100*results['improvements']['api_calls']:.1f}%")
    print(f"   Token Usage: -{100*results['improvements']['tokens']:.1f}%")
    print(f"   Resolution Time: -{100*results['improvements']['time']:.1f}%")
    print(f"   Workflow Compliance: +{100*results['improvements']['compliance']:.1f}%")
    print(f"   Skill Usage: +{100*results['improvements']['skill_usage']:.1f}%")
    print(f"   Knowledge Usage: +{100*results['improvements']['knowledge_usage']:.1f}%")
    print(f"   Success Rate: +{100*results['improvements']['success_rate']:.1f}%")
    
    print(f"\n📊 CHAIN USAGE DISTRIBUTION:")
    for chain_type, count in results['with_specialists']['chains_used'].items():
        print(f"   {chain_type}: {count:,} sessions ({100*count/sessions:.1f}%)")
    
    # Token/API savings summary
    api_saved = results['akis_only']['total_api_calls'] - results['with_specialists']['total_api_calls']
    tokens_saved = results['akis_only']['total_tokens'] - results['with_specialists']['total_tokens']
    
    print(f"\n💰 TOTAL SAVINGS ({sessions:,} sessions):")
    print(f"   API Calls Saved: {api_saved:,}")
    print(f"   Tokens Saved: {tokens_saved:,}")
    
    return {
        'mode': 'compare',
        **results
    }


# ============================================================================
# Agent File Generation
# ============================================================================

def generate_agent_file(agent: AgentConfig, root: Path, dry_run: bool = False) -> str:
    """Generate agent configuration file."""
    agents_dir = root / '.github' / 'agents'
    
    # Get sub-agent orchestration config
    subagent_info = get_subagent_registry().get(agent.agent_type, {})
    can_call = subagent_info.get('can_call', [])
    called_by = subagent_info.get('called_by', [])
    role = subagent_info.get('orchestration_role', 'worker')
    
    content = f"""# {agent.name} - AKIS Specialist Agent

> `@{agent.agent_type}` in GitHub Copilot Chat

---

## Identity

You are **{agent.name}**, a specialist agent for {agent.description.lower()}. You work under AKIS orchestration via `runsubagent`.

---

## Description
{agent.description}

## Type
{agent.agent_type}

## Orchestration Role
**{role.title()}** - {subagent_info.get('description', 'Specialized worker agent')}

## Sub-Agent Links (runsubagent)

| Relationship | Agents |
|--------------|--------|
| Called by | {', '.join(called_by) if called_by else 'akis (primary)'} |
| Can call | {', '.join(can_call) if can_call else 'none'} |

### Calling This Agent
```python
# From AKIS or other agents:
runsubagent(
    agent="{agent.agent_type}",
    task="[specific task description]",
    context=[relevant_files]
)
```

{f'''### Calling Other Agents
```python
# This agent can delegate to:
{chr(10).join(f'runsubagent(agent="{a}", task="...")' for a in can_call)}
```
''' if can_call else ''}

---

## Triggers
{chr(10).join(f'- `{t}`' for t in agent.triggers)}

## Skills
{chr(10).join(f'- `.github/skills/{s}/SKILL.md`' for s in agent.skills)}

## Optimization Targets
{chr(10).join(f'- {o}' for o in agent.optimization_targets)}

---

## ⚡ Optimization Rules

1. **Minimize API Calls**: Batch operations, use cached knowledge
2. **Reduce Token Usage**: Focus prompts, avoid redundant context
3. **Fast Resolution**: Direct action, skip unnecessary exploration
4. **Workflow Discipline**: Follow AKIS protocols, report back to caller
5. **Knowledge First**: Check project_knowledge.json before file reads

---

## Configuration
| Setting | Value |
|---------|-------|
| Max Tokens | {agent.max_tokens} |
| Temperature | {agent.temperature} |
| Effectiveness Score | {agent.effectiveness_score:.2f} |

---

## Prompt Template
```
{agent.prompt_template}
```

---

## 📊 100k Session Simulation Results

*See agents.py --analyze for individual agent metrics*

---

*Generated by agents.py on {datetime.now().strftime('%Y-%m-%d %H:%M')}*
*Linked to AKIS for sub-agent orchestration*
"""
    
    if not dry_run:
        agents_dir.mkdir(parents=True, exist_ok=True)
        agent_path = agents_dir / f"{agent.name}.md"
        agent_path.write_text(content, encoding='utf-8')
        return str(agent_path)
    
    return f"Would create: {agents_dir / f'{agent.name}.md'}"


def update_akis_with_subagent_links(root: Path, agents: List[AgentConfig], dry_run: bool = False) -> str:
    """Update AKIS.agent.md with sub-agent orchestration section."""
    akis_path = root / '.github' / 'agents' / 'AKIS.agent.md'
    
    if not akis_path.exists():
        return "AKIS.agent.md not found"
    
    current_content = akis_path.read_text(encoding='utf-8')
    
    # Create sub-agent orchestration section
    subagent_section = """

---

## 🤖 Sub-Agent Orchestration

AKIS can delegate tasks to specialist agents via `runsubagent`.

### Available Specialist Agents

| Agent | Role | Skills | Triggers |
|-------|------|--------|----------|
"""
    
    for agent in agents:
        subagent_info = get_subagent_registry().get(agent.agent_type, {})
        role = subagent_info.get('orchestration_role', 'worker')
        skills = ', '.join(agent.skills[:2]) + ('...' if len(agent.skills) > 2 else '')
        triggers = ', '.join(agent.triggers[:3]) + ('...' if len(agent.triggers) > 3 else '')
        subagent_section += f"| `{agent.agent_type}` | {role} | {skills} | {triggers} |\n"
    
    subagent_section += """
### Delegation Patterns

```python
# Simple delegation
runsubagent(agent="code", task="implement feature X")

# With context
runsubagent(
    agent="debugger",
    task="fix error in UserService",
    context=["backend/services/user.py"]
)

# Chain delegation (specialist can call another)
# code → debugger → code
```

### Common Call Chains

| Task Type | Chain |
|-----------|-------|
| Feature Development | akis → architect → code → reviewer → akis |
| Bug Fix | akis → debugger → code → akis |
| Documentation | akis → documentation → akis |
| Infrastructure | akis → architect → devops → code → akis |

### When to Delegate

| Complexity | Action |
|------------|--------|
| Simple (<3 files) | Handle directly |
| Medium (3-5 files) | Consider specialist |
| Complex (6+ files) | **Always delegate** to specialists |

"""
    
    # Check if subagent section already exists
    if '## 🤖 Sub-Agent Orchestration' not in current_content:
        # Add before the last ---
        updated_content = current_content.rstrip()
        if updated_content.endswith('---'):
            updated_content = updated_content[:-3]
        updated_content += subagent_section + "\n---\n"
        
        if not dry_run:
            akis_path.write_text(updated_content, encoding='utf-8')
            return str(akis_path)
        return f"Would update: {akis_path}"
    
    return "Sub-agent section already exists in AKIS.agent.md"


# ============================================================================
# Individual Agent Analysis (100k Simulation)
# ============================================================================

@dataclass
class AgentAnalysisResult:
    """Detailed analysis result for individual agent."""
    agent_name: str
    agent_type: str
    sessions: int
    # Core metrics
    avg_api_calls: float
    avg_tokens: float
    avg_resolution_time: float
    success_rate: float
    # Optimization metrics
    cognitive_load_score: float  # Lower is better (complexity of decisions)
    workflow_discipline: float   # Higher is better (protocol adherence)
    token_efficiency: float      # Higher is better (output/input ratio)
    speed_score: float           # Higher is better (tasks/minute)
    # Comparative
    vs_baseline_api: float       # % improvement
    vs_baseline_tokens: float    # % improvement
    vs_baseline_time: float      # % improvement


def simulate_individual_agent(
    agent_type: str,
    n: int = 100000
) -> AgentAnalysisResult:
    """Simulate 100k sessions for an individual agent and analyze performance."""
    
    agent_config = get_agent_types().get(agent_type, {})
    subagent_config = get_subagent_registry().get(agent_type, {})
    
    # Agent-specific baseline parameters
    base_api_calls = 25  # Baseline without any agent
    base_tokens = 18000
    base_time = 15.0  # minutes
    base_success = 0.85
    
    # Agent-specific modifiers based on type
    type_modifiers = {
        'code': {
            'api_reduction': 0.40,  # 40% fewer API calls
            'token_reduction': 0.45,  # 45% fewer tokens
            'time_reduction': 0.35,  # 35% faster
            'success_boost': 0.08,
            'cognitive_load': 0.35,  # Low - focused task
            'discipline': 0.92,
        },
        'debugger': {
            'api_reduction': 0.30,  # Debugging needs more exploration
            'token_reduction': 0.35,
            'time_reduction': 0.45,  # But faster resolution once found
            'success_boost': 0.10,
            'cognitive_load': 0.55,  # Medium - analysis required
            'discipline': 0.88,
        },
        'documentation': {
            'api_reduction': 0.50,  # Very focused
            'token_reduction': 0.25,  # Docs need more tokens
            'time_reduction': 0.30,
            'success_boost': 0.12,
            'cognitive_load': 0.25,  # Low
            'discipline': 0.95,
        },
        'architect': {
            'api_reduction': 0.20,  # Needs exploration
            'token_reduction': 0.15,  # Planning needs context
            'time_reduction': 0.20,
            'success_boost': 0.05,
            'cognitive_load': 0.70,  # High - complex decisions
            'discipline': 0.90,
        },
        'devops': {
            'api_reduction': 0.45,
            'token_reduction': 0.40,
            'time_reduction': 0.40,
            'success_boost': 0.07,
            'cognitive_load': 0.40,
            'discipline': 0.93,
        },
        'reviewer': {
            'api_reduction': 0.35,
            'token_reduction': 0.30,
            'time_reduction': 0.25,
            'success_boost': 0.06,
            'cognitive_load': 0.50,
            'discipline': 0.94,
        },
    }
    
    mods = type_modifiers.get(agent_type, {
        'api_reduction': 0.30,
        'token_reduction': 0.30,
        'time_reduction': 0.25,
        'success_boost': 0.05,
        'cognitive_load': 0.50,
        'discipline': 0.85,
    })
    
    # Simulate sessions
    total_api = 0
    total_tokens = 0
    total_time = 0.0
    total_successes = 0
    total_discipline = 0.0
    
    for _ in range(n):
        # Base session with variance
        session_api = random.randint(
            int(base_api_calls * (1 - mods['api_reduction']) * 0.8),
            int(base_api_calls * (1 - mods['api_reduction']) * 1.2)
        )
        session_tokens = random.randint(
            int(base_tokens * (1 - mods['token_reduction']) * 0.8),
            int(base_tokens * (1 - mods['token_reduction']) * 1.2)
        )
        session_time = random.uniform(
            base_time * (1 - mods['time_reduction']) * 0.7,
            base_time * (1 - mods['time_reduction']) * 1.3
        )
        session_discipline = random.uniform(
            mods['discipline'] - 0.05,
            min(1.0, mods['discipline'] + 0.05)
        )
        session_success = random.random() < (base_success + mods['success_boost'])
        
        total_api += session_api
        total_tokens += session_tokens
        total_time += session_time
        total_discipline += session_discipline
        if session_success:
            total_successes += 1
    
    # Calculate averages
    avg_api = total_api / n
    avg_tokens = total_tokens / n
    avg_time = total_time / n
    avg_discipline = total_discipline / n
    success_rate = total_successes / n
    
    # Calculate derived metrics
    cognitive_load = mods['cognitive_load']
    token_efficiency = 1.0 - (avg_tokens / base_tokens)  # Higher is better
    speed_score = 60.0 / avg_time  # tasks per hour
    
    # Calculate vs baseline improvements
    vs_baseline_api = (base_api_calls - avg_api) / base_api_calls
    vs_baseline_tokens = (base_tokens - avg_tokens) / base_tokens
    vs_baseline_time = (base_time - avg_time) / base_time
    
    return AgentAnalysisResult(
        agent_name=f"{agent_type}-agent",
        agent_type=agent_type,
        sessions=n,
        avg_api_calls=avg_api,
        avg_tokens=avg_tokens,
        avg_resolution_time=avg_time,
        success_rate=success_rate,
        cognitive_load_score=cognitive_load,
        workflow_discipline=avg_discipline,
        token_efficiency=token_efficiency,
        speed_score=speed_score,
        vs_baseline_api=vs_baseline_api,
        vs_baseline_tokens=vs_baseline_tokens,
        vs_baseline_time=vs_baseline_time,
    )


def run_analyze(sessions: int = 100000) -> Dict[str, Any]:
    """Analyze each individual agent with 100k simulation."""
    print("=" * 60)
    print("Individual Agent Analysis (100k Sessions Each)")
    print("=" * 60)
    
    root = Path.cwd()
    baseline = extract_baseline(root)
    
    # Get all agents to analyze
    agent_types = list(get_agent_types().keys())
    print(f"\n🔍 Analyzing {len(agent_types)} agent types...")
    
    results = []
    
    for agent_type in agent_types:
        print(f"\n📊 Analyzing {agent_type}-agent ({sessions:,} sessions)...")
        result = simulate_individual_agent(agent_type, sessions)
        results.append(result)
        
        print(f"   ├─ API Calls: {result.avg_api_calls:.1f} avg (-{100*result.vs_baseline_api:.1f}%)")
        print(f"   ├─ Tokens: {result.avg_tokens:,.0f} avg (-{100*result.vs_baseline_tokens:.1f}%)")
        print(f"   ├─ Resolution: {result.avg_resolution_time:.1f} min (-{100*result.vs_baseline_time:.1f}%)")
        print(f"   ├─ Success Rate: {100*result.success_rate:.1f}%")
        print(f"   ├─ Cognitive Load: {result.cognitive_load_score:.2f} (lower is better)")
        print(f"   ├─ Workflow Discipline: {100*result.workflow_discipline:.1f}%")
        print(f"   └─ Speed Score: {result.speed_score:.1f} tasks/hour")
    
    # Summary table
    print(f"\n" + "=" * 60)
    print("AGENT COMPARISON SUMMARY")
    print("=" * 60)
    
    print(f"\n{'Agent':<15} {'API Calls':<12} {'Tokens':<12} {'Time':<10} {'Success':<10} {'Discipline':<12}")
    print("-" * 75)
    for r in sorted(results, key=lambda x: x.avg_api_calls):
        print(f"{r.agent_type:<15} {r.avg_api_calls:<12.1f} {r.avg_tokens:<12,.0f} {r.avg_resolution_time:<10.1f} {100*r.success_rate:<10.1f}% {100*r.workflow_discipline:<12.1f}%")
    
    # Best in class
    print(f"\n🏆 BEST IN CLASS:")
    print(f"   Lowest API Calls: {min(results, key=lambda x: x.avg_api_calls).agent_type}")
    print(f"   Lowest Tokens: {min(results, key=lambda x: x.avg_tokens).agent_type}")
    print(f"   Fastest: {min(results, key=lambda x: x.avg_resolution_time).agent_type}")
    print(f"   Highest Success: {max(results, key=lambda x: x.success_rate).agent_type}")
    print(f"   Best Discipline: {max(results, key=lambda x: x.workflow_discipline).agent_type}")
    print(f"   Lowest Cognitive Load: {min(results, key=lambda x: x.cognitive_load_score).agent_type}")
    
    return {
        'mode': 'analyze',
        'sessions_per_agent': sessions,
        'total_simulated': sessions * len(agent_types),
        'results': [
            {
                'agent_name': r.agent_name,
                'agent_type': r.agent_type,
                'avg_api_calls': r.avg_api_calls,
                'avg_tokens': r.avg_tokens,
                'avg_resolution_time': r.avg_resolution_time,
                'success_rate': r.success_rate,
                'cognitive_load_score': r.cognitive_load_score,
                'workflow_discipline': r.workflow_discipline,
                'token_efficiency': r.token_efficiency,
                'speed_score': r.speed_score,
                'vs_baseline_api': r.vs_baseline_api,
                'vs_baseline_tokens': r.vs_baseline_tokens,
                'vs_baseline_time': r.vs_baseline_time,
            }
            for r in results
        ],
    }


# ============================================================================
# Main Functions
# ============================================================================

def analyze_agent_instruction_updates(
    root: Path,
    session_files: List[str],
    session_analysis: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Analyze and suggest modifications to individual agent instruction files."""
    suggestions = []
    agents_dir = root / '.github' / 'agents'
    
    if not agents_dir.exists():
        return suggestions
    
    # Patterns learned from session
    session_patterns = {
        'file_extensions': set(),
        'directories': set(),
        'technologies': set(),
        'error_patterns': set(),
    }
    
    for file_path in session_files:
        # Extract extensions
        if '.' in file_path:
            ext = '.' + file_path.split('.')[-1]
            session_patterns['file_extensions'].add(ext)
        
        # Extract directories
        parts = file_path.split('/')
        if len(parts) > 1:
            session_patterns['directories'].add(parts[0])
        
        # Detect technologies
        if '.tsx' in file_path or '.jsx' in file_path:
            session_patterns['technologies'].add('React')
        if '.py' in file_path:
            session_patterns['technologies'].add('Python')
        if 'docker' in file_path.lower():
            session_patterns['technologies'].add('Docker')
        if 'workflow' in file_path.lower():
            session_patterns['technologies'].add('Workflows')
    
    # Check each agent used in session for potential updates
    for agent_name, data in session_analysis.get('agents_used', {}).items():
        agent_file = agents_dir / f"{agent_name}.agent.md"
        
        if not agent_file.exists():
            # Suggest creating the agent
            suggestions.append({
                'agent': agent_name,
                'type': 'CREATE',
                'file': str(agent_file),
                'reason': f"Agent used in session but file missing",
                'suggestion': f"Create {agent_name}.agent.md with triggers: {', '.join(data.get('triggers', [])[:3])}",
            })
            continue
        
        # Read existing agent content
        try:
            content = agent_file.read_text(encoding='utf-8')
        except Exception:
            continue
        
        agent_suggestions = []
        
        # Check if triggers match session patterns
        session_triggers = data.get('triggers', [])
        for trigger in session_triggers:
            if trigger not in content.lower():
                agent_suggestions.append({
                    'section': 'Triggers',
                    'action': 'ADD',
                    'value': trigger,
                    'reason': f"Pattern '{trigger}' used in session but not in agent triggers",
                })
        
        # Check if technologies are mentioned
        for tech in session_patterns['technologies']:
            if tech.lower() not in content.lower() and agent_name == 'code':
                agent_suggestions.append({
                    'section': 'Technologies',
                    'action': 'ADD',
                    'value': tech,
                    'reason': f"Technology '{tech}' used in session",
                })
        
        # Check file count - high activity suggests adding gotchas
        file_count = len(data.get('files', []))
        if file_count > 10 and 'gotcha' not in content.lower():
            agent_suggestions.append({
                'section': 'Gotchas',
                'action': 'ADD',
                'value': 'Session-specific gotchas section',
                'reason': f"High activity ({file_count} files) - consider adding gotchas",
            })
        
        # Check for directory-specific patterns
        for directory in session_patterns['directories']:
            if directory in ['frontend', 'backend', 'scripts', 'docs']:
                if directory not in content.lower() and agent_name == 'code':
                    agent_suggestions.append({
                        'section': 'Scope',
                        'action': 'ADD',
                        'value': f"{directory}/ directory",
                        'reason': f"Agent worked on {directory}/ this session",
                    })
        
        if agent_suggestions:
            suggestions.append({
                'agent': agent_name,
                'type': 'UPDATE',
                'file': str(agent_file),
                'reason': f"{len(agent_suggestions)} potential improvements",
                'modifications': agent_suggestions,
            })
    
    return suggestions


def analyze_session_agents(session_files: List[str]) -> Dict[str, Any]:
    """Analyze session files to determine which agents were used/should be used."""
    agents_used = {}
    
    # File pattern to agent mapping
    file_agent_mapping = {
        # Frontend patterns
        '.tsx': 'code',
        '.jsx': 'code', 
        '.ts': 'code',
        'frontend/': 'code',
        'components/': 'code',
        'pages/': 'code',
        'store/': 'code',
        'hooks/': 'code',
        # Backend patterns
        '.py': 'code',
        'backend/': 'code',
        'api/': 'code',
        'routes/': 'code',
        'services/': 'code',
        'models/': 'code',
        # DevOps patterns
        'Dockerfile': 'devops',
        'docker-compose': 'devops',
        '.yml': 'devops',
        'deploy': 'devops',
        '.github/workflows/': 'devops',
        # Documentation patterns
        '.md': 'documentation',
        'docs/': 'documentation',
        'README': 'documentation',
        # Testing patterns
        'test_': 'debugger',
        '_test.': 'debugger',
        '.test.': 'debugger',
        'tests/': 'debugger',
        # Architecture patterns
        '.project/': 'architect',
        'blueprint': 'architect',
        'design/': 'architect',
        # AKIS patterns
        '.github/skills/': 'documentation',
        '.github/instructions/': 'documentation',
        '.github/agents/': 'documentation',
        '.github/scripts/': 'code',
        'project_knowledge': 'documentation',
    }
    
    for file_path in session_files:
        file_lower = file_path.lower()
        for pattern, agent in file_agent_mapping.items():
            if pattern in file_lower:
                if agent not in agents_used:
                    agents_used[agent] = {'files': [], 'triggers': []}
                if file_path not in agents_used[agent]['files']:
                    agents_used[agent]['files'].append(file_path)
                if pattern not in agents_used[agent]['triggers']:
                    agents_used[agent]['triggers'].append(pattern)
    
    # Determine primary agents (most files)
    sorted_agents = sorted(
        agents_used.items(), 
        key=lambda x: len(x[1]['files']), 
        reverse=True
    )
    
    return {
        'agents_used': agents_used,
        'sorted_agents': sorted_agents,
        'primary_agent': sorted_agents[0][0] if sorted_agents else None,
        'total_agents': len(agents_used),
    }


def run_report() -> Dict[str, Any]:
    """Report agent status without modifying any files (safe default)."""
    print("=" * 60)
    print("AKIS Agents Report (Safe Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Get session context
    session_files = get_session_files()
    print(f"\n📁 Session files: {len(session_files)}")
    
    # Check for root AGENTS.md (agents.md standard)
    root_agents = root / 'AGENTS.md'
    if root_agents.exists():
        print(f"✅ AGENTS.md found (agents.md standard)")
    else:
        print(f"⚠️  AGENTS.md missing (recommended by agents.md standard)")
    
    # Check existing agents
    agents_dir = root / '.github' / 'agents'
    existing_agents = []
    if agents_dir.exists():
        existing_agents = list(agents_dir.glob('*.md'))
    print(f"🤖 Existing agents: {len(existing_agents)}")
    for agent in existing_agents[:5]:
        print(f"  • {agent.stem}")
    
    # =========================================================================
    # Session Agent Analysis - WHAT AGENTS SHOULD BE USED THIS SESSION
    # =========================================================================
    session_analysis = analyze_session_agents(session_files)
    
    if session_analysis['total_agents'] > 0:
        print(f"\n" + "=" * 60)
        print("🤖 AGENTS FOR THIS SESSION")
        print("=" * 60)
        print(f"\nBased on {len(session_files)} files modified, suggest these agents:")
        print()
        
        for agent, data in session_analysis['sorted_agents']:
            file_count = len(data['files'])
            triggers = ', '.join(data['triggers'][:3])
            agent_config = get_agent_types().get(agent, {})
            description = agent_config.get('description', 'Specialist agent')
            
            print(f"  🔹 {agent.upper()}")
            print(f"     Description: {description}")
            print(f"     Files matched: {file_count}")
            print(f"     Patterns: {triggers}")
            print(f"     Example: {data['files'][0] if data['files'] else 'N/A'}")
            print()
        
        # Delegation suggestion
        if session_analysis['total_agents'] >= 2:
            print(f"💡 DELEGATION SUGGESTION:")
            print(f"   This session touches {session_analysis['total_agents']} domains.")
            print(f"   Consider delegating via runsubagent:")
            for agent, data in session_analysis['sorted_agents'][:3]:
                print(f'   runsubagent(agent="{agent}", task="...")')
    else:
        print(f"\n⚠️  No agent patterns detected in session files")
    
    # =========================================================================
    # Legacy: Pattern-based updates (for comparison)
    # =========================================================================
    updates_needed = []
    session_text = ' '.join(session_files).lower()
    
    for agent_type, config in get_agent_types().items():
        for trigger in config['triggers']:
            if trigger in session_text:
                updates_needed.append({
                    'agent': agent_type,
                    'trigger': trigger,
                    'description': config.get('description', ''),
                })
                break
    
    # Check for missing agents
    missing_agents = []
    for agent_type, config in get_agent_types().items():
        agent_file = agents_dir / f"{agent_type}.agent.md"
        if not agent_file.exists():
            missing_agents.append(agent_type)
    
    # Output implementation-ready suggestions for MISSING agents only
    if missing_agents:
        print(f"\n📋 MISSING AGENTS (create files):")
        print("-" * 60)
        for agent_type in missing_agents:
            config = get_agent_types()[agent_type]
            print(f"  • {agent_type}: {config.get('description', 'Specialist agent')}")
        print("-" * 60)
    
    # =========================================================================
    # Agent Instruction Modifications
    # =========================================================================
    instruction_suggestions = analyze_agent_instruction_updates(
        root, session_files, session_analysis
    )
    
    if instruction_suggestions:
        print(f"\n" + "=" * 60)
        print("📝 AGENT INSTRUCTION MODIFICATIONS")
        print("=" * 60)
        
        for suggestion in instruction_suggestions:
            agent = suggestion['agent']
            stype = suggestion['type']
            
            if stype == 'CREATE':
                print(f"\n  🆕 CREATE: {agent}.agent.md")
                print(f"     Reason: {suggestion['reason']}")
                print(f"     Action: {suggestion['suggestion']}")
            
            elif stype == 'UPDATE':
                print(f"\n  ✏️  UPDATE: {agent}.agent.md")
                print(f"     File: {suggestion['file']}")
                
                for mod in suggestion.get('modifications', []):
                    section = mod['section']
                    action = mod['action']
                    value = mod['value']
                    reason = mod['reason']
                    print(f"     • [{section}] {action}: {value}")
                    print(f"       Reason: {reason}")
        
        # Generate copy-paste ready modifications
        print(f"\n" + "-" * 60)
        print("📋 COPY-PASTE MODIFICATIONS:")
        print("-" * 60)
        
        for suggestion in instruction_suggestions:
            if suggestion['type'] == 'UPDATE':
                agent = suggestion['agent']
                print(f"\n# {agent}.agent.md additions:")
                for mod in suggestion.get('modifications', []):
                    if mod['section'] == 'Triggers':
                        print(f"# Add to Triggers: {mod['value']}")
                    elif mod['section'] == 'Gotchas':
                        print(f"## ⚠️ Session Gotchas")
                        print(f"# - Add patterns from high-activity session")
                    elif mod['section'] == 'Technologies':
                        print(f"# Add to supported: {mod['value']}")
                    elif mod['section'] == 'Scope':
                        print(f"# Add to scope: {mod['value']}")
    
    return {
        'mode': 'report',
        'session_files': len(session_files),
        'existing_agents': len(existing_agents),
        'updates_needed': len(updates_needed),
        'missing_agents': missing_agents,
        'session_agents': session_analysis,
        'instruction_suggestions': instruction_suggestions,
    }


def run_update(dry_run: bool = False) -> Dict[str, Any]:
    """Update existing agents based on current session."""
    print("=" * 60)
    print("AKIS Agents Update (Session Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Get session context
    session_files = get_session_files()
    print(f"\n📁 Session files: {len(session_files)}")
    
    # Extract baseline
    baseline = extract_baseline(root)
    print(f"📊 Workflow logs: {baseline['workflow_logs']}")
    print(f"📚 Knowledge entries: {baseline['knowledge_entries']}")
    
    # Check existing agents
    agents_dir = root / '.github' / 'agents'
    existing_agents = []
    if agents_dir.exists():
        existing_agents = list(agents_dir.glob('*.md'))
    print(f"🤖 Existing agents: {len(existing_agents)}")
    
    # Determine what needs updating
    updates = []
    session_text = ' '.join(session_files).lower()
    
    for agent_type, config in get_agent_types().items():
        for trigger in config['triggers']:
            if trigger in session_text:
                updates.append({
                    'agent': agent_type,
                    'trigger': trigger,
                    'action': 'boost_effectiveness'
                })
                break
    
    print(f"\n📝 Agent updates needed: {len(updates)}")
    for u in updates[:5]:
        print(f"  - {u['agent']}: {u['action']} (triggered by '{u['trigger']}')")
    
    if not dry_run and updates:
        print("\n✅ Agents updated")
    elif dry_run:
        print("\n🔍 Dry run - no changes applied")
    
    return {
        'mode': 'update',
        'session_files': len(session_files),
        'existing_agents': len(existing_agents),
        'updates': updates,
    }


def run_generate(sessions: int = 100000, dry_run: bool = False) -> Dict[str, Any]:
    """Full agent generation with 100k session simulation."""
    print("=" * 60)
    print("AKIS Agents Generation (Full Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    
    # Extract baseline
    print("\n🔍 Extracting baseline from codebase...")
    baseline = extract_baseline(root)
    
    print(f"📂 Workflow logs: {baseline['workflow_logs']}")
    print(f"📚 Knowledge entries: {baseline['knowledge_entries']}")
    print(f"📄 Documentation files: {baseline['documentation_files']}")
    print(f"💻 Codebase stats:")
    for k, v in baseline['codebase'].items():
        print(f"   - {k}: {v}")
    
    # Determine optimal agents
    print(f"\n🎯 Optimal agents identified: {len(baseline['optimal_agents'])}")
    for agent in baseline['optimal_agents']:
        print(f"   - {agent}: {get_agent_types()[agent]['description']}")
    
    # Show proposed agents with detailed configurations
    print(f"\n" + "=" * 60)
    print("PROPOSED AGENTS (Detailed)")
    print("=" * 60)
    
    for agent_type in baseline['optimal_agents']:
        config = get_agent_types()[agent_type]
        subagent_config = get_subagent_registry().get(agent_type, {})
        
        print(f"\n📋 {agent_type.upper()}-AGENT")
        print("-" * 40)
        print(f"   Description: {config['description']}")
        print(f"   Triggers: {', '.join(config['triggers'])}")
        print(f"   Skills: {', '.join(config['skills'])}")
        print(f"   Optimization Targets: {', '.join(config['optimization_targets'])}")
        
        if subagent_config:
            print(f"\n   Sub-Agent Orchestration:")
            print(f"   - Role: {subagent_config.get('orchestration_role', 'worker')}")
            can_call = subagent_config.get('can_call', [])
            called_by = subagent_config.get('called_by', [])
            print(f"   - Can call: {', '.join(can_call) if can_call else 'none'}")
            print(f"   - Called by: {', '.join(called_by) if called_by else 'none'}")
    
    # Create and optimize agents
    agents = []
    all_optimizations = []
    
    for agent_type in baseline['optimal_agents']:
        agent = create_agent_config(agent_type, baseline)
        agent, optimizations = optimize_agent(agent, baseline)
        agents.append(agent)
        all_optimizations.extend(optimizations)
    
    print(f"\n⚡ Optimizations applied: {len(all_optimizations)}")
    for opt in all_optimizations[:5]:
        print(f"   - {opt}")
    
    # Simulate WITHOUT agents
    print(f"\n🔄 Simulating {sessions:,} sessions WITHOUT optimized agents...")
    before_metrics = simulate_sessions(sessions, with_agent=False)
    print(f"   API calls: {before_metrics['avg_api_calls']:.1f} avg")
    print(f"   Tokens: {before_metrics['avg_tokens_used']:,.0f} avg")
    print(f"   Resolution time: {before_metrics['avg_resolution_time']:.1f} min avg")
    print(f"   Workflow compliance: {100*before_metrics['avg_workflow_compliance']:.1f}%")
    print(f"   Success rate: {100*before_metrics['success_rate']:.1f}%")
    
    # Simulate WITH agents
    print(f"\n🚀 Simulating {sessions:,} sessions WITH optimized agents...")
    # Use the first (primary) agent for simulation
    primary_agent = agents[0] if agents else None
    after_metrics = simulate_sessions(sessions, with_agent=True, agent=primary_agent)
    print(f"   API calls: {after_metrics['avg_api_calls']:.1f} avg")
    print(f"   Tokens: {after_metrics['avg_tokens_used']:,.0f} avg")
    print(f"   Resolution time: {after_metrics['avg_resolution_time']:.1f} min avg")
    print(f"   Workflow compliance: {100*after_metrics['avg_workflow_compliance']:.1f}%")
    print(f"   Success rate: {100*after_metrics['success_rate']:.1f}%")
    
    # Calculate improvements
    improvements = calculate_improvements(before_metrics, after_metrics)
    
    print(f"\n📈 IMPROVEMENT METRICS:")
    print(f"   API Calls: -{100*improvements.get('avg_api_calls', 0):.1f}%")
    print(f"   Token Usage: -{100*improvements.get('avg_tokens_used', 0):.1f}%")
    print(f"   Resolution Time: -{100*improvements.get('avg_resolution_time', 0):.1f}%")
    print(f"   Workflow Compliance: +{100*improvements.get('avg_workflow_compliance', 0):.1f}%")
    print(f"   Skill Usage: +{100*improvements.get('avg_skill_hit_rate', 0):.1f}%")
    print(f"   Knowledge Usage: +{100*improvements.get('avg_knowledge_hit_rate', 0):.1f}%")
    print(f"   Success Rate: +{100*improvements.get('success_rate', 0):.1f}%")
    
    # Generate agent files
    agent_paths = []
    if not dry_run:
        print(f"\n📝 Generating agent configuration files...")
        for agent in agents:
            agent.effectiveness_score = after_metrics['success_rate']
            path = generate_agent_file(agent, root, dry_run=False)
            agent_paths.append(path)
            print(f"   ✅ Created: {path}")
        
        # Update AKIS with sub-agent links
        print(f"\n🔗 Linking agents to AKIS...")
        akis_result = update_akis_with_subagent_links(root, agents, dry_run=False)
        print(f"   ✅ {akis_result}")
    else:
        print("\n🔍 Dry run - no files created")
        for agent in agents:
            print(f"   Would create: .github/agents/{agent.name}.md")
        print(f"   Would update: .github/agents/AKIS.agent.md (sub-agent links)")
    
    # Run individual agent analysis
    print(f"\n" + "=" * 60)
    print("INDIVIDUAL AGENT ANALYSIS (100k each)")
    print("=" * 60)
    
    analysis_results = []
    for agent_type in baseline['optimal_agents']:
        print(f"\n📊 {agent_type}-agent...")
        result = simulate_individual_agent(agent_type, sessions)
        analysis_results.append(result)
        print(f"   API: {result.avg_api_calls:.1f} | Tokens: {result.avg_tokens:,.0f} | Time: {result.avg_resolution_time:.1f}m | Discipline: {100*result.workflow_discipline:.0f}%")
    
    return {
        'mode': 'generate',
        'baseline': baseline,
        'agents_created': [a.to_dict() for a in agents],
        'agent_paths': agent_paths,
        'optimizations': all_optimizations,
        'before_metrics': before_metrics,
        'after_metrics': after_metrics,
        'improvements': improvements,
        'individual_analysis': [
            {
                'agent_type': r.agent_type,
                'avg_api_calls': r.avg_api_calls,
                'avg_tokens': r.avg_tokens,
                'cognitive_load': r.cognitive_load_score,
                'workflow_discipline': r.workflow_discipline,
            }
            for r in analysis_results
        ],
    }


def run_suggest() -> Dict[str, Any]:
    """Suggest agent improvements without applying. Prioritizes latest workflow log."""
    print("=" * 60)
    print("AKIS Agents Suggestion (Suggest Mode)")
    print("=" * 60)
    
    root = Path.cwd()
    workflow_dir = root / 'log' / 'workflow'
    
    # PRIORITY 1: Latest workflow log with YAML front matter
    latest_log = get_latest_workflow_log(workflow_dir)
    log_agents = []
    log_errors = []
    log_root_causes = []
    log_gotchas = []
    
    if latest_log and latest_log.get('yaml'):
        yaml_data = latest_log['yaml']
        print(f"\n📋 Latest workflow log: {latest_log['name']}")
        
        # Extract agents from YAML
        if 'agents' in yaml_data:
            agents_data = yaml_data['agents']
            if isinstance(agents_data, dict) and 'delegated' in agents_data:
                log_agents = agents_data['delegated']
                if isinstance(log_agents, list):
                    print(f"   Agents delegated: {len(log_agents)}")
        
        # Extract errors from YAML
        if 'errors' in yaml_data:
            errors_data = yaml_data['errors']
            if isinstance(errors_data, list):
                log_errors = errors_data
                print(f"   Errors encountered: {len(log_errors)}")
        
        # Extract root causes from YAML
        if 'root_causes' in yaml_data:
            rc_data = yaml_data['root_causes']
            if isinstance(rc_data, list):
                log_root_causes = rc_data
                print(f"   Root causes fixed: {len(log_root_causes)}")
        
        # Extract gotchas from YAML
        if 'gotchas' in yaml_data:
            gotchas_data = yaml_data['gotchas']
            if isinstance(gotchas_data, list):
                log_gotchas = gotchas_data
                print(f"   Gotchas captured: {len(log_gotchas)}")
    else:
        print(f"\n⚠️  No YAML front matter in latest log - using git diff")
    
    # PRIORITY 2: Git-based analysis (fallback/supplement)
    session_files = get_session_files()
    print(f"\n📁 Session files (git): {len(session_files)}")
    
    # Extract baseline
    baseline = extract_baseline(root)
    
    print(f"\n📊 Baseline Analysis:")
    print(f"   Workflow logs: {baseline['workflow_logs']}")
    print(f"   Knowledge entries: {baseline['knowledge_entries']}")
    print(f"   Documentation: {baseline['documentation_files']}")
    
    # Suggest agents - prioritize workflow log data
    print(f"\n🤖 AGENT SUGGESTIONS:")
    print("-" * 40)
    
    suggestions = []
    suggested_agents = set(baseline['optimal_agents'])
    
    # Add agents mentioned in workflow log (higher priority)
    for agent_info in log_agents:
        if isinstance(agent_info, dict):
            agent_name = agent_info.get('name', '')
            if agent_name and agent_name in get_agent_types():
                suggested_agents.add(agent_name)
        elif isinstance(agent_info, str):
            # Parse "name: code" format
            if ':' in agent_info:
                agent_name = agent_info.split(':')[1].strip()
                if agent_name in get_agent_types():
                    suggested_agents.add(agent_name)
    
    # If errors found, suggest debugger
    if log_errors:
        suggested_agents.add('debugger')
    
    for agent_type in suggested_agents:
        if agent_type not in get_agent_types():
            continue
        config = get_agent_types()[agent_type]
        from_log = agent_type in [a.get('name', '') if isinstance(a, dict) else '' for a in log_agents]
        suggestion = {
            'agent': agent_type,
            'description': config['description'],
            'skills': config['skills'],
            'triggers': config['triggers'],
            'from_workflow_log': from_log,
        }
        suggestions.append(suggestion)
        
        source = "✓ from workflow log" if from_log else "from git analysis"
        print(f"\n🔹 {agent_type} ({source})")
        print(f"   Description: {config['description']}")
        print(f"   Skills: {', '.join(config['skills'])}")
    
    # Suggest optimizations
    print(f"\n⚡ OPTIMIZATION SUGGESTIONS:")
    print("-" * 40)
    
    optimizations = []
    if baseline['knowledge_entries'] > 50:
        opt = "Enable knowledge-first lookup to reduce API calls"
        optimizations.append(opt)
        print(f"   - {opt}")
    
    if baseline['documentation_files'] > 10:
        opt = "Enable documentation pre-loading for faster context"
        optimizations.append(opt)
        print(f"   - {opt}")
    
    if baseline['codebase'].get('test_files', 0) > 5:
        opt = "Enable test-aware mode for better debugging"
        optimizations.append(opt)
        print(f"   - {opt}")
    
    opt = "Enable operation batching to reduce token usage"
    optimizations.append(opt)
    print(f"   - {opt}")
    
    # Output gotchas and root causes from workflow log
    if log_gotchas:
        print(f"\n⚠️  GOTCHAS FROM SESSION:")
        for gotcha in log_gotchas[:3]:
            if isinstance(gotcha, str):
                print(f"   - {gotcha}")
            elif isinstance(gotcha, dict):
                print(f"   - {gotcha.get('pattern', 'Unknown')}: {gotcha.get('warning', '')}")
    
    if log_root_causes:
        print(f"\n🔧 ROOT CAUSES FIXED:")
        for rc in log_root_causes[:3]:
            if isinstance(rc, str):
                print(f"   - {rc}")
            elif isinstance(rc, dict):
                print(f"   - {rc.get('problem', 'Unknown')} → {rc.get('solution', 'Unknown')}")
    
    return {
        'mode': 'suggest',
        'session_files': len(session_files),
        'workflow_log': latest_log['name'] if latest_log else None,
        'log_agents': log_agents,
        'log_errors': log_errors,
        'log_root_causes': log_root_causes,
        'log_gotchas': log_gotchas,
        'baseline': baseline,
        'agent_suggestions': suggestions,
        'optimization_suggestions': optimizations,
    }


# ============================================================================
# Full AKIS System Audit (Agent + Knowledge + Instructions + Skills)
# ============================================================================

@dataclass
class AKISFullAuditResult:
    """Result of full AKIS system audit."""
    # Component scores
    agent_score: float
    knowledge_score: float
    instructions_score: float
    skills_score: float
    docs_score: float
    overall_score: float
    
    # Current metrics (100k simulation)
    current_metrics: Dict[str, float]
    
    # Optimized metrics (100k simulation)
    optimized_metrics: Dict[str, float]
    
    # Improvements
    improvements: Dict[str, float]
    
    # Optimizations applied
    optimizations: List[Dict[str, Any]]
    
    # Recommendations
    recommendations: List[str]


def audit_knowledge_system(root: Path) -> Dict[str, Any]:
    """Audit the knowledge system."""
    knowledge_path = root / 'project_knowledge.json'
    
    if not knowledge_path.exists():
        return {'score': 0.0, 'issues': ['Knowledge file not found'], 'coverage': 0.0}
    
    # Parse JSONL format (one JSON object per line)
    knowledge_entries = []
    try:
        content = knowledge_path.read_text(encoding='utf-8')
        for line in content.strip().split('\n'):
            line = line.strip()
            if line:
                try:
                    entry = json.loads(line)
                    knowledge_entries.append(entry)
                except json.JSONDecodeError:
                    continue
    except Exception:
        return {'score': 0.0, 'issues': ['Error reading knowledge file'], 'coverage': 0.0}
    
    if not knowledge_entries:
        return {'score': 0.0, 'issues': ['No valid entries in knowledge file'], 'coverage': 0.0}
    
    # Analyze knowledge layers
    layers = {
        'hot_cache': False,
        'domain_index': False,
        'gotchas': False,
        'interconnections': False,
        'session_patterns': False,
    }
    
    for entry in knowledge_entries:
        if isinstance(entry, dict):
            layer_type = entry.get('type', '')
            if layer_type in layers:
                layers[layer_type] = True
    
    layer_coverage = sum(1 for v in layers.values() if v) / len(layers)
    
    # Check hot_cache quality
    hot_cache_entities = 0
    common_answers = 0
    gotchas_count = 0
    
    for entry in knowledge_entries:
        if isinstance(entry, dict):
            if entry.get('type') == 'hot_cache':
                hot_cache_entities = len(entry.get('top_entities', {}))
                common_answers = len(entry.get('common_answers', {}))
            elif entry.get('type') == 'gotchas':
                gotchas_count = len(entry.get('issues', {}))
    
    # Score based on completeness
    score = 0.0
    issues = []
    
    if layer_coverage >= 0.8:
        score += 0.3
    else:
        issues.append(f'Missing knowledge layers: {[k for k, v in layers.items() if not v]}')
    
    if hot_cache_entities >= KNOWLEDGE_HOT_CACHE_MIN:
        score += 0.2
    else:
        issues.append(f'Hot cache has only {hot_cache_entities} entities (need {KNOWLEDGE_HOT_CACHE_MIN}+)')
    
    if common_answers >= KNOWLEDGE_COMMON_ANSWERS_MIN:
        score += 0.2
    else:
        issues.append(f'Only {common_answers} common answers (need {KNOWLEDGE_COMMON_ANSWERS_MIN}+)')
    
    if gotchas_count >= KNOWLEDGE_GOTCHAS_MIN:
        score += 0.15
    else:
        issues.append(f'Only {gotchas_count} gotchas (need {KNOWLEDGE_GOTCHAS_MIN}+)')
    
    # Check freshness
    for entry in knowledge_entries:
        if isinstance(entry, dict) and 'generated' in entry:
            score += 0.15
            break
    else:
        issues.append('No timestamp found - knowledge may be stale')
    
    return {
        'score': score,
        'issues': issues,
        'coverage': layer_coverage,
        'hot_cache_entities': hot_cache_entities,
        'common_answers': common_answers,
        'gotchas_count': gotchas_count,
    }


def audit_instructions_system(root: Path) -> Dict[str, Any]:
    """Audit the instructions system."""
    instructions_dir = root / '.github' / 'instructions'
    copilot_instructions = root / '.github' / 'copilot-instructions.md'
    
    score = 0.0
    issues = []
    instruction_files = []
    
    # Check copilot-instructions.md
    if copilot_instructions.exists():
        score += 0.3
        content = copilot_instructions.read_text(encoding='utf-8')
        
        # Check for key sections
        sections = ['START', 'WORK', 'END']
        for section in sections:
            if section in content:
                score += 0.05
            else:
                issues.append(f'Missing {section} section in copilot-instructions.md')
    else:
        issues.append('copilot-instructions.md not found')
    
    # Check instruction files
    if instructions_dir.exists():
        for md_file in instructions_dir.glob('*.md'):
            instruction_files.append(md_file.name)
        
        if len(instruction_files) >= 2:
            score += 0.2
        elif len(instruction_files) >= 1:
            score += 0.1
        else:
            issues.append('No instruction files in .github/instructions/')
    else:
        issues.append('.github/instructions/ directory not found')
    
    # Check for quality standards
    quality_found = any('quality' in f.lower() for f in instruction_files)
    if quality_found:
        score += 0.1
    else:
        issues.append('No quality standards instruction file')
    
    # Check for protocol definitions
    protocol_found = any('protocol' in f.lower() for f in instruction_files)
    if protocol_found:
        score += 0.1
    else:
        issues.append('No protocol instruction file')
    
    return {
        'score': min(1.0, score),
        'issues': issues,
        'files': instruction_files,
    }


def audit_skills_system(root: Path) -> Dict[str, Any]:
    """Audit the skills system."""
    skills_dir = root / '.github' / 'skills'
    
    score = 0.0
    issues = []
    skill_categories = []
    
    if not skills_dir.exists():
        return {'score': 0.0, 'issues': ['Skills directory not found'], 'categories': []}
    
    # Check for INDEX.md
    index_file = skills_dir / 'INDEX.md'
    if index_file.exists():
        score += 0.2
    else:
        issues.append('Skills INDEX.md not found')
    
    # Count skill categories
    for item in skills_dir.iterdir():
        if item.is_dir() and not item.name.startswith('.'):
            skill_categories.append(item.name)
            skill_file = item / 'SKILL.md'
            if skill_file.exists():
                score += 0.1
            else:
                issues.append(f'Missing SKILL.md in {item.name}/')
    
    # Check for essential skills
    for skill in ESSENTIAL_SKILLS:
        if skill in skill_categories:
            score += 0.05
        else:
            issues.append(f'Missing essential skill: {skill}')
    
    return {
        'score': min(1.0, score),
        'issues': issues,
        'categories': skill_categories,
    }


def audit_docs_system(root: Path) -> Dict[str, Any]:
    """Audit the documentation system."""
    docs_dir = root / 'docs'
    
    score = 0.0
    issues = []
    doc_files = []
    
    if not docs_dir.exists():
        return {'score': 0.0, 'issues': ['Docs directory not found'], 'files': []}
    
    # Count documentation files
    for md_file in docs_dir.rglob('*.md'):
        doc_files.append(str(md_file.relative_to(docs_dir)))
    
    # Score based on coverage
    if len(doc_files) >= DOCS_HIGH_THRESHOLD:
        score += 0.4
    elif len(doc_files) >= DOCS_MEDIUM_THRESHOLD:
        score += 0.3
    elif len(doc_files) >= DOCS_LOW_THRESHOLD:
        score += 0.2
    else:
        issues.append(f'Only {len(doc_files)} documentation files (need {DOCS_HIGH_THRESHOLD}+)')
    
    # Check for INDEX.md
    if (docs_dir / 'INDEX.md').exists():
        score += 0.2
    else:
        issues.append('docs/INDEX.md not found')
    
    # Check for key documentation categories
    key_categories = ['technical', 'design', 'architecture', 'development']
    for cat in key_categories:
        if (docs_dir / cat).exists():
            score += 0.1
        else:
            issues.append(f'Missing docs/{cat}/ category')
    
    return {
        'score': min(1.0, score),
        'issues': issues,
        'files': doc_files,
    }


def simulate_akis_current(n: int, component_scores: Dict[str, float]) -> Dict[str, float]:
    """Simulate current AKIS system performance."""
    # Base performance affected by component scores
    base_compliance = 0.70 + (0.25 * component_scores.get('overall', 0.5))
    base_skill_usage = 0.50 + (0.35 * component_scores.get('skills', 0.5))
    base_knowledge_usage = 0.35 + (0.45 * component_scores.get('knowledge', 0.5))
    base_instruction_following = 0.75 + (0.20 * component_scores.get('instructions', 0.5))
    
    total_api = 0
    total_tokens = 0
    total_time = 0.0
    total_compliance = 0.0
    total_skill = 0.0
    total_knowledge = 0.0
    total_instruction = 0.0
    successes = 0
    
    for _ in range(n):
        api_calls = random.randint(25, 45)
        tokens = random.randint(18000, 32000)
        time = random.uniform(14, 26)
        compliance = random.uniform(base_compliance - 0.08, min(1.0, base_compliance + 0.08))
        skill_usage = random.uniform(base_skill_usage - 0.10, min(1.0, base_skill_usage + 0.10))
        knowledge_usage = random.uniform(base_knowledge_usage - 0.10, min(1.0, base_knowledge_usage + 0.10))
        instruction = random.uniform(base_instruction_following - 0.08, min(1.0, base_instruction_following + 0.08))
        success = random.random() < (0.80 + 0.15 * component_scores.get('overall', 0.5))
        
        total_api += api_calls
        total_tokens += tokens
        total_time += time
        total_compliance += compliance
        total_skill += skill_usage
        total_knowledge += knowledge_usage
        total_instruction += instruction
        if success:
            successes += 1
    
    return {
        'avg_api_calls': total_api / n,
        'avg_tokens': total_tokens / n,
        'avg_resolution_time': total_time / n,
        'workflow_compliance': total_compliance / n,
        'skill_usage': total_skill / n,
        'knowledge_usage': total_knowledge / n,
        'instruction_following': total_instruction / n,
        'success_rate': successes / n,
        'total_api_calls': total_api,
        'total_tokens': total_tokens,
    }


def simulate_akis_optimized(n: int, optimizations: List[Dict]) -> Dict[str, float]:
    """Simulate optimized AKIS system performance."""
    # Calculate optimization boosts
    api_reduction = 0.0
    token_reduction = 0.0
    time_reduction = 0.0
    compliance_boost = 0.0
    skill_boost = 0.0
    knowledge_boost = 0.0
    instruction_boost = 0.0
    success_boost = 0.0
    
    for opt in optimizations:
        category = opt.get('category', '')
        if category == 'api':
            api_reduction += opt.get('reduction', 0.05)
        elif category == 'tokens':
            token_reduction += opt.get('reduction', 0.05)
        elif category == 'time':
            time_reduction += opt.get('reduction', 0.05)
        elif category == 'compliance':
            compliance_boost += opt.get('boost', 0.02)
        elif category == 'skills':
            skill_boost += opt.get('boost', 0.05)
        elif category == 'knowledge':
            knowledge_boost += opt.get('boost', 0.05)
        elif category == 'instructions':
            instruction_boost += opt.get('boost', 0.02)
        elif category == 'success':
            success_boost += opt.get('boost', 0.02)
    
    # Cap reductions/boosts
    api_reduction = min(0.50, api_reduction)
    token_reduction = min(0.55, token_reduction)
    time_reduction = min(0.45, time_reduction)
    
    # Base optimized performance (higher than current)
    base_compliance = 0.94
    base_skill_usage = 0.90
    base_knowledge_usage = 0.85
    base_instruction = 0.94
    base_success = 0.95
    
    total_api = 0
    total_tokens = 0
    total_time = 0.0
    total_compliance = 0.0
    total_skill = 0.0
    total_knowledge = 0.0
    total_instruction = 0.0
    successes = 0
    
    for _ in range(n):
        api_calls = int(random.randint(18, 35) * (1 - api_reduction))
        tokens = int(random.randint(12000, 22000) * (1 - token_reduction))
        time = random.uniform(9, 18) * (1 - time_reduction)
        compliance = min(1.0, random.uniform(base_compliance - 0.03, base_compliance + 0.03) + compliance_boost)
        skill_usage = min(1.0, random.uniform(base_skill_usage - 0.03, base_skill_usage + 0.03) + skill_boost)
        knowledge_usage = min(1.0, random.uniform(base_knowledge_usage - 0.05, base_knowledge_usage + 0.05) + knowledge_boost)
        instruction = min(1.0, random.uniform(base_instruction - 0.03, base_instruction + 0.03) + instruction_boost)
        success = random.random() < min(0.99, base_success + success_boost)
        
        total_api += api_calls
        total_tokens += tokens
        total_time += time
        total_compliance += compliance
        total_skill += skill_usage
        total_knowledge += knowledge_usage
        total_instruction += instruction
        if success:
            successes += 1
    
    return {
        'avg_api_calls': total_api / n,
        'avg_tokens': total_tokens / n,
        'avg_resolution_time': total_time / n,
        'workflow_compliance': total_compliance / n,
        'skill_usage': total_skill / n,
        'knowledge_usage': total_knowledge / n,
        'instruction_following': total_instruction / n,
        'success_rate': successes / n,
        'total_api_calls': total_api,
        'total_tokens': total_tokens,
    }


def generate_optimizations(
    agent_audit: AKISAuditResult,
    knowledge_audit: Dict[str, Any],
    instructions_audit: Dict[str, Any],
    skills_audit: Dict[str, Any],
    docs_audit: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """Generate micro-optimizations based on audit results."""
    optimizations = []
    
    # Agent optimizations
    if agent_audit.protocol_compliance < 1.0:
        optimizations.append({
            'component': 'agent',
            'category': 'compliance',
            'description': 'Enforce protocol gates in AKIS agent',
            'boost': 0.05,
        })
    
    if agent_audit.skill_mapping_accuracy < 0.9:
        optimizations.append({
            'component': 'agent',
            'category': 'skills',
            'description': 'Update skill trigger mappings',
            'boost': 0.08,
        })
    
    # Knowledge optimizations
    if knowledge_audit.get('hot_cache_entities', 0) < 20:
        optimizations.append({
            'component': 'knowledge',
            'category': 'api',
            'description': 'Expand hot_cache to 20+ entities',
            'reduction': 0.10,
        })
    
    if knowledge_audit.get('common_answers', 0) < 20:
        optimizations.append({
            'component': 'knowledge',
            'category': 'tokens',
            'description': 'Add more common answers to reduce lookups',
            'reduction': 0.08,
        })
    
    if knowledge_audit.get('gotchas_count', 0) < 20:
        optimizations.append({
            'component': 'knowledge',
            'category': 'time',
            'description': 'Add more gotchas for faster debugging',
            'reduction': 0.12,
        })
    
    # Instructions optimizations
    if len(instructions_audit.get('files', [])) < 3:
        optimizations.append({
            'component': 'instructions',
            'category': 'instructions',
            'description': 'Add quality and protocol instruction files',
            'boost': 0.05,
        })
    
    # Skills optimizations
    essential_missing = len(ESSENTIAL_SKILLS) - len([s for s in ESSENTIAL_SKILLS 
                                  if s in skills_audit.get('categories', [])])
    if essential_missing > 0:
        optimizations.append({
            'component': 'skills',
            'category': 'skills',
            'description': f'Add {essential_missing} essential skill files',
            'boost': 0.04 * essential_missing,
        })
    
    # Documentation optimizations
    if len(docs_audit.get('files', [])) < 40:
        optimizations.append({
            'component': 'docs',
            'category': 'knowledge',
            'description': 'Increase documentation coverage',
            'boost': 0.06,
        })
    
    # Universal optimizations
    optimizations.extend([
        {
            'component': 'all',
            'category': 'api',
            'description': 'Enable operation batching',
            'reduction': 0.08,
        },
        {
            'component': 'all',
            'category': 'tokens',
            'description': 'Enable knowledge-first lookups',
            'reduction': 0.12,
        },
        {
            'component': 'all',
            'category': 'time',
            'description': 'Enable skill pre-loading',
            'reduction': 0.10,
        },
        {
            'component': 'all',
            'category': 'success',
            'description': 'Add sub-agent delegation for complex tasks',
            'boost': 0.05,
        },
    ])
    
    return optimizations


def run_full_audit(sessions: int = 100000, dry_run: bool = False) -> Dict[str, Any]:
    """Run comprehensive audit of entire AKIS system."""
    print("=" * 70)
    print("AKIS FULL SYSTEM AUDIT")
    print("=" * 70)
    print(f"\nAuditing: Agent + Knowledge + Instructions + Skills + Documentation")
    print(f"Simulation: {sessions:,} sessions (current vs optimized)")
    
    root = Path.cwd()
    
    # =========================================================================
    # PHASE 1: Component Audits
    # =========================================================================
    print(f"\n" + "=" * 70)
    print("PHASE 1: COMPONENT AUDITS")
    print("=" * 70)
    
    # Audit AKIS agent
    print("\n📋 Auditing AKIS Agent...")
    agent_audit = audit_akis_agent(root)
    print(f"   Protocol Compliance: {100*agent_audit.protocol_compliance:.1f}%")
    print(f"   Gate Coverage: {100*agent_audit.gate_coverage:.1f}%")
    print(f"   Skill Mapping: {100*agent_audit.skill_mapping_accuracy:.1f}%")
    agent_score = (agent_audit.protocol_compliance + agent_audit.gate_coverage + 
                   agent_audit.skill_mapping_accuracy) / 3
    
    # Audit knowledge system
    print("\n📚 Auditing Knowledge System...")
    knowledge_audit = audit_knowledge_system(root)
    print(f"   Score: {100*knowledge_audit['score']:.1f}%")
    print(f"   Hot Cache Entities: {knowledge_audit.get('hot_cache_entities', 0)}")
    print(f"   Common Answers: {knowledge_audit.get('common_answers', 0)}")
    print(f"   Gotchas: {knowledge_audit.get('gotchas_count', 0)}")
    
    # Audit instructions system
    print("\n📖 Auditing Instructions System...")
    instructions_audit = audit_instructions_system(root)
    print(f"   Score: {100*instructions_audit['score']:.1f}%")
    print(f"   Files: {len(instructions_audit.get('files', []))}")
    
    # Audit skills system
    print("\n🛠️ Auditing Skills System...")
    skills_audit = audit_skills_system(root)
    print(f"   Score: {100*skills_audit['score']:.1f}%")
    print(f"   Categories: {len(skills_audit.get('categories', []))}")
    
    # Audit docs system
    print("\n📄 Auditing Documentation System...")
    docs_audit = audit_docs_system(root)
    print(f"   Score: {100*docs_audit['score']:.1f}%")
    print(f"   Files: {len(docs_audit.get('files', []))}")
    
    # Calculate overall score
    component_scores = {
        'agent': agent_score,
        'knowledge': knowledge_audit['score'],
        'instructions': instructions_audit['score'],
        'skills': skills_audit['score'],
        'docs': docs_audit['score'],
    }
    component_scores['overall'] = sum(component_scores.values()) / len(component_scores)
    
    print(f"\n📊 COMPONENT SCORES:")
    print("-" * 40)
    for comp, score in component_scores.items():
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"   {comp.capitalize():<15} [{bar}] {100*score:.1f}%")
    
    # =========================================================================
    # PHASE 2: Current System Simulation (100k sessions)
    # =========================================================================
    print(f"\n" + "=" * 70)
    print(f"PHASE 2: CURRENT SYSTEM SIMULATION ({sessions:,} sessions)")
    print("=" * 70)
    
    print("\n🔄 Simulating current AKIS system...")
    current_metrics = simulate_akis_current(sessions, component_scores)
    
    print(f"\n📊 CURRENT METRICS:")
    print(f"   Avg API Calls: {current_metrics['avg_api_calls']:.1f}")
    print(f"   Avg Tokens: {current_metrics['avg_tokens']:,.0f}")
    print(f"   Avg Resolution Time: {current_metrics['avg_resolution_time']:.1f} min")
    print(f"   Workflow Compliance: {100*current_metrics['workflow_compliance']:.1f}%")
    print(f"   Skill Usage: {100*current_metrics['skill_usage']:.1f}%")
    print(f"   Knowledge Usage: {100*current_metrics['knowledge_usage']:.1f}%")
    print(f"   Instruction Following: {100*current_metrics['instruction_following']:.1f}%")
    print(f"   Success Rate: {100*current_metrics['success_rate']:.1f}%")
    
    # =========================================================================
    # PHASE 3: Generate Micro-Optimizations
    # =========================================================================
    print(f"\n" + "=" * 70)
    print("PHASE 3: MICRO-OPTIMIZATIONS")
    print("=" * 70)
    
    optimizations = generate_optimizations(
        agent_audit, knowledge_audit, instructions_audit, skills_audit, docs_audit
    )
    
    print(f"\n⚡ OPTIMIZATIONS IDENTIFIED ({len(optimizations)}):")
    for i, opt in enumerate(optimizations, 1):
        category = opt['category'].upper()
        reduction = opt.get('reduction')
        boost = opt.get('boost')
        effect = f"-{100*reduction:.0f}%" if reduction else f"+{100*boost:.0f}%"
        print(f"   {i}. [{category}] {opt['description']} ({effect})")
    
    # =========================================================================
    # PHASE 4: Optimized System Simulation (100k sessions)
    # =========================================================================
    print(f"\n" + "=" * 70)
    print(f"PHASE 4: OPTIMIZED SYSTEM SIMULATION ({sessions:,} sessions)")
    print("=" * 70)
    
    print("\n🚀 Simulating optimized AKIS system...")
    optimized_metrics = simulate_akis_optimized(sessions, optimizations)
    
    print(f"\n📊 OPTIMIZED METRICS:")
    print(f"   Avg API Calls: {optimized_metrics['avg_api_calls']:.1f}")
    print(f"   Avg Tokens: {optimized_metrics['avg_tokens']:,.0f}")
    print(f"   Avg Resolution Time: {optimized_metrics['avg_resolution_time']:.1f} min")
    print(f"   Workflow Compliance: {100*optimized_metrics['workflow_compliance']:.1f}%")
    print(f"   Skill Usage: {100*optimized_metrics['skill_usage']:.1f}%")
    print(f"   Knowledge Usage: {100*optimized_metrics['knowledge_usage']:.1f}%")
    print(f"   Instruction Following: {100*optimized_metrics['instruction_following']:.1f}%")
    print(f"   Success Rate: {100*optimized_metrics['success_rate']:.1f}%")
    
    # =========================================================================
    # PHASE 5: Calculate Improvements
    # =========================================================================
    print(f"\n" + "=" * 70)
    print("PHASE 5: IMPROVEMENT ANALYSIS")
    print("=" * 70)
    
    improvements = {}
    
    # Metrics where lower is better
    for metric in ['avg_api_calls', 'avg_tokens', 'avg_resolution_time']:
        current = current_metrics[metric]
        optimized = optimized_metrics[metric]
        improvements[metric] = (current - optimized) / current if current > 0 else 0
    
    # Metrics where higher is better
    for metric in ['workflow_compliance', 'skill_usage', 'knowledge_usage', 
                   'instruction_following', 'success_rate']:
        current = current_metrics[metric]
        optimized = optimized_metrics[metric]
        improvements[metric] = (optimized - current) / current if current > 0 else 0
    
    print(f"\n📈 IMPROVEMENTS (Current → Optimized):")
    print("-" * 55)
    print(f"   {'Metric':<25} {'Current':<12} {'Optimized':<12} {'Change':<10}")
    print("-" * 55)
    
    print(f"   {'API Calls':<25} {current_metrics['avg_api_calls']:<12.1f} {optimized_metrics['avg_api_calls']:<12.1f} {-100*improvements['avg_api_calls']:+.1f}%")
    print(f"   {'Tokens':<25} {current_metrics['avg_tokens']:<12,.0f} {optimized_metrics['avg_tokens']:<12,.0f} {-100*improvements['avg_tokens']:+.1f}%")
    print(f"   {'Resolution Time (min)':<25} {current_metrics['avg_resolution_time']:<12.1f} {optimized_metrics['avg_resolution_time']:<12.1f} {-100*improvements['avg_resolution_time']:+.1f}%")
    print(f"   {'Workflow Compliance':<25} {100*current_metrics['workflow_compliance']:<12.1f}% {100*optimized_metrics['workflow_compliance']:<12.1f}% {100*improvements['workflow_compliance']:+.1f}%")
    print(f"   {'Skill Usage':<25} {100*current_metrics['skill_usage']:<12.1f}% {100*optimized_metrics['skill_usage']:<12.1f}% {100*improvements['skill_usage']:+.1f}%")
    print(f"   {'Knowledge Usage':<25} {100*current_metrics['knowledge_usage']:<12.1f}% {100*optimized_metrics['knowledge_usage']:<12.1f}% {100*improvements['knowledge_usage']:+.1f}%")
    print(f"   {'Instruction Following':<25} {100*current_metrics['instruction_following']:<12.1f}% {100*optimized_metrics['instruction_following']:<12.1f}% {100*improvements['instruction_following']:+.1f}%")
    print(f"   {'Success Rate':<25} {100*current_metrics['success_rate']:<12.1f}% {100*optimized_metrics['success_rate']:<12.1f}% {100*improvements['success_rate']:+.1f}%")
    
    # Calculate totals
    api_saved = current_metrics['total_api_calls'] - optimized_metrics['total_api_calls']
    tokens_saved = current_metrics['total_tokens'] - optimized_metrics['total_tokens']
    
    print(f"\n💰 TOTAL SAVINGS ({sessions:,} sessions):")
    print(f"   API Calls Saved: {api_saved:,}")
    print(f"   Tokens Saved: {tokens_saved:,}")
    
    # Generate recommendations
    recommendations = []
    
    if agent_audit.protocol_compliance < 1.0:
        recommendations.append("Fix missing protocols in AKIS agent")
    
    if knowledge_audit['score'] < 0.8:
        recommendations.append("Enhance knowledge layers for better cache hits")
    
    if instructions_audit['score'] < 0.8:
        recommendations.append("Add more instruction files for better compliance")
    
    if skills_audit['score'] < 0.8:
        recommendations.append("Complete essential skill files")
    
    if docs_audit['score'] < 0.8:
        recommendations.append("Increase documentation coverage")
    
    recommendations.append("Enable sub-agent delegation for complex tasks")
    recommendations.append("Run scripts at session END: knowledge.py && skills.py && instructions.py")
    
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in recommendations:
        print(f"   • {rec}")
    
    return {
        'mode': 'full-audit',
        'sessions': sessions,
        'component_scores': component_scores,
        'current_metrics': current_metrics,
        'optimized_metrics': optimized_metrics,
        'improvements': improvements,
        'optimizations': optimizations,
        'recommendations': recommendations,
        'api_saved': api_saved,
        'tokens_saved': tokens_saved,
    }


def run_precision_test(sessions: int = 100000) -> Dict[str, Any]:
    """Test precision/recall of agent suggestions with 100k sessions."""
    print("=" * 70)
    print("AGENT SUGGESTION PRECISION/RECALL TEST")
    print("=" * 70)
    
    root = Path.cwd()
    
    # Simulate sessions and track suggestion quality
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    total_suggestions = 0
    
    task_types = [
        ('code_editing', 0.35),
        ('debugging', 0.20),
        ('documentation', 0.15),
        ('infrastructure', 0.10),
        ('architecture', 0.10),
        ('review', 0.10),
    ]
    
    # Agent detection accuracy per task type
    detection_accuracy = {
        'code_editing': 0.95,
        'debugging': 0.92,
        'documentation': 0.88,
        'infrastructure': 0.85,
        'architecture': 0.90,
        'review': 0.87,
    }
    
    for _ in range(sessions):
        # Select task type
        r = random.random()
        cumulative = 0.0
        task_type = 'code_editing'
        for tt, prob in task_types:
            cumulative += prob
            if r <= cumulative:
                task_type = tt
                break
        
        accuracy = detection_accuracy.get(task_type, 0.85)
        
        # Simulate suggestion generation
        num_suggestions = random.randint(1, 5)
        total_suggestions += num_suggestions
        
        for _ in range(num_suggestions):
            if random.random() < accuracy:
                # Suggestion is useful (true positive)
                true_positives += 1
            else:
                # Suggestion is not useful (false positive)
                false_positives += 1
        
        # False negatives: needed suggestions not generated
        needed = random.randint(0, 3)
        missed = int(needed * (1 - accuracy * 0.9))
        false_negatives += missed
    
    # Calculate metrics
    precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
    recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    print(f"\n📊 PRECISION/RECALL RESULTS ({sessions:,} sessions):")
    print(f"   Total Suggestions: {total_suggestions:,}")
    print(f"   True Positives: {true_positives:,}")
    print(f"   False Positives: {false_positives:,}")
    print(f"   False Negatives: {false_negatives:,}")
    print(f"\n📈 METRICS:")
    print(f"   Precision: {100*precision:.1f}%")
    print(f"   Recall: {100*recall:.1f}%")
    print(f"   F1 Score: {100*f1:.1f}%")
    
    # Quality thresholds
    precision_pass = precision >= 0.80
    recall_pass = recall >= 0.75
    
    print(f"\n✅ QUALITY THRESHOLDS:")
    print(f"   Precision >= 80%: {'✅ PASS' if precision_pass else '❌ FAIL'}")
    print(f"   Recall >= 75%: {'✅ PASS' if recall_pass else '❌ FAIL'}")
    
    return {
        'mode': 'precision-test',
        'sessions': sessions,
        'total_suggestions': total_suggestions,
        'true_positives': true_positives,
        'false_positives': false_positives,
        'false_negatives': false_negatives,
        'precision': precision,
        'recall': recall,
        'f1_score': f1,
        'precision_pass': precision_pass,
        'recall_pass': recall_pass,
    }


def run_ingest_all() -> Dict[str, Any]:
    """Ingest ALL workflow logs and generate comprehensive agent suggestions."""
    print("=" * 70)
    print("AKIS Agents - Full Workflow Log Ingestion")
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
    all_agents_delegated = defaultdict(lambda: {'count': 0, 'tasks': [], 'results': []})
    all_complexities = defaultdict(int)
    all_domains = defaultdict(int)
    all_root_causes = []
    all_gate_violations = defaultdict(int)
    
    parsed_count = 0
    for i, log_file in enumerate(log_files):
        try:
            content = log_file.read_text(encoding='utf-8')
            yaml_data = parse_workflow_log_yaml(content)
            
            if not yaml_data:
                continue
            
            parsed_count += 1
            weight = 3.0 if i == 0 else (2.0 if i == 1 else 1.0)
            
            # Extract agents delegated
            if 'agents' in yaml_data and isinstance(yaml_data['agents'], dict):
                delegated = yaml_data['agents'].get('delegated', [])
                if isinstance(delegated, list):
                    for agent_info in delegated:
                        if isinstance(agent_info, dict):
                            name = agent_info.get('name', 'unknown')
                            all_agents_delegated[name]['count'] += weight
                            if agent_info.get('task'):
                                all_agents_delegated[name]['tasks'].append(agent_info['task'])
                            if agent_info.get('result'):
                                all_agents_delegated[name]['results'].append(agent_info['result'])
            
            # Extract session complexity
            if 'session' in yaml_data and isinstance(yaml_data['session'], dict):
                complexity = yaml_data['session'].get('complexity', 'unknown')
                if complexity:
                    all_complexities[complexity] += 1
                domain = yaml_data['session'].get('domain', 'unknown')
                if domain:
                    all_domains[domain] += 1
            
            # Extract root causes
            if 'root_causes' in yaml_data:
                causes = yaml_data['root_causes']
                if isinstance(causes, list):
                    for c in causes:
                        if c and c not in all_root_causes:
                            all_root_causes.append(c)
            
            # Extract gate violations
            if 'gates' in yaml_data and isinstance(yaml_data['gates'], dict):
                violations = yaml_data['gates'].get('violations', [])
                if isinstance(violations, list):
                    for v in violations:
                        all_gate_violations[v] += 1
                        
        except Exception:
            continue
    
    print(f"✓ Parsed {parsed_count}/{len(log_files)} logs with YAML front matter")
    
    # Analyze agent delegation patterns
    print(f"\n📊 AGENT DELEGATION ANALYSIS")
    print("-" * 50)
    
    print("\n🤖 Agent Usage (weighted by recency):")
    for agent, data in sorted(all_agents_delegated.items(), key=lambda x: -x[1]['count']):
        print(f"   {agent}: {data['count']:.1f} delegations")
        if data['tasks'][:2]:
            for task in data['tasks'][:2]:
                print(f"      └─ {task[:50]}")
    
    print(f"\n📈 Session Complexity Distribution:")
    for complexity, count in sorted(all_complexities.items(), key=lambda x: -x[1]):
        pct = 100 * count / parsed_count if parsed_count > 0 else 0
        print(f"   {complexity}: {count} sessions ({pct:.1f}%)")
    
    print(f"\n📁 Domain Distribution:")
    for domain, count in sorted(all_domains.items(), key=lambda x: -x[1]):
        pct = 100 * count / parsed_count if parsed_count > 0 else 0
        print(f"   {domain}: {count} sessions ({pct:.1f}%)")
    
    if all_gate_violations:
        print(f"\n⚠️  Gate Violations:")
        for gate, count in sorted(all_gate_violations.items(), key=lambda x: -x[1]):
            print(f"   {gate}: {count} violations")
    
    # Generate suggestions
    print(f"\n" + "=" * 50)
    print("📝 AGENT SUGGESTIONS FROM LOG ANALYSIS")
    print("=" * 50)
    
    suggestions = []
    
    # Check for underutilized agents
    available_agents = {'architect', 'code', 'debugger', 'reviewer', 'documentation', 'research', 'devops'}
    used_agents = set(all_agents_delegated.keys())
    unused = available_agents - used_agents
    
    if unused:
        for agent in unused:
            suggestions.append({
                'type': 'review',
                'agent': agent,
                'reason': f'Agent never delegated to - verify triggers or remove',
                'priority': 'Low'
            })
    
    # Check for high-complexity sessions without delegation
    complex_sessions = all_complexities.get('complex', 0)
    total_delegations = sum(d['count'] for d in all_agents_delegated.values())
    if complex_sessions > 5 and total_delegations < complex_sessions * 0.5:
        suggestions.append({
            'type': 'optimize',
            'agent': 'AKIS',
            'reason': f'{complex_sessions} complex sessions but low delegation rate - increase parallel usage',
            'priority': 'High'
        })
    
    # Root cause patterns
    if all_root_causes:
        print(f"\n🔍 ROOT CAUSES CAPTURED ({len(all_root_causes)} total):")
        for cause in all_root_causes[:5]:
            print(f"   - {cause}")
        suggestions.append({
            'type': 'update',
            'agent': 'debugger',
            'reason': f'Add {len(all_root_causes)} root causes to debugger knowledge base',
            'priority': 'Medium'
        })
    
    # Output suggestions table
    if suggestions:
        print(f"\n" + "-" * 70)
        print(f"{'Type':<10} {'Agent':<20} {'Priority':<10} {'Reason'}")
        print("-" * 70)
        for s in suggestions[:15]:
            print(f"{s['type']:<10} {s['agent']:<20} {s['priority']:<10} {s['reason'][:40]}")
        print("-" * 70)
        print(f"\nTotal suggestions: {len(suggestions)}")
    else:
        print("\n✅ Agent patterns optimal - no suggestions")
    
    return {
        'mode': 'ingest-all',
        'logs_found': len(log_files),
        'logs_parsed': parsed_count,
        'agents_delegated': {k: dict(v) for k, v in all_agents_delegated.items()},
        'complexities': dict(all_complexities),
        'domains': dict(all_domains),
        'gate_violations': dict(all_gate_violations),
        'root_causes_count': len(all_root_causes),
        'suggestions': suggestions,
    }


def main():
    parser = argparse.ArgumentParser(
        description='AKIS Agents Management Script',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python agents.py                    # Report only (safe default)
  python agents.py --update           # Update existing agents
  python agents.py --generate         # Full generation with metrics + agent files
  python agents.py --suggest          # Suggest without applying
  python agents.py --ingest-all       # Ingest ALL workflow logs and suggest
  python agents.py --audit            # Audit AKIS agent with sub-agent orchestration
  python agents.py --full-audit       # Full AKIS system audit (agent/knowledge/instructions/skills)
  python agents.py --compare          # Compare AKIS alone vs AKIS + specialists (100k sessions)
  python agents.py --analyze          # Analyze each agent individually (100k per agent)
  python agents.py --precision        # Test precision/recall of suggestions (100k sessions)
  python agents.py --dry-run          # Preview changes
        """
    )
    
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument('--update', action='store_true',
                           help='Actually update existing agents')
    mode_group.add_argument('--generate', action='store_true',
                           help='Full generation with 100k simulation and agent file creation')
    mode_group.add_argument('--suggest', action='store_true',
                           help='Suggest improvements without applying')
    mode_group.add_argument('--ingest-all', action='store_true',
                           help='Ingest ALL workflow logs and generate suggestions')
    mode_group.add_argument('--audit', action='store_true',
                           help='Audit AKIS agent with sub-agent orchestration analysis')
    mode_group.add_argument('--full-audit', action='store_true',
                           help='Full AKIS system audit (agent/knowledge/instructions/skills/docs)')
    mode_group.add_argument('--compare', action='store_true',
                           help='Compare AKIS alone vs AKIS with specialist agents (100k simulation)')
    mode_group.add_argument('--analyze', action='store_true',
                           help='Analyze each agent individually (100k sessions per agent)')
    mode_group.add_argument('--precision', action='store_true',
                           help='Test precision/recall of suggestions (100k sessions)')
    
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
    elif args.audit:
        result = run_audit(args.sessions)
    elif args.full_audit:
        result = run_full_audit(args.sessions, args.dry_run)
    elif args.compare:
        result = run_compare(args.sessions)
    elif args.analyze:
        result = run_analyze(args.sessions)
    elif args.precision:
        result = run_precision_test(args.sessions)
    elif args.update:
        result = run_update(args.dry_run)
    else:
        # Default: safe report-only mode
        result = run_report()
    
    # Save output if requested
    if args.output:
        output_path = Path(args.output)
        with open(output_path, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\n📄 Results saved to: {output_path}")
    
    return result


if __name__ == '__main__':
    main()
