#!/usr/bin/env python3
"""
AKIS v8.0 Software Development Session Simulation (100k Sessions)

Simulates realistic developer sessions based on industry patterns:
- Martin Fowler's Continuous Integration
- Conventional Commits
- GitHub Flow
- Trunk-Based Development
- Google Engineering Practices
- 12-Factor App
- TDD (Test-Driven Development)
- Agile Principles

Session Types:
- Feature Development (35%)
- Bug Fix (25%)
- Code Review (15%)
- Refactoring (10%)
- Testing (10%)
- Documentation (5%)
"""

import json
import random
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
import statistics


@dataclass
class SessionConfig:
    """Configuration for session simulation."""
    total_sessions: int = 100_000
    random_seed: int = 42
    output_path: str = "log/akis_sw_dev_simulation_100k.json"


@dataclass
class GateCompliance:
    """Tracks compliance for each AKIS gate."""
    g0_knowledge: bool = False  # Load knowledge graph
    g1_todo: bool = False       # Use TODO tracking
    g2_skill: bool = False      # Load skill before edit
    g3_start: bool = False      # Complete START phase
    g4_end: bool = False        # Complete END phase
    g5_verify: bool = False     # Verify after edit
    g6_single: bool = False     # One task at a time
    g7_parallel: bool = False   # Use parallel execution
    
    def compliance_rate(self) -> float:
        """Return rate of gates passed (0.0 to 1.0)."""
        gates = [self.g0_knowledge, self.g1_todo, self.g2_skill, self.g3_start,
                 self.g4_end, self.g5_verify, self.g6_single, self.g7_parallel]
        return sum(gates) / len(gates)
    
    def gates_passed(self) -> int:
        """Return count of gates passed."""
        gates = [self.g0_knowledge, self.g1_todo, self.g2_skill, self.g3_start,
                 self.g4_end, self.g5_verify, self.g6_single, self.g7_parallel]
        return sum(gates)


@dataclass
class SessionMetrics:
    """Metrics for a single session."""
    session_type: str
    complexity: str  # simple, medium, complex
    duration_minutes: float
    tokens_used: int
    api_calls: int
    files_modified: int
    commits: int
    success: bool
    gates: GateCompliance = field(default_factory=GateCompliance)
    skill_loads: list = field(default_factory=list)
    commit_types: list = field(default_factory=list)  # Conventional Commits
    parallel_tasks: int = 0
    delegation_used: bool = False
    workflow_log_created: bool = False


# ============================================================
# Session Type Definitions (Based on Industry Patterns)
# ============================================================

SESSION_TYPES = {
    "feature_development": {
        "weight": 0.35,  # 35% of sessions
        "duration_range": (30, 90),  # minutes
        "files_range": (4, 12),
        "commits_range": (3, 8),
        "complexity_dist": {"simple": 0.15, "medium": 0.55, "complex": 0.30},
        "skills": ["frontend-react", "backend-api", "testing"],
        "commit_types": ["feat", "test", "refactor"],
        "parallel_opportunity": 0.7,  # High - code + tests can parallel
        "description": "GitHub Flow: Create branch → commits → PR → merge"
    },
    "bug_fix": {
        "weight": 0.25,
        "duration_range": (15, 60),
        "files_range": (1, 4),
        "commits_range": (1, 3),
        "complexity_dist": {"simple": 0.40, "medium": 0.45, "complex": 0.15},
        "skills": ["debugging", "backend-api", "frontend-react", "testing"],
        "commit_types": ["fix", "test"],
        "parallel_opportunity": 0.4,  # Medium - diagnosis is sequential
        "description": "CI: Fix broken builds immediately"
    },
    "code_review": {
        "weight": 0.15,
        "duration_range": (10, 40),
        "files_range": (0, 0),  # Read-only
        "commits_range": (0, 0),
        "complexity_dist": {"simple": 0.50, "medium": 0.40, "complex": 0.10},
        "skills": ["security", "documentation"],
        "commit_types": [],
        "parallel_opportunity": 0.2,  # Low - sequential analysis
        "description": "Google: Speed of code reviews, fast feedback"
    },
    "refactoring": {
        "weight": 0.10,
        "duration_range": (30, 75),
        "files_range": (5, 15),
        "commits_range": (4, 12),
        "complexity_dist": {"simple": 0.10, "medium": 0.40, "complex": 0.50},
        "skills": ["backend-api", "frontend-react", "testing"],
        "commit_types": ["refactor", "test", "style"],
        "parallel_opportunity": 0.5,  # Medium - tests can run parallel
        "description": "TDD: Red-Green-Refactor, small incremental changes"
    },
    "testing": {
        "weight": 0.10,
        "duration_range": (20, 50),
        "files_range": (2, 6),
        "commits_range": (2, 5),
        "complexity_dist": {"simple": 0.30, "medium": 0.50, "complex": 0.20},
        "skills": ["testing", "backend-api", "frontend-react"],
        "commit_types": ["test", "fix"],
        "parallel_opportunity": 0.6,  # High - tests are independent
        "description": "TDD: Write test list first, Red-Green-Refactor"
    },
    "documentation": {
        "weight": 0.05,
        "duration_range": (10, 30),
        "files_range": (1, 3),
        "commits_range": (1, 2),
        "complexity_dist": {"simple": 0.60, "medium": 0.35, "complex": 0.05},
        "skills": ["documentation"],
        "commit_types": ["docs"],
        "parallel_opportunity": 0.3,  # Low - mostly sequential
        "description": "12-Factor: Declarative formats, documentation as code"
    }
}

