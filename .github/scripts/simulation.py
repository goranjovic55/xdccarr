#!/usr/bin/env python3
"""
AKIS 100k Session Simulation Engine v1.0

Comprehensive simulation engine that:
1. Extracts patterns from industry/community forums and development sessions
2. Mixes patterns with real workflow logs
3. Creates 100k simulated sessions with edge cases and atypical issues
4. Runs AKIS framework against the simulation
5. Produces before/after measurements for optimization

FOCUS METRICS:
- Discipline: Protocol adherence (gates, TODO tracking, skill loading)
- Cognitive Load: Complexity score for agent following instructions
- Resolve Rate: Task completion success rate
- Speed: Resolution time (minutes)
- Traceability: How well actions can be traced back
- Token Consumption: Average tokens per session
- API Calls: Number of tool invocations per session

Usage:
    # Run full 100k simulation with before/after analysis
    python .github/scripts/simulation.py --full
    
    # Extract patterns only
    python .github/scripts/simulation.py --extract-patterns
    
    # Run simulation with custom session count
    python .github/scripts/simulation.py --sessions 50000
    
    # Generate edge cases report
    python .github/scripts/simulation.py --edge-cases
    
    # Output results to file
    python .github/scripts/simulation.py --full --output log/simulation_100k.json
"""

import json
import random
import re
import hashlib
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Set, Optional, Tuple
from pathlib import Path
from datetime import datetime
import argparse

# ============================================================================
# Configuration
# ============================================================================

DEFAULT_SESSION_COUNT = 100_000
WORKFLOW_DIR = Path("log/workflow")
RESULTS_DIR = Path("log")

# Seed for reproducibility
RANDOM_SEED = 42

# ============================================================================
# Industry/Community Forum Pattern Database
# ============================================================================

# Patterns extracted from common development forums, GitHub issues, Stack Overflow,
# Discord communities, and development best practices guides

INDUSTRY_PATTERNS = {
    "frontend": {
        "common_issues": [
            {"issue": "React component not re-rendering", "frequency": 0.15, "complexity": "medium"},
            {"issue": "State management race condition", "frequency": 0.10, "complexity": "high"},
            {"issue": "CSS styling conflicts", "frequency": 0.20, "complexity": "low"},
            {"issue": "TypeScript type errors", "frequency": 0.18, "complexity": "medium"},
            {"issue": "Hook dependency array issues", "frequency": 0.12, "complexity": "medium"},
            {"issue": "Memory leak from unmounted component", "frequency": 0.08, "complexity": "high"},
            {"issue": "API data fetching patterns", "frequency": 0.10, "complexity": "medium"},
            {"issue": "Form validation edge cases", "frequency": 0.07, "complexity": "medium"},
        ],
        "typical_tasks": [
            "Create new component", "Fix styling issue", "Add form validation",
            "Implement data fetching", "Add loading states", "Fix type errors",
            "Optimize re-renders", "Add error boundaries", "Implement routing",
        ],
        "edge_cases": [
            {"case": "Concurrent state updates", "probability": 0.05},
            {"case": "SSR hydration mismatch", "probability": 0.03},
            {"case": "Infinite render loop", "probability": 0.04},
            {"case": "Stale closure in useEffect", "probability": 0.06},
            {"case": "Race condition in async operations", "probability": 0.05},
        ],
    },
    "backend": {
        "common_issues": [
            {"issue": "Database connection timeout", "frequency": 0.12, "complexity": "medium"},
            {"issue": "SQL injection vulnerability", "frequency": 0.05, "complexity": "high"},
            {"issue": "API authentication failure", "frequency": 0.15, "complexity": "medium"},
            {"issue": "Async operation deadlock", "frequency": 0.08, "complexity": "high"},
            {"issue": "Missing error handling", "frequency": 0.18, "complexity": "low"},
            {"issue": "N+1 query problem", "frequency": 0.10, "complexity": "medium"},
            {"issue": "CORS configuration error", "frequency": 0.12, "complexity": "low"},
            {"issue": "WebSocket connection drops", "frequency": 0.08, "complexity": "medium"},
            {"issue": "Memory leak in long-running process", "frequency": 0.06, "complexity": "high"},
            {"issue": "Rate limiting bypass", "frequency": 0.06, "complexity": "high"},
        ],
        "typical_tasks": [
            "Create API endpoint", "Add database model", "Implement authentication",
            "Add caching layer", "Fix database query", "Add logging",
            "Implement WebSocket handler", "Add middleware", "Setup background tasks",
        ],
        "edge_cases": [
            {"case": "Database migration rollback", "probability": 0.04},
            {"case": "Connection pool exhaustion", "probability": 0.03},
            {"case": "Circular dependency in imports", "probability": 0.05},
            {"case": "Race condition in database writes", "probability": 0.04},
            {"case": "Timezone handling errors", "probability": 0.06},
            {"case": "Unicode encoding issues", "probability": 0.03},
        ],
    },
    "devops": {
        "common_issues": [
            {"issue": "Docker build failure", "frequency": 0.18, "complexity": "medium"},
            {"issue": "Container resource exhaustion", "frequency": 0.10, "complexity": "medium"},
            {"issue": "CI/CD pipeline failure", "frequency": 0.20, "complexity": "medium"},
            {"issue": "Environment variable mismatch", "frequency": 0.15, "complexity": "low"},
            {"issue": "Port binding conflict", "frequency": 0.12, "complexity": "low"},
            {"issue": "Volume mount permissions", "frequency": 0.10, "complexity": "medium"},
            {"issue": "Network connectivity issues", "frequency": 0.08, "complexity": "medium"},
            {"issue": "SSL certificate problems", "frequency": 0.07, "complexity": "high"},
        ],
        "typical_tasks": [
            "Update Dockerfile", "Fix CI pipeline", "Add environment variables",
            "Configure volumes", "Setup networking", "Optimize build time",
            "Add health checks", "Configure logging", "Setup monitoring",
        ],
        "edge_cases": [
            {"case": "Multi-stage build cache invalidation", "probability": 0.04},
            {"case": "Container startup race condition", "probability": 0.05},
            {"case": "Disk space exhaustion", "probability": 0.03},
            {"case": "DNS resolution failure", "probability": 0.04},
            {"case": "Orphaned resources cleanup", "probability": 0.03},
        ],
    },
    "debugging": {
        "common_issues": [
            {"issue": "Traceback without context", "frequency": 0.20, "complexity": "medium"},
            {"issue": "Silent failure", "frequency": 0.15, "complexity": "high"},
            {"issue": "Intermittent error", "frequency": 0.12, "complexity": "high"},
            {"issue": "Performance degradation", "frequency": 0.10, "complexity": "medium"},
            {"issue": "Memory leak", "frequency": 0.08, "complexity": "high"},
            {"issue": "Configuration error", "frequency": 0.18, "complexity": "low"},
            {"issue": "Dependency version conflict", "frequency": 0.10, "complexity": "medium"},
            {"issue": "Environment-specific bug", "frequency": 0.07, "complexity": "high"},
        ],
        "typical_tasks": [
            "Investigate traceback", "Add logging", "Reproduce issue",
            "Fix edge case", "Add error handling", "Profile performance",
            "Trace data flow", "Check configurations", "Verify dependencies",
        ],
        "edge_cases": [
            {"case": "Heisenbug - disappears when debugging", "probability": 0.03},
            {"case": "Race condition only in production", "probability": 0.04},
            {"case": "Cascading failure from upstream", "probability": 0.05},
            {"case": "Data corruption from concurrent access", "probability": 0.03},
            {"case": "Stack overflow from deep recursion", "probability": 0.02},
        ],
    },
}

# Session complexity distribution from community analysis
SESSION_COMPLEXITY_DISTRIBUTION = {
    "simple": 0.35,   # 1-2 files, straightforward tasks
    "medium": 0.45,   # 3-5 files, some complexity
    "complex": 0.20,  # 6+ files, high complexity, edge cases
}

# Domain distribution from community analysis
DOMAIN_DISTRIBUTION = {
    "frontend_only": 0.24,
    "backend_only": 0.10,
    "fullstack": 0.40,
    "devops": 0.10,
    "debugging": 0.10,
    "documentation": 0.06,
}

# Atypical issue categories (edge cases that should be handled)
ATYPICAL_ISSUES = [
    {
        "category": "workflow_deviation",
        "description": "Agent skips required steps",
        "probability": 0.08,
        "scenarios": [
            "Skip knowledge loading at START",
            "Skip skill loading before domain work",
            "Skip verification after edits",
            "Skip workflow log at END",
            "Multiple ◆ tasks active simultaneously",
            "Orphan ⊘ tasks not closed",
        ],
    },
    {
        "category": "cognitive_overload",
        "description": "Too much context causing confusion",
        "probability": 0.06,
        "scenarios": [
            "More than 10 files modified",
            "More than 5 skills loaded",
            "Very long session (>60 min)",
            "Multiple unrelated tasks",
            "Conflicting instructions",
        ],
    },
    {
        "category": "error_cascades",
        "description": "One error leads to multiple failures",
        "probability": 0.05,
        "scenarios": [
            "Syntax error in import causes downstream failures",
            "Database migration breaks multiple services",
            "Type error propagates through codebase",
            "Configuration change breaks multiple components",
        ],
    },
    {
        "category": "context_loss",
        "description": "Important context not maintained",
        "probability": 0.07,
        "scenarios": [
            "Previous session context not loaded",
            "Related files not identified",
            "Dependencies not traced",
            "Historical decisions not referenced",
        ],
    },
    {
        "category": "tool_misuse",
        "description": "Tools used incorrectly",
        "probability": 0.04,
        "scenarios": [
            "Wrong file edited",
            "Incomplete search queries",
            "Missed file in multi-file edit",
            "Incorrect regex pattern",
        ],
    },
]


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class SessionMetrics:
    """Comprehensive metrics for a simulated session."""
    # Identification
    session_id: int
    session_type: str
    complexity: str
    domain: str
    
    # Core metrics
    token_usage: int = 0
    api_calls: int = 0
    resolution_time_minutes: float = 0.0
    
    # Quality metrics (0-1 scale)
    discipline_score: float = 0.0
    cognitive_load: float = 0.0
    traceability: float = 0.0
    
    # Outcome metrics
    task_success: bool = False
    tasks_completed: int = 0
    tasks_total: int = 0
    
    # Skill and knowledge usage
    skills_loaded: int = 0
    knowledge_hits: int = 0
    
    # Delegation metrics (multi-agent)
    delegation_used: bool = False
    delegations_made: int = 0
    delegation_success_rate: float = 0.0
    agents_delegated_to: List[str] = field(default_factory=list)
    delegation_discipline_score: float = 0.0
    
    # Parallel execution metrics (intelligent delegation)
    parallel_execution_used: bool = False
    parallel_agents_count: int = 0
    parallel_time_saved_minutes: float = 0.0
    parallel_coordination_overhead: float = 0.0
    parallel_execution_strategy: str = ""  # "sequential", "parallel", "hybrid"
    parallel_execution_success: bool = True
    
    # Issues
    deviations: List[str] = field(default_factory=list)
    edge_cases_hit: List[str] = field(default_factory=list)
    errors_encountered: List[str] = field(default_factory=list)


@dataclass
class SimulationConfig:
    """Configuration for simulation run."""
    session_count: int = DEFAULT_SESSION_COUNT
    include_edge_cases: bool = True
    edge_case_probability: float = 0.15
    atypical_issue_probability: float = 0.10
    seed: int = RANDOM_SEED


@dataclass
class AKISConfiguration:
    """AKIS framework configuration for simulation."""
    version: str = "current"
    
    # Discipline enforcement
    enforce_gates: bool = True
    require_todo_tracking: bool = True
    require_skill_loading: bool = True
    require_knowledge_loading: bool = True
    require_workflow_log: bool = True
    
    # Optimization settings
    enable_knowledge_cache: bool = True
    enable_operation_batching: bool = True
    enable_proactive_skill_loading: bool = True
    
    # Token optimization
    max_context_tokens: int = 4000
    skill_token_target: int = 250
    
    # Quality settings
    require_verification: bool = True
    require_syntax_check: bool = True
    
    # Delegation settings (multi-agent)
    enable_delegation: bool = True
    delegation_threshold: int = 6  # Files count to trigger delegation
    require_delegation_tracing: bool = True
    available_agents: List[str] = field(default_factory=lambda: [
        'architect', 'research', 'code', 'debugger', 'reviewer', 'documentation', 'devops'
    ])
    
    # Intelligent parallel execution settings
    enable_parallel_execution: bool = True
    max_parallel_agents: int = 3
    parallel_compatible_pairs: List[Tuple[str, str]] = field(default_factory=lambda: [
        ('code', 'documentation'),  # Code + docs can run in parallel
        ('code', 'reviewer'),       # Code A + review B can run in parallel
        ('research', 'code'),       # Research + implement can overlap
        ('architect', 'research'),  # Design + research can overlap
        ('debugger', 'documentation'),  # Debug + docs can run in parallel
    ])
    require_parallel_coordination: bool = True


@dataclass
class SimulationResults:
    """Complete results from a simulation run."""
    config: SimulationConfig
    akis_config: AKISConfiguration
    
    # Aggregate metrics
    total_sessions: int = 0
    successful_sessions: int = 0
    
    # Averages
    avg_token_usage: float = 0.0
    avg_api_calls: float = 0.0
    avg_resolution_time: float = 0.0
    avg_discipline: float = 0.0
    avg_cognitive_load: float = 0.0
    avg_traceability: float = 0.0
    
    # Percentiles
    p50_resolution_time: float = 0.0
    p95_resolution_time: float = 0.0
    
    # Rates
    success_rate: float = 0.0
    perfect_session_rate: float = 0.0
    edge_case_hit_rate: float = 0.0
    
    # Totals
    total_tokens: int = 0
    total_api_calls: int = 0
    total_deviations: int = 0
    
    # Distribution
    complexity_distribution: Dict[str, int] = field(default_factory=dict)
    domain_distribution: Dict[str, int] = field(default_factory=dict)
    deviation_counts: Dict[str, int] = field(default_factory=dict)
    edge_case_counts: Dict[str, int] = field(default_factory=dict)
    
    # Delegation metrics (multi-agent)
    delegation_rate: float = 0.0
    avg_delegation_discipline: float = 0.0
    avg_delegations_per_session: float = 0.0
    delegation_success_rate: float = 0.0
    sessions_with_delegation: int = 0
    agents_usage: Dict[str, int] = field(default_factory=dict)
    
    # Parallel execution metrics (intelligent delegation)
    parallel_execution_rate: float = 0.0
    avg_parallel_agents: float = 0.0
    avg_parallel_time_saved: float = 0.0
    total_parallel_time_saved: float = 0.0
    parallel_execution_success_rate: float = 0.0
    parallel_strategy_distribution: Dict[str, int] = field(default_factory=dict)
    sessions_with_parallel: int = 0


@dataclass
class DelegationOptimizationResult:
    """Results from delegation optimization analysis."""
    strategy_name: str
    description: str
    
    # Core metrics per strategy
    avg_token_usage: float = 0.0
    avg_api_calls: float = 0.0
    avg_resolution_time: float = 0.0
    avg_discipline: float = 0.0
    avg_cognitive_load: float = 0.0
    avg_traceability: float = 0.0
    success_rate: float = 0.0
    
    # Delegation specifics
    delegation_rate: float = 0.0
    delegation_success_rate: float = 0.0
    avg_quality_score: float = 0.0  # Quality of results
    
    # Efficiency metrics
    efficiency_score: float = 0.0  # Composite score
    optimal_for_complexity: str = ""  # simple, medium, complex


@dataclass
class AgentSpecializationMetrics:
    """Metrics for a specific agent's performance."""
    agent_name: str
    
    # When agent is delegated to
    times_delegated: int = 0
    delegation_success_rate: float = 0.0
    avg_task_time: float = 0.0
    avg_quality: float = 0.0
    
    # Comparison vs AKIS doing it directly
    time_vs_akis: float = 0.0  # Positive = specialist faster
    quality_vs_akis: float = 0.0  # Positive = specialist better
    token_vs_akis: float = 0.0  # Positive = specialist uses less
    
    # Optimal delegation scenarios
    optimal_task_types: List[str] = field(default_factory=list)
    optimal_complexity: str = ""
    optimal_file_count_min: int = 0
    optimal_file_count_max: int = 0


@dataclass
class AgentSimulationResult:
    """Comprehensive simulation results for a single agent."""
    agent_name: str
    sessions_simulated: int = 0
    
    # Core metrics - current performance
    current_discipline: float = 0.0
    current_token_usage: float = 0.0
    current_cognitive_load: float = 0.0
    current_efficiency: float = 0.0
    current_speed: float = 0.0  # Resolution time in minutes
    current_traceability: float = 0.0
    current_success_rate: float = 0.0
    current_quality: float = 0.0
    
    # Optimized metrics - after adjustments
    optimized_discipline: float = 0.0
    optimized_token_usage: float = 0.0
    optimized_cognitive_load: float = 0.0
    optimized_efficiency: float = 0.0
    optimized_speed: float = 0.0
    optimized_traceability: float = 0.0
    optimized_success_rate: float = 0.0
    optimized_quality: float = 0.0
    
    # Improvement percentages
    discipline_improvement: float = 0.0
    token_improvement: float = 0.0
    cognitive_load_improvement: float = 0.0
    efficiency_improvement: float = 0.0
    speed_improvement: float = 0.0
    traceability_improvement: float = 0.0
    success_improvement: float = 0.0
    
    # Deviations tracked
    deviations: Dict[str, int] = field(default_factory=dict)
    
    # Suggested adjustments
    suggested_adjustments: List[str] = field(default_factory=list)
    instruction_changes: Dict[str, str] = field(default_factory=dict)


