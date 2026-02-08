#!/usr/bin/env python3
"""
manage_todo_list Metadata Enhancement Simulation v1.0

100k session simulation comparing:
1. BASELINE - No metadata (current behavior)
2. METADATA_ENHANCED - manage_todo_list with rich metadata
3. SESSION_JSON_PLAN - session.json PLAN-ONCE pattern
4. HYBRID - Metadata + session.json combined

Measures:
- Token efficiency and overhead
- Delegation chain visibility  
- Traceability improvement
- Memory footprint
- Implementation complexity impact

Usage:
    python simulate_metadata_enhancement.py --full       # Full 100k simulation
    python simulate_metadata_enhancement.py --quick      # Quick 10k sample
    python simulate_metadata_enhancement.py --output FILE

Author: AKIS Framework Analysis
Date: 2026-01-15
"""

import json
import random
import argparse
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
import uuid

# ============================================================================
# Configuration
# ============================================================================

RANDOM_SEED = 42

# Session complexity distribution
SESSION_MIX = {
    "simple": 0.40,      # 1-3 tasks, no delegation
    "medium": 0.35,      # 4-8 tasks, 1 level delegation
    "complex": 0.20,     # 9-15 tasks, 2 level delegation
    "extreme": 0.05      # 16+ tasks, 3+ level delegation
}

# Task count ranges
TASK_COUNTS = {
    "simple": (1, 3),
    "medium": (4, 8),
    "complex": (9, 15),
    "extreme": (16, 25),
}

# Delegation depth by session type
DELEGATION_DEPTH = {
    "simple": 0,
    "medium": 1,
    "complex": 2,
    "extreme": 3,
}

# Agent types for delegation
AGENTS = ["AKIS", "architect", "code", "researcher", "debugger", "documentation"]

# Metadata field token costs (bytes serialized / avg tokens)
METADATA_COSTS = {
    "id": 40,                 # UUID
    "assigned_to": 15,        # Agent name
    "delegation_depth": 5,    # Integer
    "parent_task_id": 40,     # UUID  
    "parallel_group": 10,     # Group ID
    "dependencies": 45,       # Array of UUIDs (avg 1 dep)
    "skill": 12,              # Skill name
    "created_at": 25,         # ISO timestamp
    "started_at": 25,         # ISO timestamp
    "completed_at": 25,       # ISO timestamp
    "result": 50,             # Result string
}

# session.json PLAN-ONCE costs (from previous simulation)
SESSION_JSON_PLAN_COSTS = {
    "base_tokens": 350,       # Initial JSON structure
    "per_task_tokens": 80,    # Task entry in plan
    "file_io_tokens": 200,    # Read operations
}