# Conventional Commits distribution (based on industry data)
COMMIT_TYPE_BASE_RATES = {
    "feat": 0.35,
    "fix": 0.25,
    "refactor": 0.12,
    "test": 0.10,
    "docs": 0.08,
    "chore": 0.05,
    "style": 0.03,
    "perf": 0.02
}


def select_session_type() -> str:
    """Select session type based on industry distribution."""
    types = list(SESSION_TYPES.keys())
    weights = [SESSION_TYPES[t]["weight"] for t in types]
    return random.choices(types, weights=weights, k=1)[0]


def select_complexity(session_type: str) -> str:
    """Select complexity based on session type distribution."""
    dist = SESSION_TYPES[session_type]["complexity_dist"]
    return random.choices(
        ["simple", "medium", "complex"],
        weights=[dist["simple"], dist["medium"], dist["complex"]],
        k=1
    )[0]


def generate_commit_types(session_type: str, num_commits: int) -> list:
    """Generate commit types following Conventional Commits."""
    session_config = SESSION_TYPES[session_type]
    preferred_types = session_config["commit_types"]
    
    if not preferred_types or num_commits == 0:
        return []
    
    # Bias towards session-appropriate commit types
    commit_types = []
    for _ in range(num_commits):
        if random.random() < 0.8:  # 80% chance of session-appropriate type
            commit_types.append(random.choice(preferred_types))
        else:  # 20% chance of any type
            commit_types.append(random.choices(
                list(COMMIT_TYPE_BASE_RATES.keys()),
                weights=list(COMMIT_TYPE_BASE_RATES.values()),
                k=1
            )[0])
    
    return commit_types


# ============================================================
# AKIS Gate Simulation (Based on Industry Patterns)
# ============================================================