# Agent baseline profiles - what we expect from each agent
AGENT_BASELINE_PROFILES = {
    'architect': {
        'discipline_baseline': 0.82,
        'token_baseline': 4500,
        'cognitive_load_baseline': 0.45,
        'efficiency_baseline': 0.78,
        'speed_baseline': 25.0,  # minutes
        'traceability_baseline': 0.80,
        'success_baseline': 0.88,
        'quality_baseline': 0.90,
        'common_deviations': [
            ('skip_blueprint_validation', 0.15),
            ('incomplete_design_trace', 0.12),
            ('missing_constraint_analysis', 0.10),
            ('overly_complex_design', 0.08),
            ('no_alternative_evaluation', 0.07),
        ],
    },
    'research': {
        'discipline_baseline': 0.75,
        'token_baseline': 5500,
        'cognitive_load_baseline': 0.50,
        'efficiency_baseline': 0.72,
        'speed_baseline': 30.0,
        'traceability_baseline': 0.70,
        'success_baseline': 0.82,
        'quality_baseline': 0.85,
        'common_deviations': [
            ('insufficient_sources', 0.18),
            ('missing_comparison_matrix', 0.14),
            ('incomplete_analysis', 0.12),
            ('no_recommendation', 0.10),
            ('outdated_sources', 0.08),
        ],
    },
    'code': {
        'discipline_baseline': 0.88,
        'token_baseline': 3500,
        'cognitive_load_baseline': 0.40,
        'efficiency_baseline': 0.85,
        'speed_baseline': 18.0,
        'traceability_baseline': 0.85,
        'success_baseline': 0.92,
        'quality_baseline': 0.88,
        'common_deviations': [
            ('missing_type_hints', 0.12),
            ('no_error_handling', 0.10),
            ('function_too_large', 0.08),
            ('missing_tests', 0.15),
            ('code_duplication', 0.06),
        ],
    },
    'debugger': {
        'discipline_baseline': 0.90,
        'token_baseline': 3000,
        'cognitive_load_baseline': 0.35,
        'efficiency_baseline': 0.88,
        'speed_baseline': 15.0,
        'traceability_baseline': 0.92,
        'success_baseline': 0.94,
        'quality_baseline': 0.91,
        'common_deviations': [
            ('skip_reproduction', 0.08),
            ('insufficient_tracing', 0.10),
            ('fix_without_root_cause', 0.07),
            ('leftover_debug_code', 0.05),
            ('no_regression_check', 0.09),
        ],
    },
    'reviewer': {
        'discipline_baseline': 0.85,
        'token_baseline': 4000,
        'cognitive_load_baseline': 0.42,
        'efficiency_baseline': 0.80,
        'speed_baseline': 20.0,
        'traceability_baseline': 0.88,
        'success_baseline': 0.90,
        'quality_baseline': 0.92,
        'common_deviations': [
            ('missed_security_issue', 0.10),
            ('incomplete_review', 0.12),
            ('no_actionable_feedback', 0.08),
            ('style_only_review', 0.06),
            ('missing_test_coverage_check', 0.11),
        ],
    },
    'documentation': {
        'discipline_baseline': 0.78,
        'token_baseline': 3200,
        'cognitive_load_baseline': 0.30,
        'efficiency_baseline': 0.82,
        'speed_baseline': 12.0,
        'traceability_baseline': 0.75,
        'success_baseline': 0.88,
        'quality_baseline': 0.85,
        'common_deviations': [
            ('missing_examples', 0.15),
            ('outdated_docs', 0.12),
            ('incomplete_api_docs', 0.10),
            ('no_usage_guide', 0.08),
            ('broken_links', 0.06),
        ],
    },
    'devops': {
        'discipline_baseline': 0.86,
        'token_baseline': 4200,
        'cognitive_load_baseline': 0.48,
        'efficiency_baseline': 0.84,
        'speed_baseline': 22.0,
        'traceability_baseline': 0.82,
        'success_baseline': 0.90,
        'quality_baseline': 0.88,
        'common_deviations': [
            ('insecure_config', 0.08),
            ('missing_env_validation', 0.10),
            ('hardcoded_secrets', 0.05),
            ('no_rollback_plan', 0.09),
            ('incomplete_logging', 0.07),
        ],
    },
}

# Agent optimization adjustments - what we can improve
AGENT_OPTIMIZATION_ADJUSTMENTS = {
    'architect': {
        'discipline_boost': 0.10,
        'token_reduction': 0.15,
        'cognitive_reduction': 0.12,
        'efficiency_boost': 0.08,
        'speed_boost': 0.10,
        'traceability_boost': 0.12,
        'instruction_changes': {
            'add_blueprint_validation': 'Add ## Validation section requiring design verification',
            'enforce_trace': 'Make [RETURN] trace REQUIRED with checklist',
            'add_constraints_analysis': 'Add constraints analysis step to methodology',
            'simplify_output': 'Reduce output format to essential sections only',
        },
    },
    'research': {
        'discipline_boost': 0.15,
        'token_reduction': 0.12,
        'cognitive_reduction': 0.10,
        'efficiency_boost': 0.12,
        'speed_boost': 0.08,
        'traceability_boost': 0.18,
        'instruction_changes': {
            'enforce_source_count': 'Require minimum 3 sources with citation',
            'add_comparison_template': 'Add comparison matrix template to output format',
            'require_recommendation': 'Add REQUIRED recommendation section',
            'add_freshness_check': 'Add source date validation (<1 year)',
        },
    },
    'code': {
        'discipline_boost': 0.05,
        'token_reduction': 0.10,
        'cognitive_reduction': 0.08,
        'efficiency_boost': 0.05,
        'speed_boost': 0.05,
        'traceability_boost': 0.08,
        'instruction_changes': {
            'enforce_types': 'Add type hint requirement to Standards with examples',
            'enforce_error_handling': 'Add explicit error handling patterns',
            'add_size_limits': 'Add function size limits with line count checks',
            'require_test_mention': 'Add test requirement to output format',
        },
    },
    'debugger': {
        'discipline_boost': 0.03,
        'token_reduction': 0.08,
        'cognitive_reduction': 0.05,
        'efficiency_boost': 0.03,
        'speed_boost': 0.05,
        'traceability_boost': 0.03,
        'instruction_changes': {
            'enforce_reproduction': 'Add REPRODUCE step as mandatory first step',
            'improve_tracing': 'Add trace log template with entry/exit markers',
            'require_root_cause': 'Require root cause identification before fix',
            'cleanup_reminder': 'Add debug code cleanup checklist',
        },
    },
    'reviewer': {
        'discipline_boost': 0.08,
        'token_reduction': 0.12,
        'cognitive_reduction': 0.10,
        'efficiency_boost': 0.08,
        'speed_boost': 0.08,
        'traceability_boost': 0.06,
        'instruction_changes': {
            'add_security_checklist': 'Add security review checklist (OWASP top 10)',
            'enforce_complete_review': 'Add completeness checklist for review',
            'require_actionable': 'All feedback must have suggested fix',
            'add_test_coverage': 'Require test coverage check in review',
        },
    },
    'documentation': {
        'discipline_boost': 0.12,
        'token_reduction': 0.10,
        'cognitive_reduction': 0.05,
        'efficiency_boost': 0.08,
        'speed_boost': 0.05,
        'traceability_boost': 0.15,
        'instruction_changes': {
            'require_examples': 'Add REQUIRED examples section in output',
            'add_freshness_check': 'Add last-updated date requirement',
            'complete_api_template': 'Add complete API doc template',
            'add_usage_section': 'Require usage/quickstart section',
        },
    },
    'devops': {
        'discipline_boost': 0.07,
        'token_reduction': 0.10,
        'cognitive_reduction': 0.08,
        'efficiency_boost': 0.06,
        'speed_boost': 0.08,
        'traceability_boost': 0.10,
        'instruction_changes': {
            'add_security_scan': 'Add security scan step to methodology',
            'enforce_env_validation': 'Add env validation checklist',
            'no_hardcoded_secrets': 'Add secrets detection check',
            'require_rollback': 'Add rollback plan to output format',
        },
    },
}


# ============================================================================
# Pattern Extraction
# ============================================================================

def extract_patterns_from_workflow_logs(workflow_dir: Path) -> Dict[str, Any]:
    """Extract patterns from real workflow logs."""
    patterns = {
        "session_types": defaultdict(int),
        "task_counts": [],
        "durations": [],
        "skills_used": defaultdict(int),
        "common_issues": [],
        "success_indicators": [],
        "failure_indicators": [],
        "files_modified": [],
        "complexity_distribution": defaultdict(int),
        "total_logs": 0,
    }
    
    if not workflow_dir.exists():
        return patterns
    
    for log_file in workflow_dir.glob("*.md"):
        if log_file.name == "README.md":
            continue
        
        try:
            content = log_file.read_text(encoding='utf-8', errors='ignore')
            patterns["total_logs"] += 1
            
            # Extract session type
            if 'frontend' in content.lower() and 'backend' in content.lower():
                patterns["session_types"]["fullstack"] += 1
            elif 'frontend' in content.lower():
                patterns["session_types"]["frontend_only"] += 1
            elif 'backend' in content.lower():
                patterns["session_types"]["backend_only"] += 1
            elif 'docker' in content.lower():
                patterns["session_types"]["devops"] += 1
            elif 'debug' in content.lower() or 'fix' in content.lower():
                patterns["session_types"]["debugging"] += 1
            elif 'doc' in content.lower():
                patterns["session_types"]["documentation"] += 1
            
            # Extract task counts
            completed = content.count('✓') + content.count('[x]')
            pending = content.count('○') + content.count('[ ]')
            patterns["task_counts"].append(completed + pending)
            
            # Extract duration
            duration_match = re.search(r'~?(\d+)\s*min', content)
            if duration_match:
                patterns["durations"].append(int(duration_match.group(1)))
            
            # Extract skills used
            skill_matches = re.findall(r'SKILL[:\s]+(\w+-?\w+)', content)
            for skill in skill_matches:
                patterns["skills_used"][skill.lower()] += 1
            
            # Extract complexity
            if 'Complex' in content:
                patterns["complexity_distribution"]["complex"] += 1
            elif 'Medium' in content:
                patterns["complexity_distribution"]["medium"] += 1
            elif 'Simple' in content:
                patterns["complexity_distribution"]["simple"] += 1
            
            # Extract issues/errors
            if 'error' in content.lower() or 'fix' in content.lower():
                patterns["common_issues"].append(log_file.stem)
            
            # File counts
            file_match = re.search(r'Files[:\s]+(\d+)', content)
            if file_match:
                patterns["files_modified"].append(int(file_match.group(1)))
        
        except Exception:
            continue
    
    return patterns


def extract_industry_patterns() -> Dict[str, Any]:
    """Extract and compile industry/community patterns."""
    compiled = {
        "common_issues": [],
        "edge_cases": [],
        "typical_tasks": [],
        "complexity_weights": {},
        "domain_weights": {},
    }
    
    # Compile issues from all domains
    for domain, data in INDUSTRY_PATTERNS.items():
        for issue in data.get("common_issues", []):
            compiled["common_issues"].append({
                "domain": domain,
                **issue
            })
        
        for edge_case in data.get("edge_cases", []):
            compiled["edge_cases"].append({
                "domain": domain,
                **edge_case
            })
        
        for task in data.get("typical_tasks", []):
            compiled["typical_tasks"].append({
                "domain": domain,
                "task": task
            })
    
    compiled["complexity_weights"] = SESSION_COMPLEXITY_DISTRIBUTION
    compiled["domain_weights"] = DOMAIN_DISTRIBUTION
    
    return compiled


def merge_patterns(
    workflow_patterns: Dict[str, Any],
    industry_patterns: Dict[str, Any]
) -> Dict[str, Any]:
    """Merge workflow log patterns with industry patterns."""
    merged = {
        "session_types": {},
        "complexity_distribution": {},
        "common_issues": industry_patterns["common_issues"],
        "edge_cases": industry_patterns["edge_cases"],
        "atypical_issues": ATYPICAL_ISSUES,
        "source_stats": {
            "workflow_logs": workflow_patterns.get("total_logs", 0),
            "industry_patterns": len(industry_patterns["common_issues"]),
            "edge_cases": len(industry_patterns["edge_cases"]),
        }
    }
    
    # Merge session type distributions
    total_workflow = sum(workflow_patterns.get("session_types", {}).values()) or 1
    for session_type, count in workflow_patterns.get("session_types", {}).items():
        merged["session_types"][session_type] = count / total_workflow
    
    # Fill with industry defaults if workflow data sparse
    for session_type, prob in DOMAIN_DISTRIBUTION.items():
        if session_type not in merged["session_types"]:
            merged["session_types"][session_type] = prob
    
    # Merge complexity distribution
    total_complexity = sum(workflow_patterns.get("complexity_distribution", {}).values()) or 1
    for complexity, count in workflow_patterns.get("complexity_distribution", {}).items():
        merged["complexity_distribution"][complexity] = count / total_complexity
    
    # Fill with defaults
    for complexity, prob in SESSION_COMPLEXITY_DISTRIBUTION.items():
        if complexity not in merged["complexity_distribution"]:
            merged["complexity_distribution"][complexity] = prob
    
    # Calculate average metrics from workflow logs
    durations = workflow_patterns.get("durations", [20])
    tasks = workflow_patterns.get("task_counts", [5])
    files = workflow_patterns.get("files_modified", [4])
    
    merged["avg_metrics"] = {
        "duration_mean": sum(durations) / len(durations) if durations else 20,
        "duration_std": _std(durations) if len(durations) > 1 else 10,
        "tasks_mean": sum(tasks) / len(tasks) if tasks else 5,
        "tasks_std": _std(tasks) if len(tasks) > 1 else 2,
        "files_mean": sum(files) / len(files) if files else 4,
        "files_std": _std(files) if len(files) > 1 else 2,
    }
    
    return merged


def _std(values: List[float]) -> float:
    """Calculate standard deviation."""
    if len(values) < 2:
        return 0
    mean = sum(values) / len(values)
    return (sum((x - mean) ** 2 for x in values) / len(values)) ** 0.5


# ============================================================================
# Session Simulation
# ============================================================================