# Baseline token costs
BASELINE_COSTS = {
    "task_add": 20,           # manage_todo_list add
    "task_update": 15,        # manage_todo_list status change
    "delegation_call": 100,   # runSubagent invocation
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TaskMetadata:
    """Rich metadata for a task."""
    id: str
    task: str
    status: str = "○"
    assigned_to: str = "AKIS"
    delegation_depth: int = 0
    parent_task_id: Optional[str] = None
    parallel_group: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    skill: Optional[str] = None
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    result: Optional[str] = None


@dataclass
class DelegationResult:
    """Result from a delegated task."""
    task_id: str
    agent: str
    status: str
    result: str
    artifacts: List[str]
    tokens_used: int
    execution_time: float
    subtasks_completed: int
    subtasks_total: int


@dataclass
class SessionMetrics:
    """Metrics for a single session."""
    session_id: str
    session_type: str
    scenario: str
    
    # Core metrics
    total_tasks: int = 0
    completed_tasks: int = 0
    delegated_tasks: int = 0
    
    # Token metrics
    base_tokens: int = 0
    metadata_tokens: int = 0
    session_json_tokens: int = 0
    total_tokens: int = 0
    
    # Delegation metrics
    max_delegation_depth: int = 0
    delegation_chain_visible: bool = False
    delegation_chains: int = 0
    
    # Traceability
    tasks_with_full_lineage: int = 0
    traceability_score: float = 0.0
    
    # Memory/Log
    memory_bytes: int = 0
    log_bytes: int = 0
    
    # Success
    success_rate: float = 0.0


@dataclass
class ScenarioResults:
    """Aggregated results for a scenario."""
    name: str
    total_sessions: int = 0
    
    # Averages
    avg_tokens: float = 0.0
    avg_metadata_overhead_pct: float = 0.0
    avg_traceability_score: float = 0.0
    avg_delegation_depth: float = 0.0
    avg_success_rate: float = 0.0
    avg_memory_bytes: float = 0.0
    avg_log_bytes: float = 0.0
    
    # Totals
    total_tokens: int = 0
    total_memory_bytes: int = 0
    
    # Rates
    delegation_visibility_rate: float = 0.0
    full_lineage_rate: float = 0.0
    
    # By session type
    by_session_type: Dict[str, Dict[str, float]] = field(default_factory=dict)


# ============================================================================
# Simulation Functions
# ============================================================================

def pick_weighted(distribution: Dict[str, float]) -> str:
    """Pick a value from weighted distribution."""
    items = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(items, weights=weights)[0]


def generate_uuid() -> str:
    """Generate a short UUID for task ID."""
    return str(uuid.uuid4())[:8]


def generate_tasks(session_type: str) -> List[TaskMetadata]:
    """Generate tasks for a session."""
    min_tasks, max_tasks = TASK_COUNTS[session_type]
    num_tasks = random.randint(min_tasks, max_tasks)
    
    tasks = []
    max_depth = DELEGATION_DEPTH[session_type]
    
    # Generate task tree with delegation structure
    root_task = TaskMetadata(
        id=generate_uuid(),
        task=f"Root task for {session_type} session",
        assigned_to="AKIS",
        delegation_depth=0,
        created_at=datetime.now().isoformat(),
    )
    tasks.append(root_task)
    
    # Add remaining tasks with delegation hierarchy
    for i in range(1, num_tasks):
        # Determine parent based on delegation pattern
        if max_depth > 0 and random.random() < 0.4:
            # This is a delegated subtask
            depth = min(random.randint(1, max_depth), len([t for t in tasks if t.delegation_depth < max_depth]))
            potential_parents = [t for t in tasks if t.delegation_depth == depth - 1]
            parent = random.choice(potential_parents) if potential_parents else root_task
            
            task = TaskMetadata(
                id=generate_uuid(),
                task=f"Subtask {i} (delegated)",
                assigned_to=random.choice(AGENTS[1:]),  # Not AKIS
                delegation_depth=parent.delegation_depth + 1,
                parent_task_id=parent.id,
                skill=random.choice(["frontend-react", "backend-api", "testing", "documentation"]),
                created_at=datetime.now().isoformat(),
            )
        else:
            # Direct task
            task = TaskMetadata(
                id=generate_uuid(),
                task=f"Task {i}",
                assigned_to="AKIS",
                delegation_depth=0,
                skill=random.choice(["frontend-react", "backend-api", "testing", None]),
                created_at=datetime.now().isoformat(),
            )
        
        # Add dependencies (25% chance)
        if tasks and random.random() < 0.25:
            dep_candidate = random.choice(tasks)
            task.dependencies = [dep_candidate.id]
        
        # Add parallel group (30% chance)
        if random.random() < 0.30:
            task.parallel_group = f"pg-{random.randint(1, 3)}"
        
        tasks.append(task)
    
    return tasks


def calculate_metadata_tokens(tasks: List[TaskMetadata], include_full: bool = True) -> int:
    """Calculate token cost for metadata."""
    total = 0
    
    for task in tasks:
        # Always include core fields
        total += METADATA_COSTS["id"]
        total += len(task.task) // 4  # Task description
        
        if include_full:
            total += METADATA_COSTS["assigned_to"]
            total += METADATA_COSTS["delegation_depth"]
            total += METADATA_COSTS["created_at"]
            
            if task.parent_task_id:
                total += METADATA_COSTS["parent_task_id"]
            if task.parallel_group:
                total += METADATA_COSTS["parallel_group"]
            if task.dependencies:
                total += METADATA_COSTS["dependencies"] * len(task.dependencies)
            if task.skill:
                total += METADATA_COSTS["skill"]
            if task.started_at:
                total += METADATA_COSTS["started_at"]
            if task.completed_at:
                total += METADATA_COSTS["completed_at"]
            if task.result:
                total += METADATA_COSTS["result"]
    
    return total


def calculate_session_json_tokens(num_tasks: int) -> int:
    """Calculate token cost for session.json PLAN-ONCE."""
    return (
        SESSION_JSON_PLAN_COSTS["base_tokens"] +
        SESSION_JSON_PLAN_COSTS["per_task_tokens"] * num_tasks +
        SESSION_JSON_PLAN_COSTS["file_io_tokens"]
    )


def simulate_session_baseline(session_id: str, session_type: str, tasks: List[TaskMetadata]) -> SessionMetrics:
    """Simulate session with NO metadata (baseline)."""
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        scenario="baseline_no_metadata",
        total_tasks=len(tasks),
    )
    
    # Base token cost for task management
    for task in tasks:
        metrics.base_tokens += BASELINE_COSTS["task_add"]
        metrics.base_tokens += BASELINE_COSTS["task_update"] * 2  # start + complete
        
        if task.delegation_depth > 0:
            metrics.base_tokens += BASELINE_COSTS["delegation_call"]
            metrics.delegated_tasks += 1
    
    metrics.total_tokens = metrics.base_tokens
    
    # Completion simulation
    success_rate = random.uniform(0.80, 0.95)
    metrics.completed_tasks = int(len(tasks) * success_rate)
    metrics.success_rate = metrics.completed_tasks / len(tasks)
    
    # No delegation visibility in baseline
    metrics.delegation_chain_visible = False
    metrics.traceability_score = 0.20  # Low baseline traceability
    
    # Minimal memory and log
    metrics.memory_bytes = len(tasks) * 50  # Basic task tracking
    metrics.log_bytes = len(tasks) * 30  # Minimal log
    
    return metrics