class AKISGateSimulator:
    """Simulates AKIS gate compliance with industry pattern alignment."""
    
    def __init__(self, optimization_level: str = "baseline"):
        """
        optimization_level:
            - "baseline": Current AKIS v7.4 behavior
            - "optimized": AKIS v8.0 with industry pattern improvements
        """
        self.optimization_level = optimization_level
        
        # Baseline compliance rates (from previous analysis)
        self.baseline_rates = {
            "g0_knowledge": 0.72,   # Knowledge loading
            "g1_todo": 0.90,        # TODO tracking
            "g2_skill": 0.69,       # Skill before edit (30.8% violation)
            "g3_start": 0.92,       # START phase
            "g4_end": 0.78,         # END phase (21.8% violation)
            "g5_verify": 0.82,      # Verify after edit (18% violation)
            "g6_single": 1.00,      # Single task
            "g7_parallel": 0.19,    # Parallel execution (low)
        }
        
        # Optimized rates with industry pattern improvements
        self.optimized_rates = {
            "g0_knowledge": 0.98,   # GitHub Flow: Context first
            "g1_todo": 0.96,        # Conventional Commits: Structured
            "g2_skill": 0.95,       # TDD: Test/skill first
            "g3_start": 0.97,       # GitHub Flow: Branch creation
            "g4_end": 0.94,         # CI: Proper commit/merge
            "g5_verify": 0.96,      # CI: Self-testing code
            "g6_single": 1.00,      # Trunk-Based: Short branches
            "g7_parallel": 0.60,    # Agile: Parallel pairs
        }
    
    def simulate_gates(self, session: SessionMetrics) -> GateCompliance:
        """Simulate gate compliance for a session."""
        rates = self.optimized_rates if self.optimization_level == "optimized" else self.baseline_rates
        
        gates = GateCompliance()
        
        # G0: Knowledge loading - higher for complex sessions
        g0_boost = 0.05 if session.complexity == "complex" else 0
        gates.g0_knowledge = random.random() < (rates["g0_knowledge"] + g0_boost)
        
        # G1: TODO tracking - higher when more files
        g1_boost = 0.03 if session.files_modified > 3 else 0
        gates.g1_todo = random.random() < (rates["g1_todo"] + g1_boost)
        
        # G2: Skill loading - critical for multi-file edits
        g2_penalty = -0.05 if session.files_modified > 5 else 0  # More files = more likely to forget
        if self.optimization_level == "optimized":
            g2_penalty = 0  # Optimized: Auto-detect skill from file type
        gates.g2_skill = random.random() < (rates["g2_skill"] + g2_penalty)
        
        # G3: START phase - tied to session initialization
        gates.g3_start = random.random() < rates["g3_start"]
        
        # G4: END phase - higher for longer sessions (>15 min)
        g4_boost = 0.10 if session.duration_minutes > 15 else -0.05
        gates.g4_end = random.random() < max(0.5, min(1.0, rates["g4_end"] + g4_boost))
        
        # G5: Verify after edit - per CI "self-testing code"
        # Optimized version uses continuous verification
        gates.g5_verify = random.random() < rates["g5_verify"]
        
        # G6: Single task - always 100%
        gates.g6_single = True
        
        # G7: Parallel execution - based on session type opportunity
        session_config = SESSION_TYPES[session.session_type]
        parallel_opportunity = session_config["parallel_opportunity"]
        
        if self.optimization_level == "optimized":
            # Optimized: Use parallel when opportunity exists
            gates.g7_parallel = random.random() < (rates["g7_parallel"] * parallel_opportunity / 0.5)
        else:
            # Baseline: Low parallel rate regardless of opportunity
            gates.g7_parallel = random.random() < rates["g7_parallel"]
        
        return gates


# ============================================================
# Session Generation
# ============================================================

