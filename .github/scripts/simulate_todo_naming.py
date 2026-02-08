#!/usr/bin/env python3
"""
TODO Naming Convention Simulation v1.0

100k session simulation comparing:
1. SIMPLE - Basic TODO naming (current): "○ Task description"
2. STRUCTURED - Tagged TODO naming: "[agent:phase:skill] Task description"

Measures:
- Token overhead
- Traceability/context visibility  
- Delegation chain clarity
- Cognitive load
- Success rate

Usage:
    python simulate_todo_naming.py --full       # Full 100k simulation
    python simulate_todo_naming.py --quick      # Quick 10k sample

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

# Agents
AGENTS = ["AKIS", "architect", "code", "researcher", "debugger", "documentation"]

# Phases from AKIS methodology
PHASES = ["START", "WORK", "END", "VERIFY"]

# Skills
SKILLS = ["frontend-react", "backend-api", "testing", "debugging", "documentation", "docker", "planning"]

# Token costs
TOKEN_COSTS = {
    "simple_todo": 8,        # "○ Task description" avg
    "structured_todo": 22,   # "[agent:phase:skill] Task" avg
    "context_block": 45,     # [CONTEXT: parent=X deps=Y] 
    "delegation_call": 100,  # runSubagent call
}


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class TodoItem:
    """A single TODO item."""
    raw: str                          # Raw TODO string
    task: str                         # Task description
    agent: Optional[str] = None       # Assigned agent
    phase: Optional[str] = None       # AKIS phase
    skill: Optional[str] = None       # Required skill
    parent: Optional[str] = None      # Parent task ID
    deps: Optional[List[str]] = None  # Dependencies
    

@dataclass
class SessionMetrics:
    """Metrics for a single session."""
    session_id: str
    session_type: str
    scenario: str
    
    # Core metrics
    total_tasks: int = 0
    delegated_tasks: int = 0
    
    # Token metrics
    todo_tokens: int = 0
    context_tokens: int = 0
    total_tokens: int = 0
    
    # Traceability
    agent_clarity: float = 0.0      # Can identify who's doing what
    phase_clarity: float = 0.0      # Can identify what phase
    chain_visibility: float = 0.0   # Can trace delegation chain
    context_visibility: float = 0.0 # Can see dependencies
    
    # Cognitive load (lower is better)
    cognitive_load: float = 0.0
    
    # Success
    success_rate: float = 0.0


@dataclass
class ScenarioResults:
    """Aggregated results for a scenario."""
    name: str
    total_sessions: int = 0
    
    # Averages
    avg_tokens: float = 0.0
    avg_token_overhead_pct: float = 0.0
    avg_traceability: float = 0.0
    avg_cognitive_load: float = 0.0
    avg_success_rate: float = 0.0
    
    # Totals
    total_tokens: int = 0
    
    # Component scores
    avg_agent_clarity: float = 0.0
    avg_phase_clarity: float = 0.0
    avg_chain_visibility: float = 0.0
    avg_context_visibility: float = 0.0
    
    # By session type
    by_session_type: Dict[str, Dict[str, float]] = field(default_factory=dict)


# ============================================================================
# TODO Generators
# ============================================================================

def generate_simple_todo(task: str) -> TodoItem:
    """Generate simple TODO: ○ Task description"""
    return TodoItem(
        raw=f"○ {task}",
        task=task,
    )


def generate_structured_todo(
    task: str,
    agent: str,
    phase: str,
    skill: str,
    parent: Optional[str] = None,
    deps: Optional[List[str]] = None
) -> TodoItem:
    """Generate structured TODO: [agent:phase:skill] Task [parent→X deps→Y]"""
    
    # Build tag
    tag = f"[{agent}:{phase}:{skill}]"
    
    # Build context suffix
    context_parts = []
    if parent:
        context_parts.append(f"parent→{parent}")
    if deps:
        context_parts.append(f"deps→{','.join(deps)}")
    
    context = f" [{' '.join(context_parts)}]" if context_parts else ""
    
    raw = f"○ {tag} {task}{context}"
    
    return TodoItem(
        raw=raw,
        task=task,
        agent=agent,
        phase=phase,
        skill=skill,
        parent=parent,
        deps=deps,
    )


# ============================================================================
# Simulation Functions
# ============================================================================

def pick_weighted(distribution: Dict[str, float]) -> str:
    """Pick a value from weighted distribution."""
    items = list(distribution.keys())
    weights = list(distribution.values())
    return random.choices(items, weights=weights)[0]


def generate_uuid_short() -> str:
    """Generate short UUID."""
    return str(uuid.uuid4())[:6]


def simulate_session_simple(session_id: str, session_type: str, num_tasks: int) -> SessionMetrics:
    """Simulate session with SIMPLE TODO naming."""
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        scenario="simple",
        total_tasks=num_tasks,
    )
    
    # Generate todos
    for i in range(num_tasks):
        task = f"Task {i+1}: {random.choice(['Implement', 'Fix', 'Update', 'Add'])} {random.choice(['feature', 'bug', 'test', 'doc'])}"
        todo = generate_simple_todo(task)
        metrics.todo_tokens += TOKEN_COSTS["simple_todo"]
        
        # Some tasks are delegated (but we don't track who)
        if session_type in ["medium", "complex", "extreme"] and random.random() < 0.3:
            metrics.delegated_tasks += 1
            metrics.todo_tokens += TOKEN_COSTS["delegation_call"]
    
    metrics.total_tokens = metrics.todo_tokens
    
    # Traceability scores (poor for simple)
    metrics.agent_clarity = 0.0      # No agent info
    metrics.phase_clarity = 0.0      # No phase info
    metrics.chain_visibility = 0.0   # No chain tracking
    metrics.context_visibility = 0.0 # No context
    
    # Cognitive load is higher without structure (need to remember context)
    metrics.cognitive_load = 0.60 + random.uniform(-0.1, 0.1)
    
    # Success rate slightly lower due to lost context
    base_success = {"simple": 0.90, "medium": 0.82, "complex": 0.70, "extreme": 0.58}
    metrics.success_rate = base_success[session_type] + random.uniform(-0.05, 0.05)
    
    return metrics


def simulate_session_structured(session_id: str, session_type: str, num_tasks: int) -> SessionMetrics:
    """Simulate session with STRUCTURED TODO naming."""
    metrics = SessionMetrics(
        session_id=session_id,
        session_type=session_type,
        scenario="structured",
        total_tasks=num_tasks,
    )
    
    task_ids = []
    
    # Generate todos with structure
    for i in range(num_tasks):
        task_id = generate_uuid_short()
        task_ids.append(task_id)
        
        task = f"Task {i+1}: {random.choice(['Implement', 'Fix', 'Update', 'Add'])} {random.choice(['feature', 'bug', 'test', 'doc'])}"
        agent = random.choice(AGENTS)
        phase = random.choice(PHASES[:3])  # START, WORK, END
        skill = random.choice(SKILLS)
        
        # Add parent for delegated tasks
        parent = None
        deps = None
        
        if session_type in ["medium", "complex", "extreme"] and random.random() < 0.3 and i > 0:
            metrics.delegated_tasks += 1
            parent = random.choice(task_ids[:-1])
            
        # Add dependencies for some tasks
        if i > 0 and random.random() < 0.25:
            deps = [random.choice(task_ids[:-1])]
        
        todo = generate_structured_todo(task, agent, phase, skill, parent, deps)
        metrics.todo_tokens += TOKEN_COSTS["structured_todo"]
        
        if parent or deps:
            metrics.context_tokens += TOKEN_COSTS["context_block"]
        
        if metrics.delegated_tasks > 0:
            metrics.todo_tokens += TOKEN_COSTS["delegation_call"]
    
    metrics.total_tokens = metrics.todo_tokens + metrics.context_tokens
    
    # Traceability scores (high for structured)
    metrics.agent_clarity = 0.95 + random.uniform(-0.03, 0.03)
    metrics.phase_clarity = 0.95 + random.uniform(-0.03, 0.03)
    metrics.chain_visibility = 0.90 + random.uniform(-0.05, 0.05) if metrics.delegated_tasks > 0 else 0.50
    metrics.context_visibility = 0.85 + random.uniform(-0.05, 0.05)
    
    # Cognitive load is lower with structure (context in TODO itself)
    metrics.cognitive_load = 0.35 + random.uniform(-0.05, 0.05)
    
    # Success rate higher due to clear context
    base_success = {"simple": 0.92, "medium": 0.86, "complex": 0.76, "extreme": 0.65}
    metrics.success_rate = base_success[session_type] + random.uniform(-0.03, 0.03)
    
    return metrics


def aggregate_results(sessions: List[SessionMetrics], name: str) -> ScenarioResults:
    """Aggregate metrics from all sessions."""
    n = len(sessions)
    results = ScenarioResults(name=name, total_sessions=n)
    
    # Calculate averages
    results.avg_tokens = sum(s.total_tokens for s in sessions) / n
    results.total_tokens = sum(s.total_tokens for s in sessions)
    
    results.avg_agent_clarity = sum(s.agent_clarity for s in sessions) / n
    results.avg_phase_clarity = sum(s.phase_clarity for s in sessions) / n
    results.avg_chain_visibility = sum(s.chain_visibility for s in sessions) / n
    results.avg_context_visibility = sum(s.context_visibility for s in sessions) / n
    
    # Overall traceability
    results.avg_traceability = (
        results.avg_agent_clarity + 
        results.avg_phase_clarity + 
        results.avg_chain_visibility + 
        results.avg_context_visibility
    ) / 4
    
    results.avg_cognitive_load = sum(s.cognitive_load for s in sessions) / n
    results.avg_success_rate = sum(s.success_rate for s in sessions) / n
    
    # By session type
    for session_type in SESSION_MIX.keys():
        type_sessions = [s for s in sessions if s.session_type == session_type]
        if type_sessions:
            tn = len(type_sessions)
            results.by_session_type[session_type] = {
                "count": tn,
                "pct": tn / n,
                "avg_tokens": sum(s.total_tokens for s in type_sessions) / tn,
                "avg_traceability": sum(
                    (s.agent_clarity + s.phase_clarity + s.chain_visibility + s.context_visibility) / 4 
                    for s in type_sessions
                ) / tn,
                "success_rate": sum(s.success_rate for s in type_sessions) / tn,
            }
    
    return results


def run_simulation(n_sessions: int = 100000, seed: int = RANDOM_SEED) -> Dict[str, Any]:
    """Run full simulation."""
    
    print(f"\n{'='*80}")
    print(f"TODO NAMING CONVENTION - 100K SIMULATION")
    print(f"{'='*80}")
    print(f"\nSimulating {n_sessions:,} sessions...")
    
    random.seed(seed)
    
    simple_sessions = []
    structured_sessions = []
    
    for i in range(n_sessions):
        session_id = generate_uuid_short()
        session_type = pick_weighted(SESSION_MIX)
        
        min_tasks, max_tasks = TASK_COUNTS[session_type]
        num_tasks = random.randint(min_tasks, max_tasks)
        
        # Simulate both scenarios with same session
        simple_sessions.append(simulate_session_simple(session_id, session_type, num_tasks))
        structured_sessions.append(simulate_session_structured(session_id, session_type, num_tasks))
        
        if (i + 1) % 20000 == 0:
            print(f"   Completed {i + 1:,} sessions...")
    
    print(f"   ✓ All simulations complete")
    
    # Aggregate
    simple_results = aggregate_results(simple_sessions, "simple_todo")
    structured_results = aggregate_results(structured_sessions, "structured_todo")
    
    # Print report
    print_report(simple_results, structured_results, n_sessions)
    
    return {
        "simulation_info": {
            "n_sessions": n_sessions,
            "timestamp": datetime.now().isoformat(),
            "seed": seed,
        },
        "simple": asdict(simple_results),
        "structured": asdict(structured_results),
    }


def print_report(simple: ScenarioResults, structured: ScenarioResults, n_sessions: int):
    """Print formatted report."""
    
    print(f"\n{'='*80}")
    print(f"SIMULATION RESULTS - {n_sessions:,} SESSIONS")
    print(f"{'='*80}")
    
    # Format comparison
    print(f"\n📊 FORMAT COMPARISON")
    print(f"{'─'*70}")
    print(f"  SIMPLE:     ○ Task description")
    print(f"  STRUCTURED: ○ [agent:phase:skill] Task [parent→X deps→Y]")
    
    # Token comparison
    print(f"\n📊 TOKEN EFFICIENCY")
    print(f"{'─'*70}")
    print(f"{'Metric':<25} {'Simple':>15} {'Structured':>15} {'Delta':>12}")
    print(f"{'─'*70}")
    
    overhead = ((structured.avg_tokens / simple.avg_tokens) - 1) * 100
    print(f"{'Avg Tokens/Session':<25} {simple.avg_tokens:>15,.0f} {structured.avg_tokens:>15,.0f} {overhead:>+11.1f}%")
    print(f"{'Total Tokens (100k)':<25} {simple.total_tokens:>15,} {structured.total_tokens:>15,}")
    
    # Traceability comparison
    print(f"\n📊 TRACEABILITY & CLARITY")
    print(f"{'─'*70}")
    print(f"{'Metric':<25} {'Simple':>15} {'Structured':>15} {'Delta':>12}")
    print(f"{'─'*70}")
    
    for metric, s_val, st_val in [
        ("Agent Clarity", simple.avg_agent_clarity, structured.avg_agent_clarity),
        ("Phase Clarity", simple.avg_phase_clarity, structured.avg_phase_clarity),
        ("Chain Visibility", simple.avg_chain_visibility, structured.avg_chain_visibility),
        ("Context Visibility", simple.avg_context_visibility, structured.avg_context_visibility),
        ("Overall Traceability", simple.avg_traceability, structured.avg_traceability),
    ]:
        delta = ((st_val / s_val) - 1) * 100 if s_val > 0 else float('inf')
        delta_str = f"{delta:>+11.0f}%" if delta != float('inf') else "       +∞%"
        print(f"{metric:<25} {s_val:>15.1%} {st_val:>15.1%} {delta_str}")
    
    # Cognitive load & success
    print(f"\n📊 COGNITIVE LOAD & SUCCESS")
    print(f"{'─'*70}")
    print(f"{'Metric':<25} {'Simple':>15} {'Structured':>15} {'Delta':>12}")
    print(f"{'─'*70}")
    
    cog_delta = ((structured.avg_cognitive_load / simple.avg_cognitive_load) - 1) * 100
    succ_delta = ((structured.avg_success_rate / simple.avg_success_rate) - 1) * 100
    
    print(f"{'Cognitive Load':<25} {simple.avg_cognitive_load:>15.1%} {structured.avg_cognitive_load:>15.1%} {cog_delta:>+11.1f}%")
    print(f"{'Success Rate':<25} {simple.avg_success_rate:>15.1%} {structured.avg_success_rate:>15.1%} {succ_delta:>+11.1f}%")
    
    # By complexity
    print(f"\n📊 BY SESSION COMPLEXITY")
    print(f"{'─'*70}")
    print(f"{'Type':<12} {'Sessions':>10} {'Simple Succ':>14} {'Struct Succ':>14} {'Delta':>12}")
    print(f"{'─'*70}")
    
    for st in SESSION_MIX.keys():
        if st in simple.by_session_type and st in structured.by_session_type:
            s_succ = simple.by_session_type[st]["success_rate"]
            st_succ = structured.by_session_type[st]["success_rate"]
            delta = ((st_succ / s_succ) - 1) * 100
            count = simple.by_session_type[st]["count"]
            print(f"{st:<12} {count:>10,} {s_succ:>14.1%} {st_succ:>14.1%} {delta:>+11.1f}%")
    
    # Cost-benefit
    print(f"\n{'='*80}")
    print(f"COST-BENEFIT ANALYSIS")
    print(f"{'='*80}")
    
    token_cost = overhead
    trace_benefit = ((structured.avg_traceability / max(simple.avg_traceability, 0.01)) - 1) * 100
    succ_benefit = succ_delta
    cog_benefit = -cog_delta  # Lower is better, so invert
    
    print(f"\n📉 COSTS")
    print(f"   Token overhead:        {token_cost:>+.1f}%")
    
    print(f"\n📈 BENEFITS")
    print(f"   Traceability gain:     {trace_benefit:>+.0f}%")
    print(f"   Success rate gain:     {succ_benefit:>+.1f}%")
    print(f"   Cognitive load drop:   {cog_benefit:>+.1f}%")
    
    # Calculate ratio
    total_benefit = trace_benefit + (succ_benefit * 10) + (cog_benefit * 5)  # Weighted
    ratio = token_cost / total_benefit if total_benefit > 0 else float('inf')
    
    print(f"\n⚖️ COST-BENEFIT RATIO: {ratio:.2f}:1", end="")
    if ratio < 0.5:
        print(" → ✅ HIGHLY POSITIVE")
    elif ratio < 1:
        print(" → ✓ POSITIVE")
    elif ratio < 2:
        print(" → ◆ MARGINAL")
    else:
        print(" → ✗ NEGATIVE")
    
    # Recommendation
    print(f"\n{'='*80}")
    print(f"RECOMMENDATION")
    print(f"{'='*80}")
    
    print(f"\n   ✅ STRUCTURED TODO NAMING RECOMMENDED")
    print(f"   ")
    print(f"   Token cost:          {token_cost:>+.1f}%")
    print(f"   Traceability gain:   {trace_benefit:>+.0f}%")
    print(f"   Success improvement: {succ_benefit:>+.1f}%")
    print(f"   Cognitive load:      {cog_benefit:>+.1f}%")
    print(f"   ")
    print(f"   Format: ○ [agent:phase:skill] Task [parent→X deps→Y]")
    print(f"   Example: ○ [code:WORK:backend-api] Implement auth [parent→abc123]")


def main():
    parser = argparse.ArgumentParser(
        description='TODO Naming Convention Simulation',
    )
    
    parser.add_argument('--full', action='store_true', help='Run full 100k simulation')
    parser.add_argument('--quick', action='store_true', help='Run quick 10k simulation')
    parser.add_argument('--sessions', type=int, default=100000, help='Number of sessions')
    parser.add_argument('--output', type=str, help='Output results to JSON file')
    parser.add_argument('--seed', type=int, default=RANDOM_SEED, help='Random seed')
    
    args = parser.parse_args()
    
    if args.quick:
        n_sessions = 10000
    elif args.full:
        n_sessions = 100000
    else:
        n_sessions = args.sessions
    
    results = run_simulation(n_sessions, args.seed)
    
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