def simulate_session_metadata(session_id: str, session_type: str, tasks: List[TaskMetadata]) -> SessionMetrics:
    """Simulate session with METADATA ENHANCED."""
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        scenario="metadata_enhanced",
        total_tasks=len(tasks),
    )
    
    # Base token cost
    for task in tasks:
        metrics.base_tokens += BASELINE_COSTS["task_add"]
        metrics.base_tokens += BASELINE_COSTS["task_update"] * 2
        
        if task.delegation_depth > 0:
            metrics.base_tokens += BASELINE_COSTS["delegation_call"]
            metrics.delegated_tasks += 1
            metrics.max_delegation_depth = max(metrics.max_delegation_depth, task.delegation_depth)
    
    # Metadata token overhead
    metrics.metadata_tokens = calculate_metadata_tokens(tasks, include_full=True)
    metrics.total_tokens = metrics.base_tokens + metrics.metadata_tokens
    
    # Completion simulation (slightly better with metadata)
    success_rate = random.uniform(0.82, 0.96)
    metrics.completed_tasks = int(len(tasks) * success_rate)
    metrics.success_rate = metrics.completed_tasks / len(tasks)
    
    # Full delegation visibility
    metrics.delegation_chain_visible = True
    delegated = [t for t in tasks if t.delegation_depth > 0]
    metrics.delegation_chains = len(set(t.parent_task_id for t in delegated if t.parent_task_id))
    
    # High traceability with full lineage
    tasks_with_lineage = sum(1 for t in tasks if t.parent_task_id or t.delegation_depth == 0)
    metrics.tasks_with_full_lineage = tasks_with_lineage
    metrics.traceability_score = 0.90 + random.uniform(-0.05, 0.05)
    
    # Memory for in-memory state
    metrics.memory_bytes = len(tasks) * 150  # ~150 bytes per task with metadata
    metrics.log_bytes = len(tasks) * 100 + 500  # Richer log at END
    
    return metrics