def generate_session(
    session_id: int,
    gate_simulator: AKISGateSimulator
) -> SessionMetrics:
    """Generate a single session with industry-aligned patterns."""
    
    # Select session type and complexity
    session_type = select_session_type()
    complexity = select_complexity(session_type)
    config = SESSION_TYPES[session_type]
    
    # Generate metrics based on session type
    duration = random.uniform(*config["duration_range"])
    files = random.randint(*config["files_range"])
    commits = random.randint(*config["commits_range"])
    commit_types = generate_commit_types(session_type, commits)
    
    # Token usage calculation
    # Base tokens + file complexity + duration factor
    base_tokens = {
        "simple": random.randint(4000, 10000),
        "medium": random.randint(10000, 20000),
        "complex": random.randint(18000, 35000)
    }[complexity]
    
    file_factor = files * random.randint(500, 1500)
    tokens = base_tokens + file_factor
    
    # API calls - proportional to complexity and files
    api_calls = {
        "simple": random.randint(8, 20),
        "medium": random.randint(18, 45),
        "complex": random.randint(40, 80)
    }[complexity]
    
    # Determine skills used
    skills = random.sample(
        config["skills"],
        k=min(len(config["skills"]), random.randint(1, 3))
    )
    
    # Create session
    session = SessionMetrics(
        session_type=session_type,
        complexity=complexity,
        duration_minutes=duration,
        tokens_used=tokens,
        api_calls=api_calls,
        files_modified=files,
        commits=commits,
        success=True,  # Will be determined by gates
        skill_loads=skills,
        commit_types=commit_types,
        parallel_tasks=0,
        delegation_used=files >= 3,
        workflow_log_created=duration > 15
    )
    
    # Simulate gate compliance
    session.gates = gate_simulator.simulate_gates(session)
    
    # Determine success based on gates and complexity
    gate_compliance = session.gates.compliance_rate()
    
    # Success factors based on industry patterns
    if complexity == "simple":
        success_threshold = 0.60
    elif complexity == "medium":
        success_threshold = 0.70
    else:  # complex
        success_threshold = 0.80
    
    # G5 (verify) is critical - per CI "fix broken builds immediately"
    if not session.gates.g5_verify:
        success_threshold += 0.15  # Harder to succeed without verification
    
    # G2 (skill) impacts quality - per TDD "test/skill first"
    if not session.gates.g2_skill:
        success_threshold += 0.10
    
    session.success = gate_compliance >= success_threshold
    
    # Parallel tasks if G7 passed
    if session.gates.g7_parallel and files >= 2:
        session.parallel_tasks = random.randint(2, 4)
    
    return session


# ============================================================
# Simulation Engine
# ============================================================