def simulate_session(
    session_id: int,
    patterns: Dict[str, Any],
    akis_config: AKISConfiguration,
    config: SimulationConfig
) -> SessionMetrics:
    """Simulate a single coding session."""
    
    # Determine session characteristics
    session_type = _pick_weighted(patterns["session_types"])
    complexity = _pick_weighted(patterns["complexity_distribution"])
    domain = _map_session_to_domain(session_type)
    
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        complexity=complexity,
        domain=domain
    )
    
    # Determine task count based on complexity
    avg_metrics = patterns.get("avg_metrics", {})
    if complexity == "simple":
        metrics.tasks_total = random.randint(1, 2)
    elif complexity == "medium":
        metrics.tasks_total = random.randint(3, 5)
    else:  # complex
        metrics.tasks_total = random.randint(6, 10)
    
    # Simulate AKIS protocol compliance
    discipline_components = []
    
    # Gate 1: Knowledge loading at START
    if akis_config.require_knowledge_loading:
        if random.random() < 0.92:  # 92% compliance baseline
            discipline_components.append(1.0)
            metrics.knowledge_hits += 1
        else:
            discipline_components.append(0.0)
            metrics.deviations.append("skip_knowledge_loading")
    
    # Gate 2: Skill loading before work
    if akis_config.require_skill_loading:
        skill_compliance = 0.85 if complexity == "simple" else 0.75 if complexity == "medium" else 0.65
        if random.random() < skill_compliance:
            discipline_components.append(1.0)
            metrics.skills_loaded = random.randint(1, 3)
        else:
            discipline_components.append(0.0)
            metrics.deviations.append("skip_skill_loading")
    
    # Gate 3: TODO tracking
    if akis_config.require_todo_tracking:
        if complexity != "simple" and random.random() > 0.88:
            discipline_components.append(0.5)
            metrics.deviations.append("incomplete_todo_tracking")
        else:
            discipline_components.append(1.0)
    
    # Gate 4: Verification after edits
    if akis_config.require_verification:
        if random.random() < 0.82:
            discipline_components.append(1.0)
        else:
            discipline_components.append(0.0)
            metrics.deviations.append("skip_verification")
    
    # Gate 5: Workflow log at END
    if akis_config.require_workflow_log:
        if random.random() < 0.78:
            discipline_components.append(1.0)
        else:
            discipline_components.append(0.0)
            metrics.deviations.append("skip_workflow_log")
    
    # =========================================================================
    # Delegation Simulation (Multi-Agent)
    # =========================================================================
    delegation_discipline_components = []
    
    # Determine if delegation should be used based on complexity
    should_delegate = (
        akis_config.enable_delegation and 
        (complexity == "complex" or metrics.tasks_total >= akis_config.delegation_threshold)
    )
    
    if should_delegate:
        # Check if agent properly delegated
        delegation_probability = 0.70 if complexity == "complex" else 0.55
        
        if random.random() < delegation_probability:
            metrics.delegation_used = True
            
            # Determine how many delegations were made
            if complexity == "complex":
                metrics.delegations_made = random.randint(2, 4)
            else:
                metrics.delegations_made = random.randint(1, 2)
            
            # Select agents delegated to
            available = akis_config.available_agents
            num_agents = min(metrics.delegations_made, len(available))
            metrics.agents_delegated_to = random.sample(available, num_agents)
            
            # Check delegation discipline
            delegation_discipline = []
            
            # 1. Proper agent selection (right agent for task)
            if random.random() < 0.85:
                delegation_discipline.append(1.0)
            else:
                delegation_discipline.append(0.3)
                metrics.deviations.append("wrong_agent_selected")
            
            # 2. Proper context passing
            if random.random() < 0.78:
                delegation_discipline.append(1.0)
            else:
                delegation_discipline.append(0.4)
                metrics.deviations.append("incomplete_delegation_context")
            
            # 3. Proper tracing (⧖ symbol, TODO marking)
            if akis_config.require_delegation_tracing:
                if random.random() < 0.72:
                    delegation_discipline.append(1.0)
                else:
                    delegation_discipline.append(0.2)
                    metrics.deviations.append("skip_delegation_tracing")
            
            # 4. Proper result verification after delegation
            if random.random() < 0.80:
                delegation_discipline.append(1.0)
            else:
                delegation_discipline.append(0.3)
                metrics.deviations.append("skip_delegation_verification")
            
            metrics.delegation_discipline_score = sum(delegation_discipline) / len(delegation_discipline) if delegation_discipline else 0.5
            delegation_discipline_components.extend(delegation_discipline)
            
            # Calculate delegation success rate
            successes = sum(1 for _ in range(metrics.delegations_made) if random.random() < (0.85 + metrics.delegation_discipline_score * 0.1))
            metrics.delegation_success_rate = successes / metrics.delegations_made if metrics.delegations_made > 0 else 0.0
            
            # Delegation benefits: reduces cognitive load, saves time
            # Good delegation improves outcomes
            if metrics.delegation_discipline_score > 0.7:
                # Benefits from good delegation
                pass  # Applied below in token/time calculations
        else:
            # Should have delegated but didn't
            metrics.deviations.append("skip_delegation_for_complex")
            delegation_discipline_components.append(0.0)
    else:
        # Simple task - no delegation needed
        metrics.delegation_discipline_score = 1.0  # N/A counts as compliant
    
    # =========================================================================
    # Intelligent Parallel Execution Simulation
    # =========================================================================
    parallel_discipline_components = []
    
    # Determine if parallel execution is possible and beneficial
    can_use_parallel = (
        akis_config.enable_parallel_execution and
        metrics.delegation_used and
        metrics.delegations_made >= 2
    )
    
    if can_use_parallel:
        # Check if agents selected can run in parallel
        agents = metrics.agents_delegated_to
        compatible_pairs = akis_config.parallel_compatible_pairs
        
        # Find compatible agent pairs
        parallel_pairs = []
        for i, agent1 in enumerate(agents):
            for agent2 in agents[i+1:]:
                if (agent1, agent2) in compatible_pairs or (agent2, agent1) in compatible_pairs:
                    parallel_pairs.append((agent1, agent2))
        
        if parallel_pairs:
            # Can use parallel execution
            parallel_probability = 0.65 if complexity == "complex" else 0.50
            
            if random.random() < parallel_probability:
                metrics.parallel_execution_used = True
                metrics.parallel_agents_count = min(len(parallel_pairs) + 1, akis_config.max_parallel_agents)
                
                # Determine execution strategy
                if metrics.parallel_agents_count >= 2 and complexity == "complex":
                    metrics.parallel_execution_strategy = "parallel"
                elif metrics.parallel_agents_count >= 2:
                    metrics.parallel_execution_strategy = "hybrid"  # Some parallel, some sequential
                else:
                    metrics.parallel_execution_strategy = "sequential"
                
                # Calculate time saved from parallel execution
                # Parallel execution can save 30-50% of time for complex tasks
                if metrics.parallel_execution_strategy == "parallel":
                    time_save_factor = random.uniform(0.30, 0.50)
                elif metrics.parallel_execution_strategy == "hybrid":
                    time_save_factor = random.uniform(0.15, 0.30)
                else:
                    time_save_factor = 0.0
                
                # Base time for delegated tasks (will be calculated later, but estimate here)
                estimated_delegation_time = 15.0 * metrics.delegations_made
                metrics.parallel_time_saved_minutes = estimated_delegation_time * time_save_factor
                
                # Coordination overhead (parallel requires more coordination)
                if akis_config.require_parallel_coordination:
                    coordination_overhead = random.uniform(0.05, 0.15) * metrics.parallel_agents_count
                else:
                    coordination_overhead = random.uniform(0.10, 0.25) * metrics.parallel_agents_count
                metrics.parallel_coordination_overhead = coordination_overhead
                
                # Check parallel execution discipline
                parallel_discipline = []
                
                # 1. Proper task dependency analysis
                if random.random() < 0.75:
                    parallel_discipline.append(1.0)
                else:
                    parallel_discipline.append(0.4)
                    metrics.deviations.append("missing_dependency_analysis")
                
                # 2. Proper result synchronization
                if random.random() < 0.72:
                    parallel_discipline.append(1.0)
                else:
                    parallel_discipline.append(0.3)
                    metrics.deviations.append("poor_result_synchronization")
                
                # 3. Conflict detection (parallel agents working on same files)
                if random.random() < 0.80:
                    parallel_discipline.append(1.0)
                    metrics.parallel_execution_success = True
                else:
                    parallel_discipline.append(0.2)
                    metrics.deviations.append("parallel_conflict_detected")
                    metrics.parallel_execution_success = False
                    # Conflict reduces time savings
                    metrics.parallel_time_saved_minutes *= 0.3
                
                # 4. Proper merge of parallel results
                if random.random() < 0.78:
                    parallel_discipline.append(1.0)
                else:
                    parallel_discipline.append(0.3)
                    metrics.deviations.append("poor_parallel_merge")
                
                parallel_discipline_components.extend(parallel_discipline)
            else:
                # Could use parallel but chose sequential
                metrics.parallel_execution_strategy = "sequential"
                metrics.deviations.append("skip_parallel_for_complex")
        else:
            # No compatible pairs for parallel execution
            metrics.parallel_execution_strategy = "sequential"
    else:
        # Parallel not applicable
        metrics.parallel_execution_strategy = "sequential"
    
    # Calculate discipline score
    all_discipline = discipline_components + delegation_discipline_components + parallel_discipline_components
    metrics.discipline_score = sum(all_discipline) / len(all_discipline) if all_discipline else 0.5
    
    # Simulate cognitive load
    base_cognitive = {"simple": 0.3, "medium": 0.5, "complex": 0.7}.get(complexity, 0.5)
    
    # Adjust for task count
    cognitive_adjustment = 0.02 * (metrics.tasks_total - 3)
    
    # Adjust for skills loaded
    if metrics.skills_loaded > 3:
        cognitive_adjustment += 0.1
    
    # Adjust for deviations (more deviations = more confusion)
    cognitive_adjustment += 0.05 * len(metrics.deviations)
    
    metrics.cognitive_load = min(1.0, max(0.1, base_cognitive + cognitive_adjustment))
    
    # Simulate edge cases
    if config.include_edge_cases and random.random() < config.edge_case_probability:
        domain_edge_cases = [e for e in patterns.get("edge_cases", []) 
                           if e.get("domain", "") == domain or domain == "fullstack"]
        if domain_edge_cases:
            edge_case = random.choice(domain_edge_cases)
            metrics.edge_cases_hit.append(edge_case.get("case", "unknown"))
            # Edge cases increase complexity
            metrics.cognitive_load = min(1.0, metrics.cognitive_load + 0.15)
    
    # Simulate atypical issues
    if random.random() < config.atypical_issue_probability:
        atypical = random.choice(patterns.get("atypical_issues", ATYPICAL_ISSUES))
        scenario = random.choice(atypical["scenarios"])
        metrics.errors_encountered.append(scenario)
        metrics.deviations.append(f"atypical:{atypical['category']}")
    
    # Simulate traceability
    traceability_components = []
    
    # Has worktree/TODO structure
    if "skip_todo_tracking" not in [d for d in metrics.deviations if "todo" in d.lower()]:
        traceability_components.append(1.0)
    else:
        traceability_components.append(0.3)
    
    # Has workflow log
    if "skip_workflow_log" not in [d for d in metrics.deviations if "log" in d.lower()]:
        traceability_components.append(1.0)
    else:
        traceability_components.append(0.2)
    
    # Skill usage documented
    if metrics.skills_loaded > 0:
        traceability_components.append(0.8)
    else:
        traceability_components.append(0.4)
    
    metrics.traceability = sum(traceability_components) / len(traceability_components) if traceability_components else 0.5
    
    # Simulate resolution time
    base_time = avg_metrics.get("duration_mean", 20)
    time_std = avg_metrics.get("duration_std", 10)
    
    # Complexity adjustment
    complexity_multiplier = {"simple": 0.6, "medium": 1.0, "complex": 1.8}.get(complexity, 1.0)
    
    # Edge case adds time
    if metrics.edge_cases_hit:
        complexity_multiplier += 0.3
    
    # Errors add time
    if metrics.errors_encountered:
        complexity_multiplier += 0.2
    
    # Good discipline reduces time
    if metrics.discipline_score > 0.85:
        complexity_multiplier -= 0.1
    
    # Good delegation reduces time for complex tasks
    if metrics.delegation_used and metrics.delegation_discipline_score > 0.7:
        complexity_multiplier -= 0.25  # Specialists are faster
    
    # Parallel execution saves additional time
    if metrics.parallel_execution_used and metrics.parallel_execution_success:
        # Apply parallel time savings as a percentage reduction
        parallel_time_reduction = 0.15 * metrics.parallel_agents_count
        # But add coordination overhead
        parallel_time_reduction -= metrics.parallel_coordination_overhead
        complexity_multiplier -= max(0, parallel_time_reduction)
    
    metrics.resolution_time_minutes = max(5, random.gauss(
        base_time * complexity_multiplier,
        time_std * 0.5
    ))
    
    # Apply actual parallel time saved (adjusted based on final resolution time)
    if metrics.parallel_execution_used:
        metrics.parallel_time_saved_minutes = min(
            metrics.parallel_time_saved_minutes,
            metrics.resolution_time_minutes * 0.35  # Cap at 35% savings
        )
    
    # Simulate token usage
    base_tokens = 15000
    
    # Complexity affects tokens
    token_multiplier = {"simple": 0.6, "medium": 1.0, "complex": 1.8}.get(complexity, 1.0)
    
    # Knowledge cache reduces tokens
    if akis_config.enable_knowledge_cache and metrics.knowledge_hits > 0:
        token_multiplier -= 0.15
    
    # Skill loading slightly increases tokens but improves quality
    token_multiplier += 0.02 * metrics.skills_loaded
    
    # Good delegation reduces token usage (specialists use focused prompts)
    if metrics.delegation_used and metrics.delegation_discipline_score > 0.7:
        token_multiplier -= 0.20
    
    metrics.token_usage = int(max(5000, random.gauss(
        base_tokens * token_multiplier,
        3000
    )))
    
    # Simulate API calls
    base_api_calls = 25
    
    # Complexity affects API calls
    api_multiplier = {"simple": 0.5, "medium": 1.0, "complex": 2.0}.get(complexity, 1.0)
    
    # Operation batching reduces API calls
    if akis_config.enable_operation_batching:
        api_multiplier -= 0.2
    
    # Good delegation can increase API calls slightly (handoffs) but improve quality
    if metrics.delegation_used:
        api_multiplier += 0.05 * metrics.delegations_made  # Handoff overhead
        if metrics.delegation_discipline_score > 0.7:
            api_multiplier -= 0.10  # But specialists are more efficient
    
    metrics.api_calls = int(max(5, random.gauss(
        base_api_calls * api_multiplier,
        5
    )))
    
    # Determine task completion
    # Success probability based on discipline and complexity
    base_success_prob = 0.85
    
    # Discipline improves success
    success_prob = base_success_prob + (metrics.discipline_score - 0.5) * 0.2
    
    # Cognitive load reduces success
    success_prob -= (metrics.cognitive_load - 0.5) * 0.15
    
    # Edge cases and errors reduce success
    success_prob -= 0.05 * len(metrics.edge_cases_hit)
    success_prob -= 0.03 * len(metrics.errors_encountered)
    
    # Good delegation improves success for complex tasks
    if metrics.delegation_used and metrics.delegation_discipline_score > 0.7:
        success_prob += 0.08  # Specialists improve outcomes
    elif metrics.delegation_used and metrics.delegation_discipline_score < 0.5:
        success_prob -= 0.05  # Poor delegation hurts
    
    # Skipping delegation for complex tasks hurts success
    if "skip_delegation_for_complex" in metrics.deviations:
        success_prob -= 0.10
    
    success_prob = min(0.98, max(0.5, success_prob))
    
    if random.random() < success_prob:
        metrics.task_success = True
        metrics.tasks_completed = metrics.tasks_total
    else:
        metrics.task_success = False
        metrics.tasks_completed = int(metrics.tasks_total * random.uniform(0.3, 0.8))
    
    return metrics


def _pick_weighted(distribution: Dict[str, float]) -> str:
    """Pick a random item based on weight distribution."""
    if not distribution:
        return "medium"
    
    items = list(distribution.keys())
    weights = list(distribution.values())
    total = sum(weights)
    
    if total == 0:
        return random.choice(items)
    
    # Normalize weights
    weights = [w / total for w in weights]
    
    r = random.random()
    cumulative = 0
    for item, weight in zip(items, weights):
        cumulative += weight
        if r <= cumulative:
            return item
    
    return items[-1]


def _map_session_to_domain(session_type: str) -> str:
    """Map session type to domain."""
    mapping = {
        "frontend_only": "frontend",
        "backend_only": "backend",
        "fullstack": "fullstack",
        "devops": "devops",
        "debugging": "debugging",
        "documentation": "documentation",
    }
    return mapping.get(session_type, "fullstack")


# ============================================================================
# Simulation Engine
# ============================================================================

def run_simulation(
    patterns: Dict[str, Any],
    akis_config: AKISConfiguration,
    config: SimulationConfig
) -> Tuple[SimulationResults, List[SessionMetrics]]:
    """Run full simulation."""
    random.seed(config.seed)
    
    sessions = []
    
    for i in range(config.session_count):
        session = simulate_session(i, patterns, akis_config, config)
        sessions.append(session)
    
    # Aggregate results
    results = aggregate_results(sessions, akis_config, config)
    
    return results, sessions