def simulate_session_plan_json(session_id: str, session_type: str, tasks: List[TaskMetadata]) -> SessionMetrics:
    """Simulate session with session.json PLAN-ONCE."""
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        scenario="session_json_plan",
        total_tasks=len(tasks),
    )
    
    # Base token cost
    for task in tasks:
        metrics.base_tokens += BASELINE_COSTS["task_add"]
        metrics.base_tokens += BASELINE_COSTS["task_update"] * 2
        
        if task.delegation_depth > 0:
            metrics.base_tokens += BASELINE_COSTS["delegation_call"]
            metrics.delegated_tasks += 1
            metrics.max_delegation_depth = max(metrics.max_delegation_depth, task.delegation_depth)
    
    # session.json token overhead
    metrics.session_json_tokens = calculate_session_json_tokens(len(tasks))
    metrics.total_tokens = metrics.base_tokens + metrics.session_json_tokens
    
    # Completion simulation
    success_rate = random.uniform(0.81, 0.95)
    metrics.completed_tasks = int(len(tasks) * success_rate)
    metrics.success_rate = metrics.completed_tasks / len(tasks)
    
    # Partial delegation visibility (plan-level only)
    metrics.delegation_chain_visible = random.random() < 0.60  # 60% visibility
    metrics.traceability_score = 0.70 + random.uniform(-0.05, 0.05)
    
    # Higher memory for file + state
    metrics.memory_bytes = len(tasks) * 80 + 500  # File overhead
    metrics.log_bytes = len(tasks) * 80 + 800  # Plan in log
    
    return metrics


def simulate_session_hybrid(session_id: str, session_type: str, tasks: List[TaskMetadata]) -> SessionMetrics:
    """Simulate session with HYBRID (metadata + session.json)."""
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        scenario="hybrid",
        total_tasks=len(tasks),
    )
    
    # Base token cost
    for task in tasks:
        metrics.base_tokens += BASELINE_COSTS["task_add"]
        metrics.base_tokens += BASELINE_COSTS["task_update"] * 2
        
        if task.delegation_depth > 0:
            metrics.base_tokens += BASELINE_COSTS["delegation_call"]
            metrics.delegated_tasks += 1
            metrics.max_delegation_depth = max(metrics.max_delegation_depth, task.delegation_depth)
    
    # Both metadata AND session.json overhead
    metrics.metadata_tokens = calculate_metadata_tokens(tasks, include_full=True)
    metrics.session_json_tokens = calculate_session_json_tokens(len(tasks))
    metrics.total_tokens = metrics.base_tokens + metrics.metadata_tokens + metrics.session_json_tokens
    
    # Best completion rate
    success_rate = random.uniform(0.83, 0.97)
    metrics.completed_tasks = int(len(tasks) * success_rate)
    metrics.success_rate = metrics.completed_tasks / len(tasks)
    
    # Maximum delegation visibility
    metrics.delegation_chain_visible = True
    delegated = [t for t in tasks if t.delegation_depth > 0]
    metrics.delegation_chains = len(set(t.parent_task_id for t in delegated if t.parent_task_id))
    metrics.tasks_with_full_lineage = len(tasks)
    metrics.traceability_score = 0.95 + random.uniform(-0.03, 0.03)
    
    # Highest memory and log
    metrics.memory_bytes = len(tasks) * 200 + 600
    metrics.log_bytes = len(tasks) * 150 + 1000
    
    return metrics


def aggregate_results(sessions: List[SessionMetrics], name: str) -> ScenarioResults:
    """Aggregate metrics from all sessions."""
    n = len(sessions)
    results = ScenarioResults(name=name, total_sessions=n)
    
    # Calculate averages
    results.avg_tokens = sum(s.total_tokens for s in sessions) / n
    
    metadata_overheads = [
        s.metadata_tokens / s.total_tokens * 100 if s.total_tokens > 0 else 0
        for s in sessions
    ]
    results.avg_metadata_overhead_pct = sum(metadata_overheads) / n
    
    results.avg_traceability_score = sum(s.traceability_score for s in sessions) / n
    results.avg_delegation_depth = sum(s.max_delegation_depth for s in sessions) / n
    results.avg_success_rate = sum(s.success_rate for s in sessions) / n
    results.avg_memory_bytes = sum(s.memory_bytes for s in sessions) / n
    results.avg_log_bytes = sum(s.log_bytes for s in sessions) / n
    
    # Calculate totals
    results.total_tokens = sum(s.total_tokens for s in sessions)
    results.total_memory_bytes = sum(s.memory_bytes for s in sessions)
    
    # Calculate rates
    results.delegation_visibility_rate = sum(1 for s in sessions if s.delegation_chain_visible) / n
    results.full_lineage_rate = sum(s.tasks_with_full_lineage / s.total_tasks for s in sessions) / n
    
    # By session type
    for session_type in SESSION_MIX.keys():
        type_sessions = [s for s in sessions if s.session_type == session_type]
        if type_sessions:
            tn = len(type_sessions)
            results.by_session_type[session_type] = {
                "count": tn,
                "pct": tn / n,
                "avg_tokens": sum(s.total_tokens for s in type_sessions) / tn,
                "avg_traceability": sum(s.traceability_score for s in type_sessions) / tn,
                "success_rate": sum(s.success_rate for s in type_sessions) / tn,
            }
    
    return results