def run_simulation(config: SessionConfig, optimization_level: str = "baseline") -> dict:
    """Run the full 100k session simulation."""
    random.seed(config.random_seed)
    
    gate_simulator = AKISGateSimulator(optimization_level)
    
    sessions = []
    gate_totals = {f"g{i}": 0 for i in range(8)}
    
    print(f"Running {config.total_sessions:,} session simulation ({optimization_level})...")
    
    for i in range(config.total_sessions):
        session = generate_session(i, gate_simulator)
        sessions.append(session)
        
        # Track gate compliance
        if session.gates.g0_knowledge: gate_totals["g0"] += 1
        if session.gates.g1_todo: gate_totals["g1"] += 1
        if session.gates.g2_skill: gate_totals["g2"] += 1
        if session.gates.g3_start: gate_totals["g3"] += 1
        if session.gates.g4_end: gate_totals["g4"] += 1
        if session.gates.g5_verify: gate_totals["g5"] += 1
        if session.gates.g6_single: gate_totals["g6"] += 1
        if session.gates.g7_parallel: gate_totals["g7"] += 1
        
        if (i + 1) % 10000 == 0:
            print(f"  {i + 1:,} sessions processed...")
    
    # Calculate aggregated metrics
    total = config.total_sessions
    
    # Per-session-type breakdown
    type_breakdown = {}
    for stype in SESSION_TYPES:
        type_sessions = [s for s in sessions if s.session_type == stype]
        if type_sessions:
            type_breakdown[stype] = {
                "count": len(type_sessions),
                "percentage": len(type_sessions) / total * 100,
                "success_rate": sum(s.success for s in type_sessions) / len(type_sessions) * 100,
                "avg_duration": statistics.mean(s.duration_minutes for s in type_sessions),
                "avg_tokens": statistics.mean(s.tokens_used for s in type_sessions),
                "avg_files": statistics.mean(s.files_modified for s in type_sessions),
                "avg_commits": statistics.mean(s.commits for s in type_sessions),
                "gate_compliance": statistics.mean(s.gates.compliance_rate() for s in type_sessions) * 100,
                "parallel_rate": sum(s.gates.g7_parallel for s in type_sessions) / len(type_sessions) * 100,
            }
    
    # Gate compliance rates
    gate_compliance = {
        f"G{i}": gate_totals[f"g{i}"] / total * 100
        for i in range(8)
    }
    
    # Conventional Commits breakdown
    all_commits = [ct for s in sessions for ct in s.commit_types]
    commit_type_counts = {}
    for ct in set(all_commits):
        commit_type_counts[ct] = all_commits.count(ct)
    
    total_commits = len(all_commits)
    commit_type_rates = {
        ct: count / total_commits * 100 if total_commits > 0 else 0
        for ct, count in commit_type_counts.items()
    }
    
    # Build results
    results = {
        "meta": {
            "simulation_date": datetime.now().isoformat(),
            "total_sessions": total,
            "optimization_level": optimization_level,
            "random_seed": config.random_seed,
            "industry_patterns": [
                "Martin Fowler - Continuous Integration",
                "Conventional Commits",
                "GitHub Flow",
                "Trunk-Based Development",
                "Google Engineering Practices",
                "12-Factor App",
                "TDD (Test-Driven Development)",
                "Agile Principles"
            ]
        },
        "summary": {
            "success_rate": sum(s.success for s in sessions) / total * 100,
            "avg_duration_minutes": statistics.mean(s.duration_minutes for s in sessions),
            "avg_tokens": statistics.mean(s.tokens_used for s in sessions),
            "avg_api_calls": statistics.mean(s.api_calls for s in sessions),
            "avg_files_modified": statistics.mean(s.files_modified for s in sessions),
            "avg_commits": statistics.mean(s.commits for s in sessions),
            "avg_gate_compliance": statistics.mean(s.gates.compliance_rate() for s in sessions) * 100,
            "delegation_rate": sum(s.delegation_used for s in sessions) / total * 100,
            "workflow_log_rate": sum(s.workflow_log_created for s in sessions) / total * 100,
            "parallel_rate": sum(s.gates.g7_parallel for s in sessions) / total * 100,
        },
        "gate_compliance": gate_compliance,
        "gate_compliance_detail": {
            "G0_knowledge": {"rate": gate_compliance["G0"], "industry_pattern": "12-Factor: Config/context first"},
            "G1_todo": {"rate": gate_compliance["G1"], "industry_pattern": "Conventional Commits: Structured changes"},
            "G2_skill": {"rate": gate_compliance["G2"], "industry_pattern": "TDD: Test/purpose first"},
            "G3_start": {"rate": gate_compliance["G3"], "industry_pattern": "GitHub Flow: Branch creation"},
            "G4_end": {"rate": gate_compliance["G4"], "industry_pattern": "CI: Proper commit/merge process"},
            "G5_verify": {"rate": gate_compliance["G5"], "industry_pattern": "CI: Self-testing code"},
            "G6_single": {"rate": gate_compliance["G6"], "industry_pattern": "Trunk-Based: Short-lived branches"},
            "G7_parallel": {"rate": gate_compliance["G7"], "industry_pattern": "Agile: Parallel work, pair programming"},
        },
        "session_type_breakdown": type_breakdown,
        "conventional_commits": {
            "total_commits": total_commits,
            "type_distribution": commit_type_rates
        },
        "complexity_breakdown": {
            "simple": {
                "count": sum(1 for s in sessions if s.complexity == "simple"),
                "success_rate": sum(s.success for s in sessions if s.complexity == "simple") / 
                               max(1, sum(1 for s in sessions if s.complexity == "simple")) * 100
            },
            "medium": {
                "count": sum(1 for s in sessions if s.complexity == "medium"),
                "success_rate": sum(s.success for s in sessions if s.complexity == "medium") / 
                               max(1, sum(1 for s in sessions if s.complexity == "medium")) * 100
            },
            "complex": {
                "count": sum(1 for s in sessions if s.complexity == "complex"),
                "success_rate": sum(s.success for s in sessions if s.complexity == "complex") / 
                               max(1, sum(1 for s in sessions if s.complexity == "complex")) * 100
            }
        }
    }
    
    return results