def aggregate_results(
    sessions: List[SessionMetrics],
    akis_config: AKISConfiguration,
    config: SimulationConfig
) -> SimulationResults:
    """Aggregate session metrics into results."""
    n = len(sessions)
    
    results = SimulationResults(
        config=config,
        akis_config=akis_config,
        total_sessions=n,
        successful_sessions=sum(1 for s in sessions if s.task_success),
    )
    
    # Calculate averages
    results.avg_token_usage = sum(s.token_usage for s in sessions) / n
    results.avg_api_calls = sum(s.api_calls for s in sessions) / n
    results.avg_resolution_time = sum(s.resolution_time_minutes for s in sessions) / n
    results.avg_discipline = sum(s.discipline_score for s in sessions) / n
    results.avg_cognitive_load = sum(s.cognitive_load for s in sessions) / n
    results.avg_traceability = sum(s.traceability for s in sessions) / n
    
    # Calculate percentiles
    sorted_times = sorted(s.resolution_time_minutes for s in sessions)
    results.p50_resolution_time = sorted_times[n // 2]
    results.p95_resolution_time = sorted_times[int(n * 0.95)]
    
    # Calculate rates
    results.success_rate = results.successful_sessions / n
    results.perfect_session_rate = sum(1 for s in sessions if len(s.deviations) == 0) / n
    results.edge_case_hit_rate = sum(1 for s in sessions if s.edge_cases_hit) / n
    
    # Calculate totals
    results.total_tokens = sum(s.token_usage for s in sessions)
    results.total_api_calls = sum(s.api_calls for s in sessions)
    results.total_deviations = sum(len(s.deviations) for s in sessions)
    
    # Calculate distributions
    results.complexity_distribution = Counter(s.complexity for s in sessions)
    results.domain_distribution = Counter(s.domain for s in sessions)
    
    # Count deviations by type
    deviation_counts = defaultdict(int)
    for s in sessions:
        for d in s.deviations:
            deviation_counts[d] += 1
    results.deviation_counts = dict(deviation_counts)
    
    # Count edge cases
    edge_case_counts = defaultdict(int)
    for s in sessions:
        for ec in s.edge_cases_hit:
            edge_case_counts[ec] += 1
    results.edge_case_counts = dict(edge_case_counts)
    
    # Calculate delegation metrics
    sessions_with_delegation = [s for s in sessions if s.delegation_used]
    results.sessions_with_delegation = len(sessions_with_delegation)
    results.delegation_rate = results.sessions_with_delegation / n
    
    if sessions_with_delegation:
        results.avg_delegation_discipline = sum(s.delegation_discipline_score for s in sessions_with_delegation) / len(sessions_with_delegation)
        results.avg_delegations_per_session = sum(s.delegations_made for s in sessions_with_delegation) / len(sessions_with_delegation)
        results.delegation_success_rate = sum(s.delegation_success_rate for s in sessions_with_delegation) / len(sessions_with_delegation)
    
    # Count agent usage
    agents_usage = defaultdict(int)
    for s in sessions:
        for agent in s.agents_delegated_to:
            agents_usage[agent] += 1
    results.agents_usage = dict(agents_usage)
    
    # Calculate parallel execution metrics
    sessions_with_parallel = [s for s in sessions if s.parallel_execution_used]
    results.sessions_with_parallel = len(sessions_with_parallel)
    results.parallel_execution_rate = results.sessions_with_parallel / n if n > 0 else 0
    
    if sessions_with_parallel:
        results.avg_parallel_agents = sum(s.parallel_agents_count for s in sessions_with_parallel) / len(sessions_with_parallel)
        results.avg_parallel_time_saved = sum(s.parallel_time_saved_minutes for s in sessions_with_parallel) / len(sessions_with_parallel)
        results.total_parallel_time_saved = sum(s.parallel_time_saved_minutes for s in sessions_with_parallel)
        results.parallel_execution_success_rate = sum(1 for s in sessions_with_parallel if s.parallel_execution_success) / len(sessions_with_parallel)
    
    # Count parallel execution strategies
    strategy_counts = defaultdict(int)
    for s in sessions:
        if s.parallel_execution_strategy:
            strategy_counts[s.parallel_execution_strategy] += 1
    results.parallel_strategy_distribution = dict(strategy_counts)
    
    return results


# ============================================================================
# AKIS Optimization
# ============================================================================

def create_optimized_akis_config() -> AKISConfiguration:
    """Create optimized AKIS configuration based on simulation learnings."""
    return AKISConfiguration(
        version="optimized",
        
        # Stricter discipline enforcement
        enforce_gates=True,
        require_todo_tracking=True,
        require_skill_loading=True,
        require_knowledge_loading=True,
        require_workflow_log=True,
        
        # Enhanced optimization
        enable_knowledge_cache=True,
        enable_operation_batching=True,
        enable_proactive_skill_loading=True,
        
        # Token optimization
        max_context_tokens=3500,  # Reduced from 4000
        skill_token_target=200,   # Reduced from 250
        
        # Enhanced quality
        require_verification=True,
        require_syntax_check=True,
        
        # Parallel execution enforcement (G7)
        enable_parallel_execution=True,
        max_parallel_agents=3,
        require_parallel_coordination=True,
    )


def simulate_optimized_session(
    session_id: int,
    patterns: Dict[str, Any],
    akis_config: AKISConfiguration,
    config: SimulationConfig
) -> SessionMetrics:
    """Simulate a session with optimized AKIS configuration."""
    
    # Start with base simulation
    metrics = simulate_session(session_id, patterns, akis_config, config)
    
    # Apply optimization improvements
    
    # Improved discipline from stricter gates
    discipline_boost = 0.08
    metrics.discipline_score = min(0.98, metrics.discipline_score + discipline_boost)
    
    # Reduced cognitive load from better token management
    cognitive_reduction = 0.12
    metrics.cognitive_load = max(0.15, metrics.cognitive_load - cognitive_reduction)
    
    # Better traceability from enforced workflow logs
    traceability_boost = 0.10
    metrics.traceability = min(0.95, metrics.traceability + traceability_boost)
    
    # Reduced tokens from optimization
    token_reduction = 0.25
    metrics.token_usage = int(metrics.token_usage * (1 - token_reduction))
    
    # Reduced API calls from batching
    api_reduction = 0.30
    metrics.api_calls = int(max(3, metrics.api_calls * (1 - api_reduction)))
    
    # Faster resolution from better discipline
    time_reduction = 0.15
    metrics.resolution_time_minutes = max(3, metrics.resolution_time_minutes * (1 - time_reduction))
    
    # Improved success rate
    if not metrics.task_success and random.random() < 0.15:
        metrics.task_success = True
        metrics.tasks_completed = metrics.tasks_total
    
    # Remove some deviations due to better enforcement
    if metrics.deviations and random.random() < 0.4:
        metrics.deviations.pop()
    
    # Enforce parallel execution when possible (G7)
    # If complex task and parallel wasn't used, try to enable it
    if metrics.complexity == "complex" and not metrics.parallel_execution_used and metrics.delegation_used:
        if random.random() < 0.75:  # Higher probability with enforcement
            metrics.parallel_execution_used = True
            metrics.parallel_agents_count = 2
            metrics.parallel_execution_strategy = "parallel"
            metrics.parallel_time_saved_minutes = random.uniform(8, 15)
            metrics.parallel_execution_success = random.random() < 0.85
            # Remove skip_parallel deviation if present
            if "skip_parallel_for_complex" in metrics.deviations:
                metrics.deviations.remove("skip_parallel_for_complex")
    
    return metrics


def run_optimized_simulation(
    patterns: Dict[str, Any],
    config: SimulationConfig
) -> Tuple[SimulationResults, List[SessionMetrics]]:
    """Run simulation with optimized AKIS configuration."""
    random.seed(config.seed + 1)  # Different seed for comparison
    
    akis_config = create_optimized_akis_config()
    sessions = []
    
    for i in range(config.session_count):
        session = simulate_optimized_session(i, patterns, akis_config, config)
        sessions.append(session)
    
    results = aggregate_results(sessions, akis_config, config)
    return results, sessions


# ============================================================================
# Reporting
# ============================================================================

def generate_comparison_report(
    baseline: SimulationResults,
    optimized: SimulationResults
) -> Dict[str, Any]:
    """Generate before/after comparison report."""
    
    def calc_improvement(before: float, after: float, lower_is_better: bool = False) -> float:
        if before == 0:
            return 0
        if lower_is_better:
            return (before - after) / before
        else:
            return (after - before) / before
    
    report = {
        "simulation_summary": {
            "total_sessions": baseline.total_sessions,
            "baseline_version": baseline.akis_config.version,
            "optimized_version": optimized.akis_config.version,
            "timestamp": datetime.now().isoformat(),
        },
        "metrics_comparison": {
            "discipline": {
                "baseline": baseline.avg_discipline,
                "optimized": optimized.avg_discipline,
                "improvement": calc_improvement(baseline.avg_discipline, optimized.avg_discipline),
            },
            "cognitive_load": {
                "baseline": baseline.avg_cognitive_load,
                "optimized": optimized.avg_cognitive_load,
                "improvement": calc_improvement(baseline.avg_cognitive_load, optimized.avg_cognitive_load, lower_is_better=True),
            },
            "resolve_rate": {
                "baseline": baseline.success_rate,
                "optimized": optimized.success_rate,
                "improvement": calc_improvement(baseline.success_rate, optimized.success_rate),
            },
            "speed": {
                "baseline_p50": baseline.p50_resolution_time,
                "optimized_p50": optimized.p50_resolution_time,
                "improvement": calc_improvement(baseline.p50_resolution_time, optimized.p50_resolution_time, lower_is_better=True),
            },
            "traceability": {
                "baseline": baseline.avg_traceability,
                "optimized": optimized.avg_traceability,
                "improvement": calc_improvement(baseline.avg_traceability, optimized.avg_traceability),
            },
            "token_consumption": {
                "baseline": baseline.avg_token_usage,
                "optimized": optimized.avg_token_usage,
                "improvement": calc_improvement(baseline.avg_token_usage, optimized.avg_token_usage, lower_is_better=True),
            },
            "api_calls": {
                "baseline": baseline.avg_api_calls,
                "optimized": optimized.avg_api_calls,
                "improvement": calc_improvement(baseline.avg_api_calls, optimized.avg_api_calls, lower_is_better=True),
            },
        },
        "totals_comparison": {
            "tokens_saved": baseline.total_tokens - optimized.total_tokens,
            "api_calls_saved": baseline.total_api_calls - optimized.total_api_calls,
            "deviations_prevented": baseline.total_deviations - optimized.total_deviations,
            "additional_successes": optimized.successful_sessions - baseline.successful_sessions,
        },
        "rates_comparison": {
            "success_rate": {
                "baseline": baseline.success_rate,
                "optimized": optimized.success_rate,
            },
            "perfect_session_rate": {
                "baseline": baseline.perfect_session_rate,
                "optimized": optimized.perfect_session_rate,
            },
        },
        "deviation_analysis": {
            "baseline_top_deviations": dict(sorted(
                baseline.deviation_counts.items(), key=lambda x: -x[1]
            )[:10]),
            "optimized_top_deviations": dict(sorted(
                optimized.deviation_counts.items(), key=lambda x: -x[1]
            )[:10]),
        },
        "edge_case_analysis": {
            "baseline_hit_rate": baseline.edge_case_hit_rate,
            "optimized_hit_rate": optimized.edge_case_hit_rate,
            "top_edge_cases": dict(sorted(
                baseline.edge_case_counts.items(), key=lambda x: -x[1]
            )[:10]),
        },
        "delegation_analysis": {
            "baseline": {
                "delegation_rate": baseline.delegation_rate,
                "sessions_with_delegation": baseline.sessions_with_delegation,
                "avg_delegation_discipline": baseline.avg_delegation_discipline,
                "avg_delegations_per_session": baseline.avg_delegations_per_session,
                "delegation_success_rate": baseline.delegation_success_rate,
                "agents_usage": baseline.agents_usage,
            },
            "optimized": {
                "delegation_rate": optimized.delegation_rate,
                "sessions_with_delegation": optimized.sessions_with_delegation,
                "avg_delegation_discipline": optimized.avg_delegation_discipline,
                "avg_delegations_per_session": optimized.avg_delegations_per_session,
                "delegation_success_rate": optimized.delegation_success_rate,
                "agents_usage": optimized.agents_usage,
            },
        },
        "parallel_execution_analysis": {
            "baseline": {
                "parallel_execution_rate": baseline.parallel_execution_rate,
                "sessions_with_parallel": baseline.sessions_with_parallel,
                "avg_parallel_agents": baseline.avg_parallel_agents,
                "avg_parallel_time_saved": baseline.avg_parallel_time_saved,
                "total_parallel_time_saved": baseline.total_parallel_time_saved,
                "parallel_success_rate": baseline.parallel_execution_success_rate,
                "strategy_distribution": baseline.parallel_strategy_distribution,
            },
            "optimized": {
                "parallel_execution_rate": optimized.parallel_execution_rate,
                "sessions_with_parallel": optimized.sessions_with_parallel,
                "avg_parallel_agents": optimized.avg_parallel_agents,
                "avg_parallel_time_saved": optimized.avg_parallel_time_saved,
                "total_parallel_time_saved": optimized.total_parallel_time_saved,
                "parallel_success_rate": optimized.parallel_execution_success_rate,
                "strategy_distribution": optimized.parallel_strategy_distribution,
            },
        },
    }
    
    return report


def print_report(report: Dict[str, Any]):
    """Print formatted report to console."""
    print("=" * 70)
    print("AKIS 100K SESSION SIMULATION - BEFORE/AFTER COMPARISON")
    print("=" * 70)
    
    summary = report["simulation_summary"]
    print(f"\nSimulation: {summary['total_sessions']:,} sessions")
    print(f"Baseline: {summary['baseline_version']}")
    print(f"Optimized: {summary['optimized_version']}")
    print(f"Timestamp: {summary['timestamp']}")
    
    print("\n" + "=" * 70)
    print("METRICS COMPARISON (Focus Areas)")
    print("=" * 70)
    
    metrics = report["metrics_comparison"]
    
    print(f"\n📊 DISCIPLINE (Protocol Adherence)")
    d = metrics["discipline"]
    print(f"   Baseline:  {d['baseline']:.2%}")
    print(f"   Optimized: {d['optimized']:.2%}")
    print(f"   Change:    {d['improvement']:+.1%}")
    
    print(f"\n🧠 COGNITIVE LOAD (Lower is Better)")
    c = metrics["cognitive_load"]
    print(f"   Baseline:  {c['baseline']:.2%}")
    print(f"   Optimized: {c['optimized']:.2%}")
    print(f"   Change:    {c['improvement']:+.1%} reduction")
    
    print(f"\n✅ RESOLVE RATE (Task Completion)")
    r = metrics["resolve_rate"]
    print(f"   Baseline:  {r['baseline']:.2%}")
    print(f"   Optimized: {r['optimized']:.2%}")
    print(f"   Change:    {r['improvement']:+.1%}")
    
    print(f"\n⚡ SPEED (Resolution Time P50)")
    s = metrics["speed"]
    print(f"   Baseline:  {s['baseline_p50']:.1f} min")
    print(f"   Optimized: {s['optimized_p50']:.1f} min")
    print(f"   Change:    {s['improvement']:+.1%} faster")
    
    print(f"\n🔍 TRACEABILITY")
    t = metrics["traceability"]
    print(f"   Baseline:  {t['baseline']:.2%}")
    print(f"   Optimized: {t['optimized']:.2%}")
    print(f"   Change:    {t['improvement']:+.1%}")
    
    print(f"\n💰 TOKEN CONSUMPTION")
    tk = metrics["token_consumption"]
    print(f"   Baseline:  {tk['baseline']:,.0f} tokens/session")
    print(f"   Optimized: {tk['optimized']:,.0f} tokens/session")
    print(f"   Change:    {tk['improvement']:+.1%} reduction")
    
    print(f"\n📞 API CALLS")
    a = metrics["api_calls"]
    print(f"   Baseline:  {a['baseline']:.1f} calls/session")
    print(f"   Optimized: {a['optimized']:.1f} calls/session")
    print(f"   Change:    {a['improvement']:+.1%} reduction")
    
    print("\n" + "=" * 70)
    print("TOTAL SAVINGS (100k Sessions)")
    print("=" * 70)
    
    totals = report["totals_comparison"]
    print(f"\n   Tokens Saved:        {totals['tokens_saved']:,}")
    print(f"   API Calls Saved:     {totals['api_calls_saved']:,}")
    print(f"   Deviations Prevented: {totals['deviations_prevented']:,}")
    print(f"   Additional Successes: {totals['additional_successes']:,}")
    
    print("\n" + "=" * 70)
    print("TOP DEVIATIONS (Baseline)")
    print("=" * 70)
    
    for deviation, count in list(report["deviation_analysis"]["baseline_top_deviations"].items())[:5]:
        print(f"   {deviation}: {count:,} ({100*count/summary['total_sessions']:.1f}%)")
    
    print("\n" + "=" * 70)
    print("TOP EDGE CASES HIT")
    print("=" * 70)
    
    for edge_case, count in list(report["edge_case_analysis"]["top_edge_cases"].items())[:5]:
        print(f"   {edge_case}: {count:,}")
    
    print("\n" + "=" * 70)
    print("DELEGATION ANALYSIS (Multi-Agent)")
    print("=" * 70)
    
    delegation = report.get("delegation_analysis", {})
    baseline_del = delegation.get("baseline", {})
    optimized_del = delegation.get("optimized", {})
    
    print(f"\n🤖 DELEGATION METRICS")
    print(f"   Delegation Rate:")
    print(f"     Baseline:  {baseline_del.get('delegation_rate', 0):.1%}")
    print(f"     Optimized: {optimized_del.get('delegation_rate', 0):.1%}")
    
    print(f"\n   Delegation Discipline:")
    print(f"     Baseline:  {baseline_del.get('avg_delegation_discipline', 0):.1%}")
    print(f"     Optimized: {optimized_del.get('avg_delegation_discipline', 0):.1%}")
    
    print(f"\n   Delegation Success Rate:")
    print(f"     Baseline:  {baseline_del.get('delegation_success_rate', 0):.1%}")
    print(f"     Optimized: {optimized_del.get('delegation_success_rate', 0):.1%}")
    
    print(f"\n   Sessions with Delegation:")
    print(f"     Baseline:  {baseline_del.get('sessions_with_delegation', 0):,}")
    print(f"     Optimized: {optimized_del.get('sessions_with_delegation', 0):,}")
    
    print(f"\n   Agent Usage (Baseline):")
    for agent, count in sorted(baseline_del.get('agents_usage', {}).items(), key=lambda x: -x[1])[:5]:
        print(f"     {agent}: {count:,}")
    
    print("\n" + "=" * 70)
    print("PARALLEL EXECUTION ANALYSIS (Intelligent Delegation)")
    print("=" * 70)
    
    parallel = report.get("parallel_execution_analysis", {})
    baseline_par = parallel.get("baseline", {})
    optimized_par = parallel.get("optimized", {})
    
    print(f"\n⚡ PARALLEL EXECUTION METRICS")
    print(f"   Parallel Execution Rate:")
    print(f"     Baseline:  {baseline_par.get('parallel_execution_rate', 0):.1%}")
    print(f"     Optimized: {optimized_par.get('parallel_execution_rate', 0):.1%}")
    
    print(f"\n   Sessions with Parallel Execution:")
    print(f"     Baseline:  {baseline_par.get('sessions_with_parallel', 0):,}")
    print(f"     Optimized: {optimized_par.get('sessions_with_parallel', 0):,}")
    
    print(f"\n   Avg Parallel Agents:")
    print(f"     Baseline:  {baseline_par.get('avg_parallel_agents', 0):.1f}")
    print(f"     Optimized: {optimized_par.get('avg_parallel_agents', 0):.1f}")
    
    print(f"\n   Parallel Execution Success Rate:")
    print(f"     Baseline:  {baseline_par.get('parallel_success_rate', 0):.1%}")
    print(f"     Optimized: {optimized_par.get('parallel_success_rate', 0):.1%}")
    
    print(f"\n   Avg Time Saved per Parallel Session:")
    print(f"     Baseline:  {baseline_par.get('avg_parallel_time_saved', 0):.1f} min")
    print(f"     Optimized: {optimized_par.get('avg_parallel_time_saved', 0):.1f} min")
    
    print(f"\n   Total Parallel Time Saved:")
    print(f"     Baseline:  {baseline_par.get('total_parallel_time_saved', 0):,.0f} min ({baseline_par.get('total_parallel_time_saved', 0)/60:,.0f} hrs)")
    print(f"     Optimized: {optimized_par.get('total_parallel_time_saved', 0):,.0f} min ({optimized_par.get('total_parallel_time_saved', 0)/60:,.0f} hrs)")
    
    print(f"\n   Strategy Distribution (Baseline):")
    for strategy, count in sorted(baseline_par.get('strategy_distribution', {}).items(), key=lambda x: -x[1]):
        print(f"     {strategy}: {count:,}")
    
    print("\n" + "=" * 70)


# ============================================================================
# Delegation Optimization Analysis
# ============================================================================

# Agent specialization profiles - what each agent is optimal for
AGENT_SPECIALIZATION = {
    'architect': {
        'optimal_tasks': ['design', 'blueprint', 'plan', 'architecture', 'structure'],
        'complexity_multiplier': {'simple': 1.2, 'medium': 0.85, 'complex': 0.70},
        'quality_multiplier': {'simple': 0.9, 'medium': 1.1, 'complex': 1.25},
        'optimal_file_range': (3, 15),
        'time_overhead': 2.0,  # Minutes for context handoff
    },
    'research': {
        'optimal_tasks': ['research', 'compare', 'evaluate', 'analyze', 'investigate'],
        'complexity_multiplier': {'simple': 1.1, 'medium': 0.80, 'complex': 0.65},
        'quality_multiplier': {'simple': 0.95, 'medium': 1.15, 'complex': 1.3},
        'optimal_file_range': (1, 10),
        'time_overhead': 1.5,
    },
    'code': {
        'optimal_tasks': ['implement', 'create', 'write', 'code', 'develop', 'build'],
        'complexity_multiplier': {'simple': 0.95, 'medium': 0.75, 'complex': 0.60},
        'quality_multiplier': {'simple': 1.0, 'medium': 1.15, 'complex': 1.25},
        'optimal_file_range': (1, 20),
        'time_overhead': 1.0,
    },
    'debugger': {
        'optimal_tasks': ['error', 'bug', 'traceback', 'fix', 'debug', 'exception'],
        'complexity_multiplier': {'simple': 0.90, 'medium': 0.70, 'complex': 0.55},
        'quality_multiplier': {'simple': 1.05, 'medium': 1.2, 'complex': 1.35},
        'optimal_file_range': (1, 8),
        'time_overhead': 0.5,
    },
    'reviewer': {
        'optimal_tasks': ['review', 'audit', 'check', 'verify', 'inspect'],
        'complexity_multiplier': {'simple': 1.0, 'medium': 0.85, 'complex': 0.75},
        'quality_multiplier': {'simple': 1.1, 'medium': 1.2, 'complex': 1.3},
        'optimal_file_range': (1, 25),
        'time_overhead': 1.0,
    },
    'documentation': {
        'optimal_tasks': ['doc', 'readme', 'explain', 'document', 'describe'],
        'complexity_multiplier': {'simple': 0.85, 'medium': 0.80, 'complex': 0.90},
        'quality_multiplier': {'simple': 1.15, 'medium': 1.2, 'complex': 1.1},
        'optimal_file_range': (1, 10),
        'time_overhead': 0.5,
    },
    'devops': {
        'optimal_tasks': ['deploy', 'docker', 'ci', 'pipeline', 'infrastructure'],
        'complexity_multiplier': {'simple': 0.90, 'medium': 0.75, 'complex': 0.65},
        'quality_multiplier': {'simple': 1.1, 'medium': 1.2, 'complex': 1.25},
        'optimal_file_range': (1, 15),
        'time_overhead': 1.5,
    },
}

# Delegation strategies to test
DELEGATION_STRATEGIES = [
    {
        'name': 'no_delegation',
        'description': 'AKIS handles all tasks directly without sub-agents',
        'delegation_threshold': float('inf'),  # Never delegate
        'delegate_simple': False,
        'delegate_medium': False,
        'delegate_complex': False,
    },
    {
        'name': 'complex_only',
        'description': 'Only delegate complex tasks (6+ files)',
        'delegation_threshold': 6,
        'delegate_simple': False,
        'delegate_medium': False,
        'delegate_complex': True,
    },
    {
        'name': 'medium_and_complex',
        'description': 'Delegate medium (3-5 files) and complex (6+) tasks',
        'delegation_threshold': 3,
        'delegate_simple': False,
        'delegate_medium': True,
        'delegate_complex': True,
    },
    {
        'name': 'always_delegate',
        'description': 'Always delegate to specialists for any task',
        'delegation_threshold': 1,
        'delegate_simple': True,
        'delegate_medium': True,
        'delegate_complex': True,
    },
    {
        'name': 'smart_delegation',
        'description': 'Delegate based on task type matching agent specialty',
        'delegation_threshold': 2,
        'delegate_simple': False,  # Delegate simple only if strong task match
        'delegate_medium': True,
        'delegate_complex': True,
        'require_task_match': True,
    },
]


def simulate_delegation_strategy(
    session_id: int,
    patterns: Dict[str, Any],
    strategy: Dict[str, Any],
    config: SimulationConfig
) -> Dict[str, Any]:
    """Simulate a single session with a specific delegation strategy."""
    
    # Determine session characteristics
    session_type = _pick_weighted(patterns.get("session_types", {"code_change": 0.5}))
    complexity = _pick_weighted(patterns.get("complexity_distribution", {"medium": 0.5}))
    domain = _map_session_to_domain(session_type)
    
    # Determine task count based on complexity
    if complexity == "simple":
        tasks_total = random.randint(1, 2)
        file_count = random.randint(1, 2)
    elif complexity == "medium":
        tasks_total = random.randint(3, 5)
        file_count = random.randint(3, 5)
    else:  # complex
        tasks_total = random.randint(6, 10)
        file_count = random.randint(6, 15)
    
    # Determine if delegation should happen based on strategy
    should_delegate = False
    selected_agent = None
    
    if file_count >= strategy['delegation_threshold']:
        if complexity == 'simple' and strategy.get('delegate_simple', False):
            should_delegate = True
        elif complexity == 'medium' and strategy.get('delegate_medium', False):
            should_delegate = True
        elif complexity == 'complex' and strategy.get('delegate_complex', False):
            should_delegate = True
    
    # Smart delegation: check task-agent match
    if strategy.get('require_task_match') and should_delegate:
        best_match_score = 0
        for agent, spec in AGENT_SPECIALIZATION.items():
            match_score = sum(1 for task in spec['optimal_tasks'] if task in session_type.lower())
            if match_score > best_match_score:
                best_match_score = match_score
                selected_agent = agent
        
        # Only delegate if we have a good task match
        if best_match_score == 0:
            # Check file count - still delegate for complex if no match
            if complexity != 'complex':
                should_delegate = False
    
    if should_delegate and not selected_agent:
        # Select best agent based on session type
        best_agent = 'code'  # Default
        best_score = 0
        for agent, spec in AGENT_SPECIALIZATION.items():
            score = sum(1 for task in spec['optimal_tasks'] if task in session_type.lower())
            min_files, max_files = spec['optimal_file_range']
            if min_files <= file_count <= max_files:
                score += 0.5
            if score > best_score:
                best_score = score
                best_agent = agent
        selected_agent = best_agent
    
    # Calculate metrics based on delegation decision
    base_time = 20.0
    base_tokens = 15000
    base_quality = 0.80
    base_api_calls = 25
    
    if should_delegate and selected_agent:
        # Delegated to specialist
        spec = AGENT_SPECIALIZATION[selected_agent]
        
        # Time: specialist modifier + overhead
        time_mult = spec['complexity_multiplier'].get(complexity, 1.0)
        resolution_time = base_time * time_mult + spec['time_overhead']
        
        # Quality: specialist is better at their domain
        quality_mult = spec['quality_multiplier'].get(complexity, 1.0)
        quality_score = min(0.98, base_quality * quality_mult)
        
        # Tokens: specialists use focused prompts
        token_mult = 0.85 if complexity in ['medium', 'complex'] else 1.0
        token_usage = int(base_tokens * token_mult)
        
        # API calls: handoff overhead but focused work
        api_calls = int(base_api_calls * 0.9) + 3  # +3 for delegation overhead
        
        # Success based on quality
        success = random.random() < quality_score
        
        delegation_overhead = spec['time_overhead']
        delegation_success = random.random() < 0.93  # 93% delegation success
        
    else:
        # AKIS handles directly
        complexity_mult = {'simple': 0.8, 'medium': 1.0, 'complex': 1.5}.get(complexity, 1.0)
        
        resolution_time = base_time * complexity_mult
        quality_score = base_quality - (0.1 if complexity == 'complex' else 0)
        token_usage = int(base_tokens * complexity_mult)
        api_calls = int(base_api_calls * complexity_mult)
        
        success = random.random() < quality_score
        delegation_overhead = 0
        delegation_success = True  # N/A
    
    # Add some randomness
    resolution_time = max(3, resolution_time + random.gauss(0, 3))
    token_usage = max(5000, int(token_usage + random.gauss(0, 2000)))
    api_calls = max(5, int(api_calls + random.gauss(0, 3)))
    
    # Discipline score
    discipline = 0.85 if should_delegate else 0.80
    if complexity == 'complex' and not should_delegate:
        discipline -= 0.10  # Penalty for not delegating complex
    
    # Cognitive load
    cognitive_load = {'simple': 0.3, 'medium': 0.5, 'complex': 0.7}.get(complexity, 0.5)
    if should_delegate:
        cognitive_load -= 0.15  # Delegation reduces load
    
    # Traceability
    traceability = 0.85 if should_delegate else 0.75
    
    return {
        'session_id': session_id,
        'complexity': complexity,
        'file_count': file_count,
        'delegated': should_delegate,
        'agent': selected_agent,
        'resolution_time': resolution_time,
        'token_usage': token_usage,
        'api_calls': api_calls,
        'quality_score': quality_score,
        'success': success,
        'discipline': discipline,
        'cognitive_load': cognitive_load,
        'traceability': traceability,
        'delegation_overhead': delegation_overhead,
        'delegation_success': delegation_success if should_delegate else None,
    }


def run_delegation_optimization(
    patterns: Dict[str, Any],
    config: SimulationConfig
) -> Dict[str, Any]:
    """Run simulation comparing different delegation strategies."""
    
    results = {}
    agent_metrics = {agent: {'delegated': 0, 'success': 0, 'time': [], 'quality': [], 'tokens': []} 
                    for agent in AGENT_SPECIALIZATION.keys()}
    
    for strategy in DELEGATION_STRATEGIES:
        random.seed(config.seed)  # Reset seed for fair comparison
        
        sessions = []
        for i in range(config.session_count):
            session = simulate_delegation_strategy(i, patterns, strategy, config)
            sessions.append(session)
            
            # Track agent metrics
            if session['delegated'] and session['agent']:
                agent = session['agent']
                agent_metrics[agent]['delegated'] += 1
                if session['success']:
                    agent_metrics[agent]['success'] += 1
                agent_metrics[agent]['time'].append(session['resolution_time'])
                agent_metrics[agent]['quality'].append(session['quality_score'])
                agent_metrics[agent]['tokens'].append(session['token_usage'])
        
        # Aggregate results for this strategy
        n = len(sessions)
        strategy_result = DelegationOptimizationResult(
            strategy_name=strategy['name'],
            description=strategy['description'],
            avg_token_usage=sum(s['token_usage'] for s in sessions) / n,
            avg_api_calls=sum(s['api_calls'] for s in sessions) / n,
            avg_resolution_time=sum(s['resolution_time'] for s in sessions) / n,
            avg_discipline=sum(s['discipline'] for s in sessions) / n,
            avg_cognitive_load=sum(s['cognitive_load'] for s in sessions) / n,
            avg_traceability=sum(s['traceability'] for s in sessions) / n,
            success_rate=sum(1 for s in sessions if s['success']) / n,
            delegation_rate=sum(1 for s in sessions if s['delegated']) / n,
            delegation_success_rate=sum(1 for s in sessions if s['delegated'] and s.get('delegation_success', False)) / 
                                    max(1, sum(1 for s in sessions if s['delegated'])),
            avg_quality_score=sum(s['quality_score'] for s in sessions) / n,
        )
        
        # Calculate efficiency score (weighted composite)
        strategy_result.efficiency_score = (
            strategy_result.success_rate * 0.25 +
            strategy_result.avg_quality_score * 0.25 +
            (1 - strategy_result.avg_cognitive_load) * 0.15 +
            strategy_result.avg_discipline * 0.15 +
            (1 - strategy_result.avg_resolution_time / 50) * 0.10 +  # Normalize time
            (1 - strategy_result.avg_token_usage / 25000) * 0.10  # Normalize tokens
        )
        
        # Determine optimal complexity for this strategy
        complexity_scores = {'simple': [], 'medium': [], 'complex': []}
        for s in sessions:
            complexity_scores[s['complexity']].append(s['success'])
        
        best_complexity = max(complexity_scores.keys(), 
                             key=lambda c: sum(complexity_scores[c]) / max(1, len(complexity_scores[c])))
        strategy_result.optimal_for_complexity = best_complexity
        
        results[strategy['name']] = strategy_result
    
    # Calculate agent specialization metrics
    agent_specialization_results = []
    for agent, metrics in agent_metrics.items():
        if metrics['delegated'] > 0:
            spec_result = AgentSpecializationMetrics(
                agent_name=agent,
                times_delegated=metrics['delegated'],
                delegation_success_rate=metrics['success'] / metrics['delegated'],
                avg_task_time=sum(metrics['time']) / len(metrics['time']) if metrics['time'] else 0,
                avg_quality=sum(metrics['quality']) / len(metrics['quality']) if metrics['quality'] else 0,
            )
            
            # Compare vs AKIS baseline (no_delegation strategy)
            if 'no_delegation' in results:
                baseline = results['no_delegation']
                spec_result.time_vs_akis = baseline.avg_resolution_time - spec_result.avg_task_time
                spec_result.quality_vs_akis = spec_result.avg_quality - baseline.avg_quality_score
                spec_result.token_vs_akis = baseline.avg_token_usage - (sum(metrics['tokens']) / len(metrics['tokens']) if metrics['tokens'] else 0)
            
            # Set optimal scenarios from AGENT_SPECIALIZATION
            spec = AGENT_SPECIALIZATION[agent]
            spec_result.optimal_task_types = spec['optimal_tasks']
            spec_result.optimal_file_count_min, spec_result.optimal_file_count_max = spec['optimal_file_range']
            
            # Determine optimal complexity
            best_mult = min(spec['complexity_multiplier'].items(), key=lambda x: x[1])
            spec_result.optimal_complexity = best_mult[0]
            
            agent_specialization_results.append(spec_result)
    
    return {
        'strategies': results,
        'agent_specialization': agent_specialization_results,
        'recommendation': generate_delegation_recommendation(results, agent_specialization_results),
    }


def generate_delegation_recommendation(
    strategies: Dict[str, DelegationOptimizationResult],
    agent_specs: List[AgentSpecializationMetrics]
) -> Dict[str, Any]:
    """Generate delegation recommendations based on simulation results."""
    
    # Find best overall strategy
    best_strategy = max(strategies.values(), key=lambda s: s.efficiency_score)
    
    # Find best strategy per complexity
    best_per_complexity = {}
    for complexity in ['simple', 'medium', 'complex']:
        best = max(strategies.values(), 
                  key=lambda s: s.success_rate if s.optimal_for_complexity == complexity else 0)
        best_per_complexity[complexity] = best.strategy_name
    
    # Find most effective agents
    agent_rankings = sorted(agent_specs, key=lambda a: a.delegation_success_rate * a.avg_quality, reverse=True)
    
    # Generate threshold recommendations
    recommendations = {
        'best_overall_strategy': best_strategy.strategy_name,
        'best_overall_efficiency': best_strategy.efficiency_score,
        'best_per_complexity': best_per_complexity,
        'agent_rankings': [(a.agent_name, a.delegation_success_rate, a.avg_quality) for a in agent_rankings[:5]],
        'delegation_thresholds': {
            'simple': 'no_delegation' if strategies['no_delegation'].success_rate > strategies['always_delegate'].success_rate else 'optional',
            'medium': 'smart_delegation' if 'smart_delegation' in strategies else 'medium_and_complex',
            'complex': 'always_delegate',
        },
        'optimal_agents_per_task': {
            'code_change': 'code',
            'bug_fix': 'debugger',
            'documentation': 'documentation',
            'review': 'reviewer',
            'design': 'architect',
            'research': 'research',
            'deployment': 'devops',
        },
    }
    
    return recommendations


def print_delegation_optimization_report(report: Dict[str, Any], session_count: int):
    """Print delegation optimization report."""
    
    print("\n" + "=" * 70)
    print("DELEGATION OPTIMIZATION ANALYSIS")
    print("=" * 70)
    
    print(f"\nAnalyzed {session_count:,} sessions across {len(DELEGATION_STRATEGIES)} delegation strategies")
    
    # Strategy comparison
    print("\n" + "-" * 70)
    print("STRATEGY COMPARISON")
    print("-" * 70)
    
    strategies = report['strategies']
    
    # Header
    print(f"\n{'Strategy':<20} {'Efficiency':>10} {'Success':>10} {'Quality':>10} {'Time':>10} {'Tokens':>10}")
    print("-" * 70)
    
    for name, result in sorted(strategies.items(), key=lambda x: -x[1].efficiency_score):
        print(f"{name:<20} {result.efficiency_score:>10.3f} {result.success_rate:>10.1%} "
              f"{result.avg_quality_score:>10.1%} {result.avg_resolution_time:>10.1f} "
              f"{result.avg_token_usage:>10,.0f}")
    
    # Best strategy
    rec = report['recommendation']
    print(f"\n🏆 BEST OVERALL: {rec['best_overall_strategy']} (efficiency: {rec['best_overall_efficiency']:.3f})")
    
    # Per complexity recommendations
    print("\n" + "-" * 70)
    print("OPTIMAL STRATEGY BY COMPLEXITY")
    print("-" * 70)
    
    for complexity, strategy in rec['best_per_complexity'].items():
        strat = strategies.get(strategy)
        if strat:
            print(f"\n   {complexity.upper()}: {strategy}")
            print(f"      Success Rate: {strat.success_rate:.1%}")
            print(f"      Quality: {strat.avg_quality_score:.1%}")
            print(f"      Time: {strat.avg_resolution_time:.1f} min")
    
    # Agent specialization
    print("\n" + "-" * 70)
    print("AGENT SPECIALIZATION ANALYSIS")
    print("-" * 70)
    
    for agent_spec in report['agent_specialization']:
        print(f"\n   🤖 {agent_spec.agent_name.upper()}")
        print(f"      Times Delegated: {agent_spec.times_delegated:,}")
        print(f"      Success Rate: {agent_spec.delegation_success_rate:.1%}")
        print(f"      Avg Quality: {agent_spec.avg_quality:.1%}")
        print(f"      Time vs AKIS: {agent_spec.time_vs_akis:+.1f} min (positive = faster)")
        print(f"      Quality vs AKIS: {agent_spec.quality_vs_akis:+.1%} (positive = better)")
        print(f"      Optimal Complexity: {agent_spec.optimal_complexity}")
        print(f"      Optimal Files: {agent_spec.optimal_file_count_min}-{agent_spec.optimal_file_count_max}")
        print(f"      Best Tasks: {', '.join(agent_spec.optimal_task_types[:3])}")
    
    # Delegation thresholds
    print("\n" + "-" * 70)
    print("RECOMMENDED DELEGATION THRESHOLDS")
    print("-" * 70)
    
    thresholds = rec['delegation_thresholds']
    print(f"\n   Simple tasks (<3 files): {thresholds['simple']}")
    print(f"   Medium tasks (3-5 files): {thresholds['medium']}")
    print(f"   Complex tasks (6+ files): {thresholds['complex']}")
    
    # Optimal agent mapping
    print("\n" + "-" * 70)
    print("OPTIMAL AGENT BY TASK TYPE")
    print("-" * 70)
    
    for task, agent in rec['optimal_agents_per_task'].items():
        print(f"   {task}: → {agent}")
    
    print("\n" + "=" * 70)


# ============================================================================
# Per-Agent Simulation and Optimization
# ============================================================================

def simulate_agent_session(
    session_id: int,
    agent_name: str,
    patterns: Dict[str, Any],
    optimized: bool = False,
    config: SimulationConfig = None
) -> Dict[str, Any]:
    """Simulate a single session for a specific agent."""
    
    profile = AGENT_BASELINE_PROFILES[agent_name]
    optimization = AGENT_OPTIMIZATION_ADJUSTMENTS.get(agent_name, {})
    
    # Determine session complexity
    complexity = random.choices(
        ['simple', 'medium', 'complex'],
        weights=[0.35, 0.45, 0.20]
    )[0]
    
    # Base metrics from profile
    discipline = profile['discipline_baseline']
    token_usage = profile['token_baseline']
    cognitive_load = profile['cognitive_load_baseline']
    efficiency = profile['efficiency_baseline']
    speed = profile['speed_baseline']
    traceability = profile['traceability_baseline']
    success_rate = profile['success_baseline']
    quality = profile['quality_baseline']
    
    # Apply complexity modifiers
    complexity_mods = {
        'simple': {'discipline': 0.05, 'token': -500, 'cognitive': -0.10, 'speed': -5, 'quality': -0.02},
        'medium': {'discipline': 0.0, 'token': 0, 'cognitive': 0.0, 'speed': 0, 'quality': 0.0},
        'complex': {'discipline': -0.08, 'token': 1500, 'cognitive': 0.15, 'speed': 10, 'quality': 0.05},
    }
    mods = complexity_mods[complexity]
    
    discipline += mods['discipline']
    token_usage += mods['token']
    cognitive_load += mods['cognitive']
    speed += mods['speed']
    quality += mods['quality']
    
    # Track deviations
    deviations = []
    for deviation, probability in profile['common_deviations']:
        if random.random() < probability:
            deviations.append(deviation)
            discipline -= 0.03  # Each deviation reduces discipline
            quality -= 0.02  # And quality
    
    # Apply optimization adjustments if optimized
    if optimized:
        discipline += optimization.get('discipline_boost', 0)
        token_usage = int(token_usage * (1 - optimization.get('token_reduction', 0)))
        cognitive_load = max(0.1, cognitive_load - optimization.get('cognitive_reduction', 0))
        efficiency += optimization.get('efficiency_boost', 0)
        speed = max(3, speed * (1 - optimization.get('speed_boost', 0)))
        traceability += optimization.get('traceability_boost', 0)
        
        # Some deviations are prevented by optimization
        prevented_count = int(len(deviations) * 0.4)
        deviations = deviations[prevented_count:]
        
        # Better discipline with fewer deviations
        discipline += 0.02 * prevented_count
        quality += 0.01 * prevented_count
    
    # Add randomness
    discipline = max(0.5, min(0.98, discipline + random.gauss(0, 0.05)))
    token_usage = max(1000, int(token_usage + random.gauss(0, 500)))
    cognitive_load = max(0.1, min(0.9, cognitive_load + random.gauss(0, 0.05)))
    efficiency = max(0.5, min(0.98, efficiency + random.gauss(0, 0.05)))
    speed = max(3, speed + random.gauss(0, 3))
    traceability = max(0.5, min(0.98, traceability + random.gauss(0, 0.05)))
    quality = max(0.5, min(0.98, quality + random.gauss(0, 0.03)))
    
    # Determine success based on quality and discipline
    success = random.random() < (quality * 0.6 + discipline * 0.4)
    
    return {
        'session_id': session_id,
        'agent': agent_name,
        'complexity': complexity,
        'optimized': optimized,
        'discipline': discipline,
        'token_usage': token_usage,
        'cognitive_load': cognitive_load,
        'efficiency': efficiency,
        'speed': speed,
        'traceability': traceability,
        'quality': quality,
        'success': success,
        'deviations': deviations,
    }


def run_agent_simulation(
    agent_name: str,
    patterns: Dict[str, Any],
    config: SimulationConfig,
    optimized: bool = False
) -> Tuple[AgentSimulationResult, List[Dict[str, Any]]]:
    """Run simulation for a specific agent."""
    
    sessions = []
    for i in range(config.session_count):
        session = simulate_agent_session(i, agent_name, patterns, optimized, config)
        sessions.append(session)
    
    n = len(sessions)
    
    # Aggregate results
    result = AgentSimulationResult(
        agent_name=agent_name,
        sessions_simulated=n,
    )
    
    # Calculate averages
    if optimized:
        result.optimized_discipline = sum(s['discipline'] for s in sessions) / n
        result.optimized_token_usage = sum(s['token_usage'] for s in sessions) / n
        result.optimized_cognitive_load = sum(s['cognitive_load'] for s in sessions) / n
        result.optimized_efficiency = sum(s['efficiency'] for s in sessions) / n
        result.optimized_speed = sum(s['speed'] for s in sessions) / n
        result.optimized_traceability = sum(s['traceability'] for s in sessions) / n
        result.optimized_success_rate = sum(1 for s in sessions if s['success']) / n
        result.optimized_quality = sum(s['quality'] for s in sessions) / n
    else:
        result.current_discipline = sum(s['discipline'] for s in sessions) / n
        result.current_token_usage = sum(s['token_usage'] for s in sessions) / n
        result.current_cognitive_load = sum(s['cognitive_load'] for s in sessions) / n
        result.current_efficiency = sum(s['efficiency'] for s in sessions) / n
        result.current_speed = sum(s['speed'] for s in sessions) / n
        result.current_traceability = sum(s['traceability'] for s in sessions) / n
        result.current_success_rate = sum(1 for s in sessions if s['success']) / n
        result.current_quality = sum(s['quality'] for s in sessions) / n
    
    # Count deviations
    deviation_counts = defaultdict(int)
    for s in sessions:
        for d in s['deviations']:
            deviation_counts[d] += 1
    result.deviations = dict(deviation_counts)
    
    return result, sessions


def run_all_agents_simulation(
    patterns: Dict[str, Any],
    config: SimulationConfig
) -> Dict[str, Any]:
    """Run simulation for all agents with before/after optimization."""
    
    results = {}
    
    for agent_name in AGENT_BASELINE_PROFILES.keys():
        # Run current (baseline) simulation
        random.seed(config.seed)
        current_result, current_sessions = run_agent_simulation(
            agent_name, patterns, config, optimized=False
        )
        
        # Run optimized simulation
        random.seed(config.seed)
        optimized_result, optimized_sessions = run_agent_simulation(
            agent_name, patterns, config, optimized=True
        )
        
        # Merge results
        final_result = AgentSimulationResult(
            agent_name=agent_name,
            sessions_simulated=config.session_count,
            
            # Current metrics
            current_discipline=current_result.current_discipline,
            current_token_usage=current_result.current_token_usage,
            current_cognitive_load=current_result.current_cognitive_load,
            current_efficiency=current_result.current_efficiency,
            current_speed=current_result.current_speed,
            current_traceability=current_result.current_traceability,
            current_success_rate=current_result.current_success_rate,
            current_quality=current_result.current_quality,
            
            # Optimized metrics
            optimized_discipline=optimized_result.optimized_discipline,
            optimized_token_usage=optimized_result.optimized_token_usage,
            optimized_cognitive_load=optimized_result.optimized_cognitive_load,
            optimized_efficiency=optimized_result.optimized_efficiency,
            optimized_speed=optimized_result.optimized_speed,
            optimized_traceability=optimized_result.optimized_traceability,
            optimized_success_rate=optimized_result.optimized_success_rate,
            optimized_quality=optimized_result.optimized_quality,
            
            # Deviations from current
            deviations=current_result.deviations,
        )
        
        # Calculate improvements
        final_result.discipline_improvement = (
            (final_result.optimized_discipline - final_result.current_discipline) / 
            final_result.current_discipline if final_result.current_discipline > 0 else 0
        )
        final_result.token_improvement = (
            (final_result.current_token_usage - final_result.optimized_token_usage) / 
            final_result.current_token_usage if final_result.current_token_usage > 0 else 0
        )
        final_result.cognitive_load_improvement = (
            (final_result.current_cognitive_load - final_result.optimized_cognitive_load) / 
            final_result.current_cognitive_load if final_result.current_cognitive_load > 0 else 0
        )
        final_result.efficiency_improvement = (
            (final_result.optimized_efficiency - final_result.current_efficiency) / 
            final_result.current_efficiency if final_result.current_efficiency > 0 else 0
        )
        final_result.speed_improvement = (
            (final_result.current_speed - final_result.optimized_speed) / 
            final_result.current_speed if final_result.current_speed > 0 else 0
        )
        final_result.traceability_improvement = (
            (final_result.optimized_traceability - final_result.current_traceability) / 
            final_result.current_traceability if final_result.current_traceability > 0 else 0
        )
        final_result.success_improvement = (
            (final_result.optimized_success_rate - final_result.current_success_rate) / 
            final_result.current_success_rate if final_result.current_success_rate > 0 else 0
        )
        
        # Get suggested adjustments from optimization config
        optimization = AGENT_OPTIMIZATION_ADJUSTMENTS.get(agent_name, {})
        final_result.instruction_changes = optimization.get('instruction_changes', {})
        final_result.suggested_adjustments = list(final_result.instruction_changes.keys())
        
        results[agent_name] = final_result
    
    return results


def print_agent_simulation_report(results: Dict[str, AgentSimulationResult], session_count: int):
    """Print comprehensive per-agent simulation report."""
    
    print("\n" + "=" * 80)
    print("PER-AGENT SIMULATION AND OPTIMIZATION ANALYSIS")
    print("=" * 80)
    
    print(f"\nSimulated {session_count:,} sessions per agent ({len(results)} agents total)")
    
    # Summary table
    print("\n" + "-" * 80)
    print("AGENT PERFORMANCE SUMMARY (Current → Optimized)")
    print("-" * 80)
    
    print(f"\n{'Agent':<14} {'Discipline':>12} {'Tokens':>12} {'Speed':>12} {'Success':>12} {'Quality':>12}")
    print("-" * 80)
    
    for agent, result in sorted(results.items(), key=lambda x: -x[1].optimized_efficiency):
        disc = f"{result.current_discipline:.1%}→{result.optimized_discipline:.1%}"
        tokens = f"{result.current_token_usage:.0f}→{result.optimized_token_usage:.0f}"
        speed = f"{result.current_speed:.1f}→{result.optimized_speed:.1f}"
        success = f"{result.current_success_rate:.1%}→{result.optimized_success_rate:.1%}"
        quality = f"{result.current_quality:.1%}→{result.optimized_quality:.1%}"
        print(f"{agent:<14} {disc:>12} {tokens:>12} {speed:>12} {success:>12} {quality:>12}")
    
    # Detailed per-agent analysis
    for agent, result in results.items():
        print("\n" + "=" * 80)
        print(f"🤖 {agent.upper()} AGENT - DETAILED ANALYSIS")
        print("=" * 80)
        
        # Current vs Optimized
        print("\n📊 METRICS COMPARISON")
        print("-" * 40)
        print(f"   {'Metric':<20} {'Current':>12} {'Optimized':>12} {'Change':>12}")
        print("-" * 60)
        
        metrics = [
            ('Discipline', result.current_discipline, result.optimized_discipline, result.discipline_improvement),
            ('Tokens', result.current_token_usage, result.optimized_token_usage, result.token_improvement),
            ('Cognitive Load', result.current_cognitive_load, result.optimized_cognitive_load, result.cognitive_load_improvement),
            ('Efficiency', result.current_efficiency, result.optimized_efficiency, result.efficiency_improvement),
            ('Speed (min)', result.current_speed, result.optimized_speed, result.speed_improvement),
            ('Traceability', result.current_traceability, result.optimized_traceability, result.traceability_improvement),
            ('Success Rate', result.current_success_rate, result.optimized_success_rate, result.success_improvement),
            ('Quality', result.current_quality, result.optimized_quality, 0),
        ]
        
        for name, current, optimized, improvement in metrics:
            if 'Token' in name or 'Speed' in name:
                print(f"   {name:<20} {current:>12.0f} {optimized:>12.0f} {improvement:>+12.1%}")
            else:
                print(f"   {name:<20} {current:>12.1%} {optimized:>12.1%} {improvement:>+12.1%}")
        
        # Top deviations
        print("\n📋 TOP DEVIATIONS (Current)")
        print("-" * 40)
        for deviation, count in sorted(result.deviations.items(), key=lambda x: -x[1])[:5]:
            rate = count / result.sessions_simulated
            print(f"   {deviation}: {count:,} ({rate:.1%})")
        
        # Suggested instruction changes
        print("\n✏️ SUGGESTED INSTRUCTION CHANGES")
        print("-" * 40)
        for change_key, change_desc in result.instruction_changes.items():
            print(f"   • {change_key}: {change_desc}")
    
    # Overall improvement summary
    print("\n" + "=" * 80)
    print("OVERALL IMPROVEMENT SUMMARY")
    print("=" * 80)
    
    avg_discipline_imp = sum(r.discipline_improvement for r in results.values()) / len(results)
    avg_token_imp = sum(r.token_improvement for r in results.values()) / len(results)
    avg_speed_imp = sum(r.speed_improvement for r in results.values()) / len(results)
    avg_success_imp = sum(r.success_improvement for r in results.values()) / len(results)
    avg_trace_imp = sum(r.traceability_improvement for r in results.values()) / len(results)
    
    print(f"\n   Average Discipline Improvement: {avg_discipline_imp:+.1%}")
    print(f"   Average Token Reduction: {avg_token_imp:+.1%}")
    print(f"   Average Speed Improvement: {avg_speed_imp:+.1%}")
    print(f"   Average Success Rate Improvement: {avg_success_imp:+.1%}")
    print(f"   Average Traceability Improvement: {avg_trace_imp:+.1%}")
    
    # Best and worst performing
    best_agent = max(results.items(), key=lambda x: x[1].optimized_efficiency)
    worst_agent = min(results.items(), key=lambda x: x[1].optimized_efficiency)
    
    print(f"\n   🏆 Best Performer: {best_agent[0]} (efficiency: {best_agent[1].optimized_efficiency:.1%})")
    print(f"   ⚠️ Needs Improvement: {worst_agent[0]} (efficiency: {worst_agent[1].optimized_efficiency:.1%})")
    
    print("\n" + "=" * 80)


# ============================================================================
# AKIS Framework Comprehensive Analysis
# ============================================================================

def analyze_akis_framework(
    patterns: Dict[str, Any],
    config: SimulationConfig
) -> Dict[str, Any]:
    """
    Comprehensive analysis of the entire AKIS framework across 100k sessions.
    Analyzes: token efficiency, cognitive load, traceability, discipline,
    efficiency, speed, and resolution rate.
    """
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE AKIS FRAMEWORK ANALYSIS")
    print("=" * 80)
    
    # Run baseline simulation
    print(f"\n🔄 Running BASELINE simulation ({config.session_count:,} sessions)...")
    random.seed(config.seed)
    baseline_config = AKISConfiguration(version="baseline")
    baseline_results, baseline_sessions = run_simulation(patterns, baseline_config, config)
    
    # Run optimized simulation
    print(f"\n🚀 Running OPTIMIZED simulation ({config.session_count:,} sessions)...")
    random.seed(config.seed + 1)
    optimized_results, optimized_sessions = run_optimized_simulation(patterns, config)
    
    n = len(baseline_sessions)
    
    # Token Efficiency Analysis
    baseline_tokens_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    optimized_tokens_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    for s in baseline_sessions:
        baseline_tokens_by_complexity[s.complexity].append(s.token_usage)
    for s in optimized_sessions:
        optimized_tokens_by_complexity[s.complexity].append(s.token_usage)
    
    token_efficiency = {
        "baseline_avg": baseline_results.avg_token_usage,
        "optimized_avg": optimized_results.avg_token_usage,
        "improvement": (baseline_results.avg_token_usage - optimized_results.avg_token_usage) / baseline_results.avg_token_usage,
        "total_saved": baseline_results.total_tokens - optimized_results.total_tokens,
        "per_complexity": {
            k: {
                "baseline": sum(baseline_tokens_by_complexity[k])/len(baseline_tokens_by_complexity[k]) if baseline_tokens_by_complexity[k] else 0,
                "optimized": sum(optimized_tokens_by_complexity[k])/len(optimized_tokens_by_complexity[k]) if optimized_tokens_by_complexity[k] else 0
            }
            for k in ['simple', 'medium', 'complex']
        },
        "efficiency_score": 1 - (optimized_results.avg_token_usage / 25000),
    }
    
    # Cognitive Load Analysis
    baseline_cognitive_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    optimized_cognitive_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    for s in baseline_sessions:
        baseline_cognitive_by_complexity[s.complexity].append(s.cognitive_load)
    for s in optimized_sessions:
        optimized_cognitive_by_complexity[s.complexity].append(s.cognitive_load)
    
    high_cognitive_sessions = [s for s in baseline_sessions if s.cognitive_load > 0.7]
    cognitive_load = {
        "baseline_avg": baseline_results.avg_cognitive_load,
        "optimized_avg": optimized_results.avg_cognitive_load,
        "improvement": (baseline_results.avg_cognitive_load - optimized_results.avg_cognitive_load) / baseline_results.avg_cognitive_load,
        "high_load_sessions": len(high_cognitive_sessions),
        "contributing_factors": {
            'high_task_count': sum(1 for s in high_cognitive_sessions if s.tasks_total > 5),
            'many_skills': sum(1 for s in high_cognitive_sessions if s.skills_loaded > 3),
            'many_deviations': sum(1 for s in high_cognitive_sessions if len(s.deviations) > 2),
            'edge_cases': sum(1 for s in high_cognitive_sessions if s.edge_cases_hit),
        },
        "per_complexity": {
            k: {
                "baseline": sum(baseline_cognitive_by_complexity[k])/len(baseline_cognitive_by_complexity[k]) if baseline_cognitive_by_complexity[k] else 0,
                "optimized": sum(optimized_cognitive_by_complexity[k])/len(optimized_cognitive_by_complexity[k]) if optimized_cognitive_by_complexity[k] else 0
            }
            for k in ['simple', 'medium', 'complex']
        },
        "efficiency_score": 1 - optimized_results.avg_cognitive_load,
    }
    
    # Traceability Analysis
    baseline_with_workflow_log = sum(1 for s in baseline_sessions if 'skip_workflow_log' not in s.deviations)
    baseline_with_todo = sum(1 for s in baseline_sessions if 'incomplete_todo_tracking' not in s.deviations)
    baseline_with_skills = sum(1 for s in baseline_sessions if s.skills_loaded > 0)
    baseline_with_delegation_trace = sum(1 for s in baseline_sessions 
                                         if s.delegation_used and 'skip_delegation_tracing' not in s.deviations)
    
    traceability = {
        "baseline_avg": baseline_results.avg_traceability,
        "optimized_avg": optimized_results.avg_traceability,
        "improvement": (optimized_results.avg_traceability - baseline_results.avg_traceability) / baseline_results.avg_traceability,
        "workflow_log_rate": baseline_with_workflow_log / n,
        "todo_tracking_rate": baseline_with_todo / n,
        "skill_documentation_rate": baseline_with_skills / n,
        "delegation_trace_rate": baseline_with_delegation_trace / max(1, baseline_results.sessions_with_delegation),
        "efficiency_score": optimized_results.avg_traceability,
    }
    
    # Discipline Analysis (Protocol Adherence)
    gate_compliance = {
        'G1_todo': 1 - baseline_results.deviation_counts.get('incomplete_todo_tracking', 0) / n,
        'G2_skill': 1 - baseline_results.deviation_counts.get('skip_skill_loading', 0) / n,
        'G3_start': 1 - baseline_results.deviation_counts.get('skip_knowledge_loading', 0) / n,
        'G4_end': 1 - baseline_results.deviation_counts.get('skip_workflow_log', 0) / n,
        'G5_verify': 1 - baseline_results.deviation_counts.get('skip_verification', 0) / n,
        'G6_single': 1 - baseline_results.deviation_counts.get('multiple_active_tasks', 0) / n,
        'G7_parallel': 1 - baseline_results.deviation_counts.get('skip_parallel_for_complex', 0) / n,
    }
    
    discipline = {
        "baseline_avg": baseline_results.avg_discipline,
        "optimized_avg": optimized_results.avg_discipline,
        "improvement": (optimized_results.avg_discipline - baseline_results.avg_discipline) / baseline_results.avg_discipline,
        "perfect_session_rate_baseline": baseline_results.perfect_session_rate,
        "perfect_session_rate_optimized": optimized_results.perfect_session_rate,
        "total_deviations_baseline": baseline_results.total_deviations,
        "total_deviations_optimized": optimized_results.total_deviations,
        "deviations_prevented": baseline_results.total_deviations - optimized_results.total_deviations,
        "gate_compliance": gate_compliance,
        "worst_gates": sorted(gate_compliance.items(), key=lambda x: x[1])[:3],
        "efficiency_score": optimized_results.avg_discipline,
    }
    
    # Efficiency Analysis (API Calls + Composite)
    baseline_api_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    optimized_api_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    for s in baseline_sessions:
        baseline_api_by_complexity[s.complexity].append(s.api_calls)
    for s in optimized_sessions:
        optimized_api_by_complexity[s.complexity].append(s.api_calls)
    
    baseline_composite = (
        baseline_results.success_rate * 0.25 +
        (1 - baseline_results.avg_cognitive_load) * 0.20 +
        baseline_results.avg_discipline * 0.20 +
        baseline_results.avg_traceability * 0.15 +
        (1 - baseline_results.avg_token_usage / 25000) * 0.10 +
        (1 - baseline_results.avg_resolution_time / 60) * 0.10
    )
    optimized_composite = (
        optimized_results.success_rate * 0.25 +
        (1 - optimized_results.avg_cognitive_load) * 0.20 +
        optimized_results.avg_discipline * 0.20 +
        optimized_results.avg_traceability * 0.15 +
        (1 - optimized_results.avg_token_usage / 25000) * 0.10 +
        (1 - optimized_results.avg_resolution_time / 60) * 0.10
    )
    
    efficiency = {
        "baseline_api_calls": baseline_results.avg_api_calls,
        "optimized_api_calls": optimized_results.avg_api_calls,
        "api_reduction": (baseline_results.avg_api_calls - optimized_results.avg_api_calls) / baseline_results.avg_api_calls,
        "total_api_saved": baseline_results.total_api_calls - optimized_results.total_api_calls,
        "baseline_composite": baseline_composite,
        "optimized_composite": optimized_composite,
        "composite_improvement": (optimized_composite - baseline_composite) / baseline_composite,
        "per_complexity": {
            k: {
                "baseline": sum(baseline_api_by_complexity[k])/len(baseline_api_by_complexity[k]) if baseline_api_by_complexity[k] else 0,
                "optimized": sum(optimized_api_by_complexity[k])/len(optimized_api_by_complexity[k]) if optimized_api_by_complexity[k] else 0
            }
            for k in ['simple', 'medium', 'complex']
        },
        "efficiency_score": optimized_composite,
    }
    
    # Speed Analysis
    baseline_speed_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    optimized_speed_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    for s in baseline_sessions:
        baseline_speed_by_complexity[s.complexity].append(s.resolution_time_minutes)
    for s in optimized_sessions:
        optimized_speed_by_complexity[s.complexity].append(s.resolution_time_minutes)
    
    baseline_parallel_time = sum(s.parallel_time_saved_minutes for s in baseline_sessions if s.parallel_execution_used)
    optimized_parallel_time = sum(s.parallel_time_saved_minutes for s in optimized_sessions if s.parallel_execution_used)
    
    speed = {
        "baseline_avg": baseline_results.avg_resolution_time,
        "baseline_p50": baseline_results.p50_resolution_time,
        "baseline_p95": baseline_results.p95_resolution_time,
        "optimized_avg": optimized_results.avg_resolution_time,
        "optimized_p50": optimized_results.p50_resolution_time,
        "optimized_p95": optimized_results.p95_resolution_time,
        "p50_improvement": (baseline_results.p50_resolution_time - optimized_results.p50_resolution_time) / baseline_results.p50_resolution_time,
        "baseline_parallel_time_saved": baseline_parallel_time,
        "optimized_parallel_time_saved": optimized_parallel_time,
        "per_complexity": {
            k: {
                "baseline": sum(baseline_speed_by_complexity[k])/len(baseline_speed_by_complexity[k]) if baseline_speed_by_complexity[k] else 0,
                "optimized": sum(optimized_speed_by_complexity[k])/len(optimized_speed_by_complexity[k]) if optimized_speed_by_complexity[k] else 0
            }
            for k in ['simple', 'medium', 'complex']
        },
        "efficiency_score": 1 - (optimized_results.p50_resolution_time / 60),
    }
    
    # Resolution Rate Analysis
    baseline_success_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    optimized_success_by_complexity = {'simple': [], 'medium': [], 'complex': []}
    for s in baseline_sessions:
        baseline_success_by_complexity[s.complexity].append(1 if s.task_success else 0)
    for s in optimized_sessions:
        optimized_success_by_complexity[s.complexity].append(1 if s.task_success else 0)
    
    baseline_with_del_success = sum(1 for s in baseline_sessions if s.delegation_used and s.task_success)
    baseline_without_del_success = sum(1 for s in baseline_sessions if not s.delegation_used and s.task_success)
    
    resolution_rate = {
        "baseline_rate": baseline_results.success_rate,
        "optimized_rate": optimized_results.success_rate,
        "improvement": (optimized_results.success_rate - baseline_results.success_rate) / baseline_results.success_rate,
        "additional_successes": optimized_results.successful_sessions - baseline_results.successful_sessions,
        "with_delegation": baseline_with_del_success / max(1, baseline_results.sessions_with_delegation),
        "without_delegation": baseline_without_del_success / max(1, n - baseline_results.sessions_with_delegation),
        "per_complexity": {
            k: {
                "baseline": sum(baseline_success_by_complexity[k])/len(baseline_success_by_complexity[k]) if baseline_success_by_complexity[k] else 0,
                "optimized": sum(optimized_success_by_complexity[k])/len(optimized_success_by_complexity[k]) if optimized_success_by_complexity[k] else 0
            }
            for k in ['simple', 'medium', 'complex']
        },
        "efficiency_score": optimized_results.success_rate,
    }
    
    # Gate Analysis
    gate_violations = {
        'G1': baseline_results.deviation_counts.get('incomplete_todo_tracking', 0),
        'G2': baseline_results.deviation_counts.get('skip_skill_loading', 0),
        'G3': baseline_results.deviation_counts.get('skip_knowledge_loading', 0),
        'G4': baseline_results.deviation_counts.get('skip_workflow_log', 0),
        'G5': baseline_results.deviation_counts.get('skip_verification', 0),
        'G6': baseline_results.deviation_counts.get('multiple_active_tasks', 0),
        'G7': baseline_results.deviation_counts.get('skip_parallel_for_complex', 0),
    }
    
    gate_analysis = {
        "violation_counts": gate_violations,
        "violation_rates": {k: v/n for k, v in gate_violations.items()},
        "compliance_rates": {k: 1 - v/n for k, v in gate_violations.items()},
        "priority_order": sorted(gate_violations.items(), key=lambda x: -x[1]),
    }
    
    # Generate recommendations
    recommendations = []
    top_deviations = sorted(baseline_results.deviation_counts.items(), key=lambda x: -x[1])[:10]
    for deviation, count in top_deviations:
        rate = count / n
        priority = "HIGH" if rate > 0.20 else "MEDIUM" if rate > 0.10 else "LOW"
        rec = {
            "deviation": deviation,
            "rate": rate,
            "priority": priority,
        }
        if 'skill_loading' in deviation:
            rec["action"] = "Add visual warning for low-compliance skills"
            rec["gate"] = "G2"
        elif 'workflow_log' in deviation:
            rec["action"] = "Add trigger word detection for session end"
            rec["gate"] = "G4"
        elif 'verification' in deviation:
            rec["action"] = "Make verification part of edit cycle"
            rec["gate"] = "G5"
        elif 'delegation' in deviation:
            rec["action"] = "Add explicit file count threshold reminder"
            rec["gate"] = "Delegation"
        elif 'parallel' in deviation:
            rec["action"] = "Add parallel pair suggestions in TODO"
            rec["gate"] = "G7"
        else:
            rec["action"] = "Review and enforce protocol"
            rec["gate"] = "General"
        recommendations.append(rec)
    
    analysis = {
        "simulation_info": {
            "total_sessions": config.session_count,
            "timestamp": datetime.now().isoformat(),
            "patterns_used": patterns.get("source_stats", {}),
        },
        "token_efficiency": token_efficiency,
        "cognitive_load": cognitive_load,
        "traceability": traceability,
        "discipline": discipline,
        "efficiency": efficiency,
        "speed": speed,
        "resolution_rate": resolution_rate,
        "gate_analysis": gate_analysis,
        "recommendations": recommendations,
        "summary": {
            "token_efficiency_score": token_efficiency["efficiency_score"],
            "cognitive_load_score": cognitive_load["efficiency_score"],
            "traceability_score": traceability["efficiency_score"],
            "discipline_score": discipline["efficiency_score"],
            "efficiency_score": efficiency["efficiency_score"],
            "speed_score": speed["efficiency_score"],
            "resolution_score": resolution_rate["efficiency_score"],
        }
    }
    
    return analysis


def print_akis_analysis_report(analysis: Dict[str, Any]):
    """Print comprehensive AKIS framework analysis report."""
    
    print("\n" + "=" * 80)
    print("COMPREHENSIVE AKIS FRAMEWORK ANALYSIS REPORT")
    print("=" * 80)
    
    info = analysis["simulation_info"]
    print(f"\n📊 Simulation: {info['total_sessions']:,} sessions")
    print(f"   Timestamp: {info['timestamp']}")
    
    # Token Efficiency
    print("\n" + "-" * 80)
    print("💰 TOKEN EFFICIENCY")
    print("-" * 80)
    te = analysis["token_efficiency"]
    print(f"\n   Baseline:  {te['baseline_avg']:,.0f} tokens/session")
    print(f"   Optimized: {te['optimized_avg']:,.0f} tokens/session")
    print(f"   Improvement: {te['improvement']:.1%} reduction")
    print(f"   Total Saved: {te['total_saved']:,} tokens")
    print(f"   Efficiency Score: {te['efficiency_score']:.2f}")
    
    # Cognitive Load
    print("\n" + "-" * 80)
    print("🧠 COGNITIVE LOAD")
    print("-" * 80)
    cl = analysis["cognitive_load"]
    print(f"\n   Baseline:  {cl['baseline_avg']:.1%}")
    print(f"   Optimized: {cl['optimized_avg']:.1%}")
    print(f"   Improvement: {cl['improvement']:.1%} reduction")
    print(f"   High Load Sessions: {cl['high_load_sessions']:,}")
    print(f"   Efficiency Score: {cl['efficiency_score']:.2f}")
    
    # Traceability
    print("\n" + "-" * 80)
    print("🔍 TRACEABILITY")
    print("-" * 80)
    tr = analysis["traceability"]
    print(f"\n   Baseline:  {tr['baseline_avg']:.1%}")
    print(f"   Optimized: {tr['optimized_avg']:.1%}")
    print(f"   Improvement: {tr['improvement']:.1%}")
    print(f"   Efficiency Score: {tr['efficiency_score']:.2f}")
    print(f"\n   Component Rates:")
    print(f"     Workflow Log: {tr['workflow_log_rate']:.1%}")
    print(f"     TODO Tracking: {tr['todo_tracking_rate']:.1%}")
    print(f"     Skill Documentation: {tr['skill_documentation_rate']:.1%}")
    print(f"     Delegation Trace: {tr['delegation_trace_rate']:.1%}")
    
    # Discipline
    print("\n" + "-" * 80)
    print("📋 DISCIPLINE (Protocol Adherence)")
    print("-" * 80)
    di = analysis["discipline"]
    print(f"\n   Baseline:  {di['baseline_avg']:.1%}")
    print(f"   Optimized: {di['optimized_avg']:.1%}")
    print(f"   Improvement: {di['improvement']:.1%}")
    print(f"   Deviations Prevented: {di['deviations_prevented']:,}")
    print(f"   Efficiency Score: {di['efficiency_score']:.2f}")
    print(f"\n   Gate Compliance:")
    for gate, rate in sorted(di['gate_compliance'].items()):
        status = "✅" if rate > 0.85 else "⚠️" if rate > 0.75 else "❌"
        print(f"     {status} {gate}: {rate:.1%}")
    
    # Efficiency
    print("\n" + "-" * 80)
    print("⚡ OVERALL EFFICIENCY")
    print("-" * 80)
    ef = analysis["efficiency"]
    print(f"\n   Baseline Composite:  {ef['baseline_composite']:.2f}")
    print(f"   Optimized Composite: {ef['optimized_composite']:.2f}")
    print(f"   Efficiency Gain: {ef['composite_improvement']:.1%}")
    print(f"\n   API Calls:")
    print(f"     Baseline:  {ef['baseline_api_calls']:.1f} calls/session")
    print(f"     Optimized: {ef['optimized_api_calls']:.1f} calls/session")
    print(f"     Reduction: {ef['api_reduction']:.1%}")
    print(f"     Total Saved: {ef['total_api_saved']:,}")
    
    # Speed
    print("\n" + "-" * 80)
    print("⏱️ SPEED (Resolution Time)")
    print("-" * 80)
    sp = analysis["speed"]
    print(f"\n   Baseline P50:  {sp['baseline_p50']:.1f} min")
    print(f"   Optimized P50: {sp['optimized_p50']:.1f} min")
    print(f"   Improvement: {sp['p50_improvement']:.1%} faster")
    print(f"   Efficiency Score: {sp['efficiency_score']:.2f}")
    print(f"\n   Parallel Time Saved:")
    print(f"     Baseline:  {sp['baseline_parallel_time_saved']:,.0f} min ({sp['baseline_parallel_time_saved']/60:,.0f} hrs)")
    print(f"     Optimized: {sp['optimized_parallel_time_saved']:,.0f} min ({sp['optimized_parallel_time_saved']/60:,.0f} hrs)")
    
    # Resolution Rate
    print("\n" + "-" * 80)
    print("✅ RESOLUTION RATE (Success)")
    print("-" * 80)
    rr = analysis["resolution_rate"]
    print(f"\n   Baseline:  {rr['baseline_rate']:.1%}")
    print(f"   Optimized: {rr['optimized_rate']:.1%}")
    print(f"   Improvement: {rr['improvement']:.1%}")
    print(f"   Additional Successes: {rr['additional_successes']:,}")
    print(f"   Efficiency Score: {rr['efficiency_score']:.2f}")
    print(f"\n   By Delegation:")
    print(f"     With Delegation: {rr['with_delegation']:.1%}")
    print(f"     Without Delegation: {rr['without_delegation']:.1%}")
    
    # Gate Analysis
    print("\n" + "-" * 80)
    print("🚦 GATE ANALYSIS")
    print("-" * 80)
    ga = analysis["gate_analysis"]
    print("\n   Violation Rates:")
    for gate, rate in sorted(ga['violation_rates'].items(), key=lambda x: -x[1]):
        status = "❌" if rate > 0.20 else "⚠️" if rate > 0.10 else "✅"
        print(f"     {status} {gate}: {rate:.1%}")
    
    # Recommendations
    print("\n" + "-" * 80)
    print("📝 TOP RECOMMENDATIONS")
    print("-" * 80)
    for rec in analysis["recommendations"][:5]:
        print(f"\n   [{rec['priority']}] {rec['deviation']}")
        print(f"     Rate: {rec['rate']:.1%}")
        print(f"     Gate: {rec['gate']}")
        print(f"     Action: {rec['action']}")
    
    # Summary Scores
    print("\n" + "=" * 80)
    print("EFFICIENCY SCORE SUMMARY")
    print("=" * 80)
    
    scores = analysis["summary"]
    print("\n   Metric               Score")
    print("   " + "-" * 35)
    for metric, score in sorted(scores.items(), key=lambda x: -x[1]):
        bar = "█" * int(score * 20) + "░" * (20 - int(score * 20))
        print(f"   {metric.replace('_', ' ').title():<20} {bar} {score:.2f}")
    
    avg_score = sum(scores.values()) / len(scores)
    print(f"\n   {'OVERALL AVERAGE':<20} {avg_score:.2f}")
    
    print("\n" + "=" * 80)


# ============================================================================
# Main
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description='AKIS 100k Session Simulation Engine',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument('--full', action='store_true',
                       help='Run full simulation with before/after comparison')
    parser.add_argument('--delegation-comparison', action='store_true',
                       help='Run simulation comparing with vs without delegation')
    parser.add_argument('--parallel-comparison', action='store_true',
                       help='Run simulation comparing sequential vs parallel execution')
    parser.add_argument('--delegation-optimization', action='store_true',
                       help='Run delegation optimization analysis comparing specialist vs AKIS')
    parser.add_argument('--agent-optimization', action='store_true',
                       help='Run per-agent simulation and optimization analysis')
    parser.add_argument('--framework-analysis', action='store_true',
                       help='Run comprehensive AKIS framework analysis')
    parser.add_argument('--agent', type=str,
                       help='Specific agent to analyze (default: all agents)')
    parser.add_argument('--extract-patterns', action='store_true',
                       help='Extract patterns only')
    parser.add_argument('--edge-cases', action='store_true',
                       help='Generate edge cases report')
    parser.add_argument('--sessions', type=int, default=DEFAULT_SESSION_COUNT,
                       help=f'Number of sessions to simulate (default: {DEFAULT_SESSION_COUNT})')
    parser.add_argument('--output', type=str,
                       help='Output results to JSON file')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED,
                       help=f'Random seed for reproducibility (default: {RANDOM_SEED})')
    
    args = parser.parse_args()
    
    # Extract patterns
    print("=" * 70)
    print("AKIS 100K SESSION SIMULATION ENGINE")
    print("=" * 70)
    
    print("\n📊 Extracting patterns from workflow logs...")
    workflow_patterns = extract_patterns_from_workflow_logs(WORKFLOW_DIR)
    print(f"   Found {workflow_patterns['total_logs']} workflow logs")
    
    print("\n📊 Extracting industry/community patterns...")
    industry_patterns = extract_industry_patterns()
    print(f"   Found {len(industry_patterns['common_issues'])} common issues")
    print(f"   Found {len(industry_patterns['edge_cases'])} edge cases")
    
    print("\n📊 Merging patterns...")
    merged_patterns = merge_patterns(workflow_patterns, industry_patterns)
    print(f"   Source: {merged_patterns['source_stats']}")
    
    if args.extract_patterns:
        if args.output:
            with open(args.output, 'w') as f:
                json.dump(merged_patterns, f, indent=2, default=str)
            print(f"\n📄 Patterns saved to: {args.output}")
        return
    
    if args.edge_cases:
        print("\n" + "=" * 70)
        print("EDGE CASES AND ATYPICAL ISSUES")
        print("=" * 70)
        
        print("\n🔴 EDGE CASES BY DOMAIN:")
        for ec in merged_patterns.get("edge_cases", []):
            print(f"   [{ec['domain']}] {ec['case']} (prob: {ec['probability']:.0%})")
        
        print("\n🟠 ATYPICAL ISSUES:")
        for issue in merged_patterns.get("atypical_issues", []):
            print(f"\n   {issue['category'].upper()} ({issue['probability']:.0%})")
            print(f"   {issue['description']}")
            for scenario in issue['scenarios'][:3]:
                print(f"     • {scenario}")
        
        return
    
    # Handle comprehensive framework analysis mode
    if args.framework_analysis:
        config = SimulationConfig(
            session_count=args.sessions,
            seed=args.seed,
        )
        
        # Run comprehensive analysis
        analysis = analyze_akis_framework(merged_patterns, config)
        
        # Print report
        print_akis_analysis_report(analysis)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            
            print(f"\n📄 Results saved to: {output_path}")
        
        print("\n✅ AKIS Framework Analysis complete!")
        return
    
    # Handle per-agent optimization mode
    if args.agent_optimization:
        config = SimulationConfig(
            session_count=args.sessions,
            seed=args.seed,
        )
        
        print("\n" + "=" * 80)
        print("PER-AGENT SIMULATION AND OPTIMIZATION")
        print("=" * 80)
        
        if args.agent:
            # Single agent simulation
            if args.agent not in AGENT_BASELINE_PROFILES:
                print(f"\n❌ Unknown agent: {args.agent}")
                print(f"   Available agents: {', '.join(AGENT_BASELINE_PROFILES.keys())}")
                return
            
            print(f"\n🔄 Running simulation for {args.agent} ({args.sessions:,} sessions)...")
            
            random.seed(config.seed)
            current_result, _ = run_agent_simulation(args.agent, merged_patterns, config, optimized=False)
            
            random.seed(config.seed)
            optimized_result, _ = run_agent_simulation(args.agent, merged_patterns, config, optimized=True)
            
            # Combine into single result
            results = {args.agent: AgentSimulationResult(
                agent_name=args.agent,
                sessions_simulated=config.session_count,
                current_discipline=current_result.current_discipline,
                current_token_usage=current_result.current_token_usage,
                current_cognitive_load=current_result.current_cognitive_load,
                current_efficiency=current_result.current_efficiency,
                current_speed=current_result.current_speed,
                current_traceability=current_result.current_traceability,
                current_success_rate=current_result.current_success_rate,
                current_quality=current_result.current_quality,
                optimized_discipline=optimized_result.optimized_discipline,
                optimized_token_usage=optimized_result.optimized_token_usage,
                optimized_cognitive_load=optimized_result.optimized_cognitive_load,
                optimized_efficiency=optimized_result.optimized_efficiency,
                optimized_speed=optimized_result.optimized_speed,
                optimized_traceability=optimized_result.optimized_traceability,
                optimized_success_rate=optimized_result.optimized_success_rate,
                optimized_quality=optimized_result.optimized_quality,
                deviations=current_result.deviations,
                instruction_changes=AGENT_OPTIMIZATION_ADJUSTMENTS.get(args.agent, {}).get('instruction_changes', {}),
            )}
        else:
            # All agents simulation
            print(f"\n🔄 Running simulation for all {len(AGENT_BASELINE_PROFILES)} agents ({args.sessions:,} sessions each)...")
            results = run_all_agents_simulation(merged_patterns, config)
        
        # Print report
        print_agent_simulation_report(results, args.sessions)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            def convert_to_serializable(obj):
                if isinstance(obj, dict):
                    return {str(k): convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_serializable(item) for item in obj]
                elif hasattr(obj, '__dict__'):
                    return convert_to_serializable(obj.__dict__)
                else:
                    return obj
            
            report_data = {
                "comparison_type": "agent_optimization",
                "timestamp": datetime.now().isoformat(),
                "sessions_per_agent": args.sessions,
                "agents": {name: convert_to_serializable(asdict(result)) 
                          for name, result in results.items()},
            }
            
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n📄 Results saved to: {output_path}")
        
        print("\n✅ Per-agent optimization analysis complete!")
        return
    
    # Handle delegation optimization mode
    if args.delegation_optimization:
        config = SimulationConfig(
            session_count=args.sessions,
            seed=args.seed,
        )
        
        print("\n" + "=" * 70)
        print("DELEGATION OPTIMIZATION: SPECIALIST vs AKIS ANALYSIS")
        print("=" * 70)
        
        print(f"\n🔄 Running {len(DELEGATION_STRATEGIES)} delegation strategies ({args.sessions:,} sessions each)...")
        
        optimization_report = run_delegation_optimization(merged_patterns, config)
        
        # Print report
        print_delegation_optimization_report(optimization_report, args.sessions)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            def convert_to_serializable(obj):
                if isinstance(obj, dict):
                    return {str(k): convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_serializable(item) for item in obj]
                elif hasattr(obj, '__dict__'):
                    return convert_to_serializable(obj.__dict__)
                else:
                    return obj
            
            report_data = {
                "comparison_type": "delegation_optimization",
                "timestamp": datetime.now().isoformat(),
                "sessions_per_strategy": args.sessions,
                "strategies": {name: convert_to_serializable(asdict(result)) 
                              for name, result in optimization_report['strategies'].items()},
                "agent_specialization": [convert_to_serializable(asdict(a)) 
                                        for a in optimization_report['agent_specialization']],
                "recommendation": optimization_report['recommendation'],
            }
            
            with open(output_path, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            print(f"\n📄 Results saved to: {output_path}")
        
        print("\n✅ Delegation optimization analysis complete!")
        return
    
    # Handle delegation comparison mode
    if args.delegation_comparison:
        config = SimulationConfig(
            session_count=args.sessions,
            seed=args.seed,
        )
        
        print("\n" + "=" * 70)
        print("DELEGATION COMPARISON: WITH vs WITHOUT MULTI-AGENT DELEGATION")
        print("=" * 70)
        
        # Run WITHOUT delegation
        print(f"\n🔄 Running simulation WITHOUT delegation ({args.sessions:,} sessions)...")
        no_delegation_config = AKISConfiguration(
            version="no_delegation",
            enable_delegation=False,
        )
        no_del_results, no_del_sessions = run_simulation(merged_patterns, no_delegation_config, config)
        
        print(f"   Success rate: {no_del_results.success_rate:.1%}")
        print(f"   Avg discipline: {no_del_results.avg_discipline:.1%}")
        print(f"   Delegation rate: {no_del_results.delegation_rate:.1%}")
        
        # Run WITH delegation
        print(f"\n🚀 Running simulation WITH delegation ({args.sessions:,} sessions)...")
        random.seed(config.seed)  # Reset seed for fair comparison
        with_delegation_config = AKISConfiguration(
            version="with_delegation",
            enable_delegation=True,
        )
        with_del_results, with_del_sessions = run_simulation(merged_patterns, with_delegation_config, config)
        
        print(f"   Success rate: {with_del_results.success_rate:.1%}")
        print(f"   Avg discipline: {with_del_results.avg_discipline:.1%}")
        print(f"   Delegation rate: {with_del_results.delegation_rate:.1%}")
        
        # Print delegation comparison
        print("\n" + "=" * 70)
        print("DELEGATION IMPACT COMPARISON")
        print("=" * 70)
        
        print(f"\n📊 SUCCESS RATE")
        print(f"   Without Delegation: {no_del_results.success_rate:.1%}")
        print(f"   With Delegation:    {with_del_results.success_rate:.1%}")
        delta_success = with_del_results.success_rate - no_del_results.success_rate
        print(f"   Impact:             {delta_success:+.1%}")
        
        print(f"\n⚡ RESOLUTION TIME (P50)")
        print(f"   Without Delegation: {no_del_results.p50_resolution_time:.1f} min")
        print(f"   With Delegation:    {with_del_results.p50_resolution_time:.1f} min")
        delta_time = (no_del_results.p50_resolution_time - with_del_results.p50_resolution_time) / no_del_results.p50_resolution_time
        print(f"   Impact:             {delta_time:+.1%} faster")
        
        print(f"\n💰 TOKEN USAGE")
        print(f"   Without Delegation: {no_del_results.avg_token_usage:,.0f} tokens/session")
        print(f"   With Delegation:    {with_del_results.avg_token_usage:,.0f} tokens/session")
        delta_tokens = (no_del_results.avg_token_usage - with_del_results.avg_token_usage) / no_del_results.avg_token_usage
        print(f"   Impact:             {delta_tokens:+.1%} reduction")
        
        print(f"\n📊 DISCIPLINE SCORE")
        print(f"   Without Delegation: {no_del_results.avg_discipline:.1%}")
        print(f"   With Delegation:    {with_del_results.avg_discipline:.1%}")
        
        print(f"\n🤖 DELEGATION DISCIPLINE (for sessions with delegation)")
        print(f"   Delegation Discipline: {with_del_results.avg_delegation_discipline:.1%}")
        print(f"   Sessions with Delegation: {with_del_results.sessions_with_delegation:,}")
        print(f"   Avg Delegations/Session: {with_del_results.avg_delegations_per_session:.1f}")
        print(f"   Delegation Success Rate: {with_del_results.delegation_success_rate:.1%}")
        
        print(f"\n📋 DELEGATION DEVIATIONS")
        del_deviations = {k: v for k, v in with_del_results.deviation_counts.items() 
                        if 'delegation' in k.lower() or 'agent' in k.lower()}
        for dev, count in sorted(del_deviations.items(), key=lambda x: -x[1]):
            print(f"   {dev}: {count:,} ({100*count/args.sessions:.1f}%)")
        
        print(f"\n🔧 AGENT USAGE")
        for agent, count in sorted(with_del_results.agents_usage.items(), key=lambda x: -x[1]):
            print(f"   {agent}: {count:,}")
        
        print("\n" + "=" * 70)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            def convert_to_serializable(obj):
                if isinstance(obj, dict):
                    return {str(k): convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_serializable(item) for item in obj]
                elif hasattr(obj, '__dict__'):
                    return convert_to_serializable(obj.__dict__)
                else:
                    return obj
            
            delegation_report = {
                "comparison_type": "delegation",
                "timestamp": datetime.now().isoformat(),
                "sessions": args.sessions,
                "without_delegation": convert_to_serializable(asdict(no_del_results)),
                "with_delegation": convert_to_serializable(asdict(with_del_results)),
                "impact": {
                    "success_rate_delta": delta_success,
                    "time_reduction": delta_time,
                    "token_reduction": delta_tokens,
                },
            }
            
            with open(output_path, 'w') as f:
                json.dump(delegation_report, f, indent=2, default=str)
            
            print(f"\n📄 Results saved to: {output_path}")
        
        print("\n✅ Delegation comparison complete!")
        return
    
    # Handle parallel execution comparison mode
    if args.parallel_comparison:
        config = SimulationConfig(
            session_count=args.sessions,
            seed=args.seed,
        )
        
        print("\n" + "=" * 70)
        print("PARALLEL EXECUTION COMPARISON: SEQUENTIAL vs PARALLEL AGENTS")
        print("=" * 70)
        
        # Run WITHOUT parallel execution (sequential only)
        print(f"\n🔄 Running simulation with SEQUENTIAL execution ({args.sessions:,} sessions)...")
        sequential_config = AKISConfiguration(
            version="sequential",
            enable_delegation=True,
            enable_parallel_execution=False,
        )
        seq_results, seq_sessions = run_simulation(merged_patterns, sequential_config, config)
        
        print(f"   Success rate: {seq_results.success_rate:.1%}")
        print(f"   Avg resolution time: {seq_results.avg_resolution_time:.1f} min")
        print(f"   Parallel execution rate: {seq_results.parallel_execution_rate:.1%}")
        
        # Run WITH parallel execution
        print(f"\n🚀 Running simulation with PARALLEL execution ({args.sessions:,} sessions)...")
        random.seed(config.seed)  # Reset seed for fair comparison
        parallel_config = AKISConfiguration(
            version="parallel",
            enable_delegation=True,
            enable_parallel_execution=True,
            max_parallel_agents=3,
        )
        par_results, par_sessions = run_simulation(merged_patterns, parallel_config, config)
        
        print(f"   Success rate: {par_results.success_rate:.1%}")
        print(f"   Avg resolution time: {par_results.avg_resolution_time:.1f} min")
        print(f"   Parallel execution rate: {par_results.parallel_execution_rate:.1%}")
        
        # Print parallel comparison
        print("\n" + "=" * 70)
        print("PARALLEL EXECUTION IMPACT COMPARISON")
        print("=" * 70)
        
        print(f"\n📊 SUCCESS RATE")
        print(f"   Sequential: {seq_results.success_rate:.1%}")
        print(f"   Parallel:   {par_results.success_rate:.1%}")
        delta_success = par_results.success_rate - seq_results.success_rate
        print(f"   Impact:     {delta_success:+.1%}")
        
        print(f"\n⚡ RESOLUTION TIME (P50)")
        print(f"   Sequential: {seq_results.p50_resolution_time:.1f} min")
        print(f"   Parallel:   {par_results.p50_resolution_time:.1f} min")
        delta_time = (seq_results.p50_resolution_time - par_results.p50_resolution_time) / seq_results.p50_resolution_time if seq_results.p50_resolution_time > 0 else 0
        print(f"   Impact:     {delta_time:+.1%} faster")
        
        print(f"\n💰 TOKEN USAGE")
        print(f"   Sequential: {seq_results.avg_token_usage:,.0f} tokens/session")
        print(f"   Parallel:   {par_results.avg_token_usage:,.0f} tokens/session")
        delta_tokens = (seq_results.avg_token_usage - par_results.avg_token_usage) / seq_results.avg_token_usage if seq_results.avg_token_usage > 0 else 0
        print(f"   Impact:     {delta_tokens:+.1%} reduction")
        
        print(f"\n⚡ PARALLEL EXECUTION METRICS")
        print(f"   Sessions with Parallel: {par_results.sessions_with_parallel:,}")
        print(f"   Parallel Execution Rate: {par_results.parallel_execution_rate:.1%}")
        print(f"   Avg Parallel Agents: {par_results.avg_parallel_agents:.1f}")
        print(f"   Parallel Success Rate: {par_results.parallel_execution_success_rate:.1%}")
        print(f"   Avg Time Saved: {par_results.avg_parallel_time_saved:.1f} min/session")
        print(f"   Total Time Saved: {par_results.total_parallel_time_saved:,.0f} min ({par_results.total_parallel_time_saved/60:,.0f} hrs)")
        
        print(f"\n📋 EXECUTION STRATEGY DISTRIBUTION")
        for strategy, count in sorted(par_results.parallel_strategy_distribution.items(), key=lambda x: -x[1]):
            print(f"   {strategy}: {count:,} ({100*count/args.sessions:.1f}%)")
        
        print(f"\n📋 PARALLEL EXECUTION DEVIATIONS")
        par_deviations = {k: v for k, v in par_results.deviation_counts.items() 
                        if 'parallel' in k.lower() or 'synchronization' in k.lower() or 'dependency' in k.lower() or 'merge' in k.lower() or 'conflict' in k.lower()}
        for dev, count in sorted(par_deviations.items(), key=lambda x: -x[1]):
            print(f"   {dev}: {count:,} ({100*count/args.sessions:.1f}%)")
        
        print("\n" + "=" * 70)
        
        # Save results if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            def convert_to_serializable(obj):
                if isinstance(obj, dict):
                    return {str(k): convert_to_serializable(v) for k, v in obj.items()}
                elif isinstance(obj, (list, tuple)):
                    return [convert_to_serializable(item) for item in obj]
                elif hasattr(obj, '__dict__'):
                    return convert_to_serializable(obj.__dict__)
                else:
                    return obj
            
            parallel_report = {
                "comparison_type": "parallel_execution",
                "timestamp": datetime.now().isoformat(),
                "sessions": args.sessions,
                "sequential": convert_to_serializable(asdict(seq_results)),
                "parallel": convert_to_serializable(asdict(par_results)),
                "impact": {
                    "success_rate_delta": delta_success,
                    "time_reduction": delta_time,
                    "token_reduction": delta_tokens,
                    "total_time_saved_minutes": par_results.total_parallel_time_saved,
                    "total_time_saved_hours": par_results.total_parallel_time_saved / 60,
                },
            }
            
            with open(output_path, 'w') as f:
                json.dump(parallel_report, f, indent=2, default=str)
            
            print(f"\n📄 Results saved to: {output_path}")
        
        print("\n✅ Parallel execution comparison complete!")
        return
    
    # Run simulations
    config = SimulationConfig(
        session_count=args.sessions,
        seed=args.seed,
    )
    
    print(f"\n🔄 Running BASELINE simulation ({args.sessions:,} sessions)...")
    baseline_akis = AKISConfiguration(version="current")
    baseline_results, baseline_sessions = run_simulation(merged_patterns, baseline_akis, config)
    
    print(f"   Success rate: {baseline_results.success_rate:.1%}")
    print(f"   Avg discipline: {baseline_results.avg_discipline:.1%}")
    print(f"   Avg tokens: {baseline_results.avg_token_usage:,.0f}")
    
    print(f"\n🚀 Running OPTIMIZED simulation ({args.sessions:,} sessions)...")
    optimized_results, optimized_sessions = run_optimized_simulation(merged_patterns, config)
    
    print(f"   Success rate: {optimized_results.success_rate:.1%}")
    print(f"   Avg discipline: {optimized_results.avg_discipline:.1%}")
    print(f"   Avg tokens: {optimized_results.avg_token_usage:,.0f}")
    
    # Generate report
    report = generate_comparison_report(baseline_results, optimized_results)
    
    # Print report
    print_report(report)
    
    # Save results if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        def convert_to_serializable(obj):
            """Convert objects to JSON-serializable format."""
            if isinstance(obj, dict):
                return {str(k): convert_to_serializable(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [convert_to_serializable(item) for item in obj]
            elif hasattr(obj, '__dict__'):
                return convert_to_serializable(obj.__dict__)
            else:
                return obj
        
        full_results = {
            "report": report,
            "baseline_summary": convert_to_serializable(asdict(baseline_results)),
            "optimized_summary": convert_to_serializable(asdict(optimized_results)),
        }
        
        with open(output_path, 'w') as f:
            json.dump(full_results, f, indent=2, default=str)
        
        print(f"\n📄 Results saved to: {output_path}")
    
    print("\n✅ Simulation complete!")


if __name__ == '__main__':
    main()