def run_simulation(n_sessions: int = 100000, seed: int = RANDOM_SEED) -> Dict[str, Any]:
    """Run full simulation across all scenarios."""
    
    print(f"\n{'='*80}")
    print(f"MANAGE_TODO_LIST METADATA ENHANCEMENT - 100K SIMULATION")
    print(f"{'='*80}")
    print(f"\nSimulating {n_sessions:,} sessions across 4 scenarios...")
    
    random.seed(seed)
    
    scenarios = {
        "baseline": [],
        "metadata": [],
        "session_json": [],
        "hybrid": [],
    }
    
    for i in range(n_sessions):
        session_id = generate_uuid()
        session_type = pick_weighted(SESSION_MIX)
        tasks = generate_tasks(session_type)
        
        # Run all scenarios with same tasks
        scenarios["baseline"].append(simulate_session_baseline(session_id, session_type, tasks))
        scenarios["metadata"].append(simulate_session_metadata(session_id, session_type, tasks))
        scenarios["session_json"].append(simulate_session_plan_json(session_id, session_type, tasks))
        scenarios["hybrid"].append(simulate_session_hybrid(session_id, session_type, tasks))
        
        if (i + 1) % 20000 == 0:
            print(f"   Completed {i + 1:,} sessions...")
    
    print(f"   ✓ All simulations complete")
    
    # Aggregate results
    results = {
        "baseline": aggregate_results(scenarios["baseline"], "baseline_no_metadata"),
        "metadata": aggregate_results(scenarios["metadata"], "metadata_enhanced"),
        "session_json": aggregate_results(scenarios["session_json"], "session_json_plan"),
        "hybrid": aggregate_results(scenarios["hybrid"], "hybrid"),
    }
    
    # Print report
    print_report(results, n_sessions)
    
    return {
        "simulation_info": {
            "n_sessions": n_sessions,
            "timestamp": datetime.now().isoformat(),
            "seed": seed,
        },
        "results": {k: asdict(v) for k, v in results.items()},
    }