def compare_optimization(config: SessionConfig) -> dict:
    """Run both baseline and optimized simulations for comparison."""
    
    print("=" * 60)
    print("AKIS Software Development Session Simulation (100k)")
    print("Industry Patterns: CI, GitHub Flow, TDD, Conventional Commits")
    print("=" * 60)
    
    # Run baseline
    baseline = run_simulation(config, "baseline")
    
    # Run optimized
    optimized = run_simulation(config, "optimized")
    
    # Calculate improvements
    improvements = {
        "success_rate": {
            "baseline": baseline["summary"]["success_rate"],
            "optimized": optimized["summary"]["success_rate"],
            "improvement": optimized["summary"]["success_rate"] - baseline["summary"]["success_rate"]
        },
        "tokens": {
            "baseline": baseline["summary"]["avg_tokens"],
            "optimized": optimized["summary"]["avg_tokens"],
            "improvement_pct": (baseline["summary"]["avg_tokens"] - optimized["summary"]["avg_tokens"]) / baseline["summary"]["avg_tokens"] * 100
        },
        "gate_compliance": {
            "baseline": baseline["summary"]["avg_gate_compliance"],
            "optimized": optimized["summary"]["avg_gate_compliance"],
            "improvement": optimized["summary"]["avg_gate_compliance"] - baseline["summary"]["avg_gate_compliance"]
        },
        "parallel_rate": {
            "baseline": baseline["summary"]["parallel_rate"],
            "optimized": optimized["summary"]["parallel_rate"],
            "improvement": optimized["summary"]["parallel_rate"] - baseline["summary"]["parallel_rate"]
        }
    }
    
    # Per-gate improvements
    gate_improvements = {}
    for gate in [f"G{i}" for i in range(8)]:
        gate_improvements[gate] = {
            "baseline": baseline["gate_compliance"][gate],
            "optimized": optimized["gate_compliance"][gate],
            "improvement": optimized["gate_compliance"][gate] - baseline["gate_compliance"][gate]
        }
    
    return {
        "baseline": baseline,
        "optimized": optimized,
        "improvements": improvements,
        "gate_improvements": gate_improvements
    }


def main():
    """Main entry point."""
    config = SessionConfig(
        total_sessions=100_000,
        random_seed=42,
        output_path="log/akis_sw_dev_simulation_100k.json"
    )
    
    results = compare_optimization(config)
    
    # Print summary
    print("\n" + "=" * 60)
    print("SIMULATION RESULTS SUMMARY")
    print("=" * 60)
    
    print("\n📊 Overall Metrics (Baseline → Optimized):")
    imp = results["improvements"]
    print(f"  Success Rate:     {imp['success_rate']['baseline']:.1f}% → {imp['success_rate']['optimized']:.1f}% (+{imp['success_rate']['improvement']:.1f}%)")
    print(f"  Gate Compliance:  {imp['gate_compliance']['baseline']:.1f}% → {imp['gate_compliance']['optimized']:.1f}% (+{imp['gate_compliance']['improvement']:.1f}%)")
    print(f"  Parallel Rate:    {imp['parallel_rate']['baseline']:.1f}% → {imp['parallel_rate']['optimized']:.1f}% (+{imp['parallel_rate']['improvement']:.1f}%)")
    print(f"  Avg Tokens:       {imp['tokens']['baseline']:.0f} → {imp['tokens']['optimized']:.0f} ({imp['tokens']['improvement_pct']:.1f}% reduction)")
    
    print("\n📈 Gate-Level Improvements:")
    for gate, data in results["gate_improvements"].items():
        print(f"  {gate}: {data['baseline']:.1f}% → {data['optimized']:.1f}% (+{data['improvement']:.1f}%)")
    
    print("\n📝 Session Type Breakdown (Optimized):")
    for stype, data in results["optimized"]["session_type_breakdown"].items():
        print(f"  {stype}: {data['count']:,} sessions ({data['percentage']:.1f}%), {data['success_rate']:.1f}% success")
    
    print("\n📦 Conventional Commits Distribution:")
    commits = results["optimized"]["conventional_commits"]["type_distribution"]
    for ct in ["feat", "fix", "refactor", "test", "docs", "chore"]:
        if ct in commits:
            print(f"  {ct}: {commits[ct]:.1f}%")
    
    # Save results
    output_path = Path(config.output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to {config.output_path}")
    
    return results


if __name__ == "__main__":
    main()