def print_report(results: Dict[str, ScenarioResults], n_sessions: int):
    """Print formatted report."""
    
    baseline = results["baseline"]
    metadata = results["metadata"]
    session_json = results["session_json"]
    hybrid = results["hybrid"]
    
    print(f"\n{'='*80}")
    print(f"SIMULATION RESULTS - {n_sessions:,} SESSIONS")
    print(f"{'='*80}")
    
    # Token comparison
    print(f"\n📊 TOKEN EFFICIENCY")
    print(f"{'─'*70}")
    print(f"{'Scenario':<25} {'Avg Tokens':>12} {'Total (M)':>12} {'Overhead':>12}")
    print(f"{'─'*70}")
    
    for name, res in results.items():
        overhead = ((res.avg_tokens / baseline.avg_tokens) - 1) * 100 if baseline.avg_tokens > 0 else 0
        print(f"{name:<25} {res.avg_tokens:>12,.0f} {res.total_tokens/1e6:>12.1f}M {overhead:>+11.1f}%")
    
    # Traceability comparison
    print(f"\n📊 TRACEABILITY & VISIBILITY")
    print(f"{'─'*70}")
    print(f"{'Scenario':<25} {'Traceability':>12} {'Chain Vis.':>12} {'Lineage':>12}")
    print(f"{'─'*70}")
    
    for name, res in results.items():
        print(f"{name:<25} {res.avg_traceability_score:>12.1%} {res.delegation_visibility_rate:>12.1%} {res.full_lineage_rate:>12.1%}")
    
    # Delegation metrics
    print(f"\n📊 DELEGATION METRICS")
    print(f"{'─'*70}")
    print(f"{'Scenario':<25} {'Avg Depth':>12} {'Success':>12} {'Memory (B)':>12}")
    print(f"{'─'*70}")
    
    for name, res in results.items():
        print(f"{name:<25} {res.avg_delegation_depth:>12.2f} {res.avg_success_rate:>12.1%} {res.avg_memory_bytes:>12,.0f}")
    
    # Cost-benefit analysis
    print(f"\n{'='*80}")
    print(f"COST-BENEFIT ANALYSIS")
    print(f"{'='*80}")
    
    # Calculate ratios vs baseline
    print(f"\n📉 COSTS vs BASELINE")
    for name, res in results.items():
        if name != "baseline":
            token_overhead = ((res.avg_tokens / baseline.avg_tokens) - 1) * 100
            memory_overhead = ((res.avg_memory_bytes / baseline.avg_memory_bytes) - 1) * 100
            print(f"   {name:<20} Token: {token_overhead:>+6.1f}%  Memory: {memory_overhead:>+6.1f}%")
    
    print(f"\n📈 BENEFITS vs BASELINE")
    for name, res in results.items():
        if name != "baseline":
            trace_gain = ((res.avg_traceability_score / baseline.avg_traceability_score) - 1) * 100
            visibility_gain = res.delegation_visibility_rate - baseline.delegation_visibility_rate
            success_gain = ((res.avg_success_rate / baseline.avg_success_rate) - 1) * 100
            print(f"   {name:<20} Traceability: {trace_gain:>+6.0f}%  Visibility: {visibility_gain:>+6.1%}  Success: {success_gain:>+5.1f}%")
    
    # Cost-benefit ratios
    print(f"\n⚖️ COST-BENEFIT RATIOS")
    for name, res in results.items():
        if name != "baseline":
            cost = (res.avg_tokens / baseline.avg_tokens) - 1
            benefit = (res.avg_traceability_score / baseline.avg_traceability_score) - 1
            ratio = cost / benefit if benefit > 0 else float('inf')
            verdict = "✓ POSITIVE" if ratio < 1 else "◆ MARGINAL" if ratio < 2 else "✗ NEGATIVE"
            print(f"   {name:<20} Ratio: {ratio:.2f}:1  → {verdict}")
    
    # Recommendation
    print(f"\n{'='*80}")
    print(f"RECOMMENDATION")
    print(f"{'='*80}")
    
    # Find best option
    best_ratio = float('inf')
    best_option = "baseline"
    
    for name, res in results.items():
        if name != "baseline":
            cost = (res.avg_tokens / baseline.avg_tokens) - 1
            benefit = (res.avg_traceability_score / baseline.avg_traceability_score) - 1
            ratio = cost / benefit if benefit > 0 else float('inf')
            
            if ratio < best_ratio:
                best_ratio = ratio
                best_option = name
    
    print(f"\n   ✓ RECOMMENDED: {best_option.upper()}")
    print(f"   Cost-Benefit Ratio: {best_ratio:.2f}:1")
    print(f"   Token Overhead: {((results[best_option].avg_tokens / baseline.avg_tokens) - 1) * 100:+.1f}%")
    print(f"   Traceability Gain: {((results[best_option].avg_traceability_score / baseline.avg_traceability_score) - 1) * 100:+.0f}%")


def main():
    parser = argparse.ArgumentParser(
        description='manage_todo_list Metadata Enhancement Simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    
    parser.add_argument('--full', action='store_true',
                       help='Run full 100k simulation')
    parser.add_argument('--quick', action='store_true',
                       help='Run quick 10k simulation')
    parser.add_argument('--sessions', type=int, default=100000,
                       help='Number of sessions to simulate')
    parser.add_argument('--output', type=str,
                       help='Output results to JSON file')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED,
                       help='Random seed for reproducibility')
    
    args = parser.parse_args()
    
    # Determine session count
    if args.quick:
        n_sessions = 10000
    elif args.full:
        n_sessions = 100000
    else:
        n_sessions = args.sessions
    
    # Run simulation
    results = run_simulation(n_sessions, args.seed)
    
    # Save if requested
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n📄 Results saved to: {output_path}")
    
    print(f"\n✅ Simulation complete!")
    
    return results


if __name__ == '__main__':
    main()
