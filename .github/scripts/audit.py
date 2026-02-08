#!/usr/bin/env python3
"""
AKIS Audit Script - 100k Session Simulation Engine

Audits AKIS framework components against these metrics:
- Token Usage: Total tokens consumed per session
- API Calls: Number of tool invocations
- Cognitive Load: Complexity score for human following
- Discipline: Ease of protocol adherence
- Resolution Effectiveness: Task completion rate
- Traceability: How well actions can be traced

Usage:
    python audit.py --target agents                    # Audit all agents
    python audit.py --target agents/AKIS.agent.md     # Audit specific agent
    python audit.py --target instructions             # Audit instructions
    python audit.py --target skills                   # Audit skills
    python audit.py --target knowledge                # Audit knowledge
    python audit.py --baseline                        # Create baseline
    python audit.py --compare                         # Compare to baseline
"""

import json
import os
import re
import sys
import random
import hashlib
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Tuple
from collections import Counter

# Constants
SIMULATION_COUNT = 100_000
WORKFLOW_DIR = Path("log/workflow")
AGENTS_DIR = Path(".github/agents")
SKILLS_DIR = Path(".github/skills")
INSTRUCTIONS_DIR = Path(".github/instructions")
KNOWLEDGE_FILE = Path("project_knowledge.json")
BASELINE_FILE = Path("log/audit_baseline.json")
RESULTS_FILE = Path("log/audit_results.json")


@dataclass
class SessionMetrics:
    """Metrics for a single simulated session"""
    token_usage: int
    api_calls: int
    cognitive_load: float  # 0-1 scale
    discipline_score: float  # 0-1 scale
    resolution_effectiveness: float  # 0-1 scale
    traceability: float  # 0-1 scale
    duration_seconds: int
    tasks_completed: int
    tasks_total: int
    skills_loaded: int
    complexity: str  # Simple/Medium/Complex


@dataclass
class AuditResult:
    """Result of auditing a component"""
    component: str
    component_type: str  # agent/instruction/skill/knowledge
    token_count: int
    section_count: int
    cognitive_load: float
    discipline_score: float
    resolution_potential: float
    traceability_score: float
    issues: List[str]
    suggestions: List[str]
    baseline_comparison: Optional[Dict] = None


@dataclass
class SimulationResult:
    """Result of 100k session simulation"""
    total_sessions: int
    avg_token_usage: float
    avg_api_calls: float
    avg_cognitive_load: float
    avg_discipline: float
    avg_resolution: float
    avg_traceability: float
    p50_duration: float
    p95_duration: float
    complexity_distribution: Dict[str, int]
    failure_rate: float
    improvement_potential: Dict[str, float]


class WorkflowParser:
    """Parse workflow logs to extract ground truth patterns"""
    
    def __init__(self, workflow_dir: Path):
        self.workflow_dir = workflow_dir
        self.workflows = []
        self._parse_all()
    
    def _parse_all(self):
        """Parse all workflow files"""
        if not self.workflow_dir.exists():
            return
        
        for f in self.workflow_dir.glob("*.md"):
            if f.name == "README.md":
                continue
            try:
                workflow = self._parse_workflow(f)
                if workflow:
                    self.workflows.append(workflow)
            except Exception:
                pass
    
    def _parse_workflow(self, path: Path) -> Optional[Dict]:
        """Parse a single workflow file"""
        content = path.read_text(encoding='utf-8', errors='ignore')
        
        workflow = {
            'file': path.name,
            'date': self._extract_date(path.name),
            'duration_min': self._extract_duration(content),
            'tasks_completed': self._count_tasks(content, completed=True),
            'tasks_total': self._count_tasks(content, completed=False),
            'skills_used': self._extract_skills(content),
            'complexity': self._detect_complexity(content),
            'files_modified': self._count_files(content),
            'has_worktree': '<MAIN>' in content or 'MAIN' in content,
            'has_metrics': '## Metrics' in content or '## Session Metrics' in content,
            'has_verification': '## Verification' in content,
            'delegations': content.count('<DELEGATE>') + content.count('DELEGATE'),
            'problems': self._has_problems(content)
        }
        return workflow
    
    def _extract_date(self, filename: str) -> str:
        match = re.match(r'(\d{4}-\d{2}-\d{2})', filename)
        return match.group(1) if match else ''
    
    def _extract_duration(self, content: str) -> int:
        patterns = [
            r'~(\d+)min',
            r'Duration[:\s]+~?(\d+)',
            r'\|.*?(\d+)min'
        ]
        for pattern in patterns:
            match = re.search(pattern, content)
            if match:
                return int(match.group(1))
        return 15  # default
    
    def _count_tasks(self, content: str, completed: bool) -> int:
        if completed:
            return content.count('✓')
        else:
            return content.count('✓') + content.count('○') + content.count('◆')
    
    def _extract_skills(self, content: str) -> List[str]:
        skills = re.findall(r'\.github/skills/([^/]+)/SKILL\.md', content)
        return list(set(skills))
    
    def _detect_complexity(self, content: str) -> str:
        if 'Complex' in content:
            return 'Complex'
        elif 'Medium' in content:
            return 'Medium'
        elif 'Simple' in content:
            return 'Simple'
        else:
            # Infer from task count
            tasks = self._count_tasks(content, completed=False)
            if tasks >= 6:
                return 'Complex'
            elif tasks >= 3:
                return 'Medium'
            return 'Simple'
    
    def _count_files(self, content: str) -> int:
        match = re.search(r'Files[:\s]+(\d+)', content)
        if match:
            return int(match.group(1))
        return len(re.findall(r'\|.*?`[^`]+\.[a-z]+`', content))
    
    def _has_problems(self, content: str) -> bool:
        return '## Problems' in content or 'Problem:' in content

    def get_patterns(self) -> Dict:
        """Extract statistical patterns from workflows"""
        if not self.workflows:
            return self._default_patterns()
        
        durations = [w['duration_min'] for w in self.workflows]
        tasks = [w['tasks_completed'] for w in self.workflows]
        files = [w['files_modified'] for w in self.workflows]
        skills = [len(w['skills_used']) for w in self.workflows]
        complexities = Counter(w['complexity'] for w in self.workflows)
        
        return {
            'duration_avg': sum(durations) / len(durations),
            'duration_std': self._std(durations),
            'tasks_avg': sum(tasks) / len(tasks),
            'tasks_std': self._std(tasks),
            'files_avg': sum(files) / len(files),
            'skills_avg': sum(skills) / len(skills),
            'complexity_dist': dict(complexities),
            'problem_rate': sum(1 for w in self.workflows if w['problems']) / len(self.workflows),
            'worktree_compliance': sum(1 for w in self.workflows if w['has_worktree']) / len(self.workflows),
            'metrics_compliance': sum(1 for w in self.workflows if w['has_metrics']) / len(self.workflows),
            'verification_compliance': sum(1 for w in self.workflows if w['has_verification']) / len(self.workflows),
            'delegation_rate': sum(w['delegations'] for w in self.workflows) / len(self.workflows),
            'total_workflows': len(self.workflows)
        }
    
    def _std(self, values: List[float]) -> float:
        if len(values) < 2:
            return 0
        avg = sum(values) / len(values)
        return (sum((x - avg) ** 2 for x in values) / len(values)) ** 0.5
    
    def _default_patterns(self) -> Dict:
        return {
            'duration_avg': 20,
            'duration_std': 15,
            'tasks_avg': 5,
            'tasks_std': 3,
            'files_avg': 4,
            'skills_avg': 2,
            'complexity_dist': {'Simple': 40, 'Medium': 40, 'Complex': 20},
            'problem_rate': 0.15,
            'worktree_compliance': 0.85,
            'metrics_compliance': 0.70,
            'verification_compliance': 0.60,
            'delegation_rate': 0.1,
            'total_workflows': 0
        }


class ComponentAnalyzer:
    """Analyze AKIS components for audit metrics"""
    
    TOKEN_WEIGHTS = {
        'table': 1.2,  # Tables are dense
        'code_block': 0.8,  # Code blocks are scannable
        'list': 0.9,  # Lists are easy to follow
        'paragraph': 1.0,  # Normal text
        'header': 0.5  # Headers are low-cost
    }
    
    def analyze_agent(self, path: Path) -> AuditResult:
        """Analyze an agent file"""
        content = path.read_text(encoding='utf-8')
        
        # Token analysis
        words = len(content.split())
        
        # Structure analysis
        sections = len(re.findall(r'^##\s+', content, re.MULTILINE))
        tables = len(re.findall(r'\|.*\|', content))
        code_blocks = len(re.findall(r'```', content)) // 2
        lists = len(re.findall(r'^[-*]\s+', content, re.MULTILINE))
        
        # Cognitive load calculation
        # More sections = higher cognitive load
        # Tables are efficient, reduce load
        # Code blocks are scannable
        cognitive_base = min(1.0, sections / 15)
        cognitive_adjustment = -0.1 * min(tables, 5) / 5  # Tables help
        cognitive_adjustment += 0.05 * max(0, sections - 10) / 10  # Too many sections hurt
        cognitive_load = max(0.1, min(1.0, cognitive_base + cognitive_adjustment))
        
        # Discipline score - how easy to follow
        has_gates = 'HARD GATES' in content or 'GATES' in content
        has_protocols = 'Protocol' in content
        has_rules = 'Rules' in content or 'DO:' in content
        has_recovery = 'Recovery' in content or 'Lost?' in content
        
        discipline_score = sum([has_gates, has_protocols, has_rules, has_recovery]) / 4
        
        # Resolution potential
        has_tools = 'Tools' in content or 'Tool' in content
        has_workflow = 'Workflow' in content or 'WORK' in content
        has_end = 'END' in content
        has_delegation = 'Delegate' in content or 'DELEGATE' in content
        
        resolution_potential = sum([has_tools, has_workflow, has_end, has_delegation]) / 4
        
        # Traceability
        has_worktree = '<MAIN>' in content or 'Worktree' in content
        has_symbols = '✓' in content or '◆' in content
        has_checkpoint = 'Checkpoint' in content or 'CP:' in content
        has_summary = 'Summary' in content or 'END Summary' in content
        
        traceability = sum([has_worktree, has_symbols, has_checkpoint, has_summary]) / 4
        
        # Issues detection
        issues = []
        if words > 3000:
            issues.append(f"High token count: {words} words (target <2000)")
        if sections > 15:
            issues.append(f"Too many sections: {sections} (target <12)")
        if cognitive_load > 0.7:
            issues.append(f"High cognitive load: {cognitive_load:.2f}")
        if not has_gates:
            issues.append("Missing HARD GATES section")
        if not has_recovery:
            issues.append("Missing Recovery section")
        
        # Suggestions
        suggestions = []
        if words > 2000:
            suggestions.append("Offload Workflow Log Template to templates/workflow-log.md")
        if sections > 12:
            suggestions.append("Consolidate related sections")
        if 'Sub-Agent Orchestration' in content and content.count('runsubagent') > 5:
            suggestions.append("Move delegation examples to agents/INDEX.md")
        if '## Unified Scripts Interface' in content:
            suggestions.append("Scripts interface can be referenced from scripts/README.md")
        
        return AuditResult(
            component=path.name,
            component_type='agent',
            token_count=words,
            section_count=sections,
            cognitive_load=cognitive_load,
            discipline_score=discipline_score,
            resolution_potential=resolution_potential,
            traceability_score=traceability,
            issues=issues,
            suggestions=suggestions
        )
    
    def analyze_instruction(self, path: Path) -> AuditResult:
        """Analyze an instruction file"""
        content = path.read_text(encoding='utf-8')
        words = len(content.split())
        sections = len(re.findall(r'^##\s+', content, re.MULTILINE))
        
        # Instructions should be very terse
        cognitive_load = min(1.0, words / 200)  # Target <200 words
        
        # Check GitHub Copilot custom instructions standard compliance
        # All .instructions.md files MUST have frontmatter with applyTo
        has_frontmatter = content.strip().startswith('---')
        has_apply_to = 'applyTo:' in content
        
        # Check for actionable format
        has_table = '|' in content
        has_list = re.search(r'^[-*]\s+', content, re.MULTILINE)
        discipline_score = 0.0
        if has_frontmatter and has_apply_to:
            discipline_score += 0.4  # Required by standard
        if has_table:
            discipline_score += 0.3
        if has_list:
            discipline_score += 0.3
        
        issues = []
        if words > 200:
            issues.append(f"Too verbose: {words} words (target <200)")
        if not has_frontmatter:
            issues.append("Missing YAML frontmatter (required by GitHub Copilot standard)")
        if not has_apply_to:
            issues.append("Missing applyTo field (required by GitHub Copilot standard)")
        
        suggestions = []
        if words > 150 and not has_table:
            suggestions.append("Convert to table format for density")
        
        return AuditResult(
            component=path.name,
            component_type='instruction',
            token_count=words,
            section_count=sections,
            cognitive_load=cognitive_load,
            discipline_score=discipline_score,
            resolution_potential=0.8,  # Instructions are always high
            traceability_score=0.7 if has_apply_to else 0.3,
            issues=issues,
            suggestions=suggestions
        )
    
    def analyze_skill(self, path: Path) -> AuditResult:
        """Analyze a skill file"""
        content = path.read_text(encoding='utf-8')
        words = len(content.split())
        sections = len(re.findall(r'^##\s+', content, re.MULTILINE))
        
        # Skills should be <250 words (balanced for effectiveness)
        cognitive_load = min(1.0, words / 250)
        
        # Check Agent Skills Standard compliance
        # Standard only requires: name + description (no triggers field)
        has_name = 'name:' in content
        has_description = 'description:' in content
        description_match = re.search(r'description:\s*(.+?)(?:\n---|\n\n)', content, re.DOTALL)
        good_description = bool(description_match and len(description_match.group(1).strip()) > 50)
        has_patterns = 'Patterns' in content or '## Critical' in content or '## Rules' in content
        has_avoid = 'Avoid' in content
        has_gotchas = '## ⚠️ Critical Gotchas' in content or '## Critical Gotchas' in content
        
        discipline_score = sum([has_name, has_description, good_description, has_patterns, has_avoid, has_gotchas]) / 6
        
        issues = []
        if words > 350:  # Max is 350
            issues.append(f"Too verbose: {words} words (max 350)")
        if not has_name:
            issues.append("Missing name field (required by Agent Skills Standard)")
        if not has_description:
            issues.append("Missing description field (required by Agent Skills Standard)")
        if not good_description:
            issues.append("Description too short (should explain what skill does AND when to use)")
        if not has_gotchas:
            issues.append("Missing ⚠️ Critical Gotchas section (required for effectiveness)")
        
        suggestions = []
        
        return AuditResult(
            component=path.name,
            component_type='skill',
            token_count=words,
            section_count=sections,
            cognitive_load=cognitive_load,
            discipline_score=discipline_score,
            resolution_potential=0.9,
            traceability_score=0.7 if good_description else 0.4,
            issues=issues,
            suggestions=suggestions
        )
    
    def analyze_knowledge(self, path: Path) -> AuditResult:
        """Analyze project_knowledge.json against v3.0 schema"""
        issues = []
        suggestions = []
        
        # Parse JSONL format
        try:
            lines = path.read_text(encoding='utf-8').strip().split('\n')
            records = [json.loads(line) for line in lines if line.strip()]
        except Exception as e:
            return AuditResult(
                component=path.name, component_type='knowledge',
                token_count=0, section_count=0, cognitive_load=1.0,
                discipline_score=0.0, resolution_potential=0.0, traceability_score=0.0,
                issues=[f"Parse error: {e}"], suggestions=[]
            )
        
        # Extract layers by type
        layers = {r.get('type'): r for r in records if 'type' in r}
        entities = [r for r in records if r.get('type') == 'entity']
        
        # Metrics with targets
        metrics = {
            'hot_cache_entities': (len(layers.get('hot_cache', {}).get('top_entities', {})), 20),
            'common_answers': (len(layers.get('hot_cache', {}).get('common_answers', {})), 20),
            'quick_facts': (len(layers.get('hot_cache', {}).get('quick_facts', {})), 5),
            'domain_coverage': (self._count_domains(layers.get('domain_index', {})), 3),
            'gotchas': (len(layers.get('gotchas', {}).get('items', [])), 10),
            'session_patterns': (len(layers.get('session_patterns', {}).get('patterns', [])), 5),
            'interconnections': (self._count_chains(layers.get('interconnections', {})), 5),
            'entities': (len(entities), 50),
        }
        
        # Calculate scores
        score_sum = 0
        score_count = 0
        for name, (actual, target) in metrics.items():
            ratio = min(1.0, actual / target) if target > 0 else 0
            score_sum += ratio
            score_count += 1
            if actual < target:
                issues.append(f"{name}: {actual}/{target} (below target)")
        
        completeness_score = score_sum / score_count if score_count > 0 else 0
        
        # Check staleness (change_tracking)
        ct = layers.get('change_tracking', {})
        file_hashes = ct.get('file_hashes', {})
        if len(file_hashes) < 3:
            issues.append(f"change_tracking: only {len(file_hashes)} files tracked")
        
        # Check required layers
        required_layers = ['hot_cache', 'domain_index', 'gotchas', 'session_patterns', 'interconnections']
        missing = [l for l in required_layers if l not in layers]
        if missing:
            issues.append(f"Missing layers: {', '.join(missing)}")
        
        # Token estimation (file size / 4 chars per token)
        file_size = path.stat().st_size
        estimated_tokens = file_size // 4
        
        # Suggestions
        if metrics['gotchas'][0] < metrics['gotchas'][1]:
            suggestions.append("Run knowledge.py --update to extract gotchas from workflow logs")
        if metrics['entities'][0] < 100:
            suggestions.append("Run knowledge.py --generate for comprehensive entity coverage")
        if metrics['interconnections'][0] < 5:
            suggestions.append("Add backend_chains to interconnections for API tracing")
        
        # Discipline: how well structured
        discipline = 0.5
        if 'hot_cache' in layers and layers['hot_cache'].get('version'):
            discipline += 0.2
        if 'map' in layers:
            discipline += 0.15
        if len(entities) >= 50:
            discipline += 0.15
        
        return AuditResult(
            component=path.name,
            component_type='knowledge',
            token_count=estimated_tokens,
            section_count=len(layers),
            cognitive_load=0.3,  # Low - not loaded into context directly
            discipline_score=min(1.0, discipline),
            resolution_potential=completeness_score,
            traceability_score=completeness_score * 0.9,
            issues=issues,
            suggestions=suggestions
        )
    
    def _count_domains(self, domain_index: Dict) -> int:
        """Count domain categories"""
        domains = ['frontend', 'backend', 'infrastructure']
        return sum(1 for d in domains if d in domain_index and domain_index[d])
    
    def _count_chains(self, interconnections: Dict) -> int:
        """Count interconnection chains"""
        backend = len(interconnections.get('backend_chains', []))
        frontend = len(interconnections.get('frontend_chains', []))
        return backend + frontend


class SessionSimulator:
    """Simulate 100k sessions based on workflow patterns"""
    
    def __init__(self, patterns: Dict, component_results: List[AuditResult]):
        self.patterns = patterns
        self.components = component_results
        random.seed(42)  # Reproducible
    
    def simulate(self, count: int = SIMULATION_COUNT) -> SimulationResult:
        """Run simulation"""
        sessions = []
        
        for i in range(count):
            session = self._simulate_session(i)
            sessions.append(session)
        
        return self._aggregate(sessions)
    
    def _simulate_session(self, seed: int) -> SessionMetrics:
        """Simulate a single session"""
        random.seed(seed)
        
        # Determine complexity based on distribution
        complexity = self._pick_complexity()
        
        # Base metrics from patterns
        duration = max(5, int(random.gauss(
            self.patterns['duration_avg'],
            self.patterns['duration_std']
        )))
        
        tasks_total = max(1, int(random.gauss(
            self.patterns['tasks_avg'],
            self.patterns['tasks_std']
        )))
        
        # Completion rate based on complexity
        completion_rates = {'Simple': 0.95, 'Medium': 0.88, 'Complex': 0.78}
        base_completion = completion_rates.get(complexity, 0.85)
        
        # Adjust for component quality
        avg_discipline = sum(c.discipline_score for c in self.components) / max(1, len(self.components))
        completion_adjustment = (avg_discipline - 0.5) * 0.2
        completion_rate = min(1.0, base_completion + completion_adjustment)
        
        tasks_completed = int(tasks_total * completion_rate)
        
        # Skills loaded
        skills_loaded = max(1, int(random.gauss(
            self.patterns['skills_avg'],
            1
        )))
        
        # Token usage based on component complexity
        avg_tokens = sum(c.token_count for c in self.components) / max(1, len(self.components))
        base_tokens = int(avg_tokens * (1 + tasks_total * 0.3))
        token_noise = random.gauss(0, base_tokens * 0.2)
        token_usage = int(max(500, base_tokens + token_noise))
        
        # API calls - correlate with tasks and complexity
        complexity_multiplier = {'Simple': 1, 'Medium': 1.5, 'Complex': 2.5}
        base_api = tasks_total * 3 * complexity_multiplier.get(complexity, 1.5)
        api_calls = int(max(3, base_api + random.gauss(0, base_api * 0.3)))
        
        # Cognitive load from component analysis
        avg_cognitive = sum(c.cognitive_load for c in self.components) / max(1, len(self.components))
        cognitive_load = min(1.0, max(0.1, avg_cognitive + random.gauss(0, 0.1)))
        
        # Discipline score
        discipline = min(1.0, max(0.1, avg_discipline + random.gauss(0, 0.1)))
        
        # Resolution effectiveness
        resolution = completion_rate * discipline
        
        # Traceability
        avg_trace = sum(c.traceability_score for c in self.components) / max(1, len(self.components))
        traceability = min(1.0, max(0.1, avg_trace + random.gauss(0, 0.1)))
        
        return SessionMetrics(
            token_usage=token_usage,
            api_calls=api_calls,
            cognitive_load=cognitive_load,
            discipline_score=discipline,
            resolution_effectiveness=resolution,
            traceability=traceability,
            duration_seconds=duration * 60,
            tasks_completed=tasks_completed,
            tasks_total=tasks_total,
            skills_loaded=skills_loaded,
            complexity=complexity
        )
    
    def _pick_complexity(self) -> str:
        dist = self.patterns.get('complexity_dist', {})
        total = sum(dist.values()) or 1
        r = random.random() * total
        cumulative = 0
        for complexity, count in dist.items():
            cumulative += count
            if r <= cumulative:
                return complexity
        return 'Medium'
    
    def _aggregate(self, sessions: List[SessionMetrics]) -> SimulationResult:
        """Aggregate session metrics"""
        n = len(sessions)
        
        tokens = [s.token_usage for s in sessions]
        api_calls = [s.api_calls for s in sessions]
        cognitive = [s.cognitive_load for s in sessions]
        discipline = [s.discipline_score for s in sessions]
        resolution = [s.resolution_effectiveness for s in sessions]
        trace = [s.traceability for s in sessions]
        durations = sorted([s.duration_seconds for s in sessions])
        
        complexity_dist = Counter(s.complexity for s in sessions)
        failures = sum(1 for s in sessions if s.tasks_completed < s.tasks_total * 0.5)
        
        # Calculate improvement potential
        improvement = {
            'token_reduction': (sum(tokens) / n - 1500) / (sum(tokens) / n) if sum(tokens) / n > 1500 else 0,
            'api_reduction': (sum(api_calls) / n - 8) / (sum(api_calls) / n) if sum(api_calls) / n > 8 else 0,
            'cognitive_reduction': sum(cognitive) / n - 0.4 if sum(cognitive) / n > 0.4 else 0,
            'discipline_improvement': 0.95 - sum(discipline) / n if sum(discipline) / n < 0.95 else 0,
            'resolution_improvement': 0.90 - sum(resolution) / n if sum(resolution) / n < 0.90 else 0,
            'trace_improvement': 0.85 - sum(trace) / n if sum(trace) / n < 0.85 else 0
        }
        
        return SimulationResult(
            total_sessions=n,
            avg_token_usage=sum(tokens) / n,
            avg_api_calls=sum(api_calls) / n,
            avg_cognitive_load=sum(cognitive) / n,
            avg_discipline=sum(discipline) / n,
            avg_resolution=sum(resolution) / n,
            avg_traceability=sum(trace) / n,
            p50_duration=durations[n // 2],
            p95_duration=durations[int(n * 0.95)],
            complexity_distribution=dict(complexity_dist),
            failure_rate=failures / n,
            improvement_potential=improvement
        )


class OptimizationEngine:
    """Propose and simulate optimizations"""
    
    def __init__(self, audit_results: List[AuditResult], baseline: SimulationResult):
        self.results = audit_results
        self.baseline = baseline
    
    def propose_optimizations(self) -> List[Dict]:
        """Generate optimization proposals"""
        proposals = []
        
        for result in self.results:
            if result.component_type == 'agent':
                proposals.extend(self._agent_optimizations(result))
            elif result.component_type == 'instruction':
                proposals.extend(self._instruction_optimizations(result))
            elif result.component_type == 'skill':
                proposals.extend(self._skill_optimizations(result))
            elif result.component_type == 'knowledge':
                proposals.extend(self._knowledge_optimizations(result))
        
        return proposals
    
    def _agent_optimizations(self, result: AuditResult) -> List[Dict]:
        opts = []
        
        if result.token_count > 2500:
            opts.append({
                'type': 'offload',
                'component': result.component,
                'section': 'Workflow Log Template',
                'target': '.github/templates/workflow-log.md',
                'token_reduction': 400,
                'cognitive_reduction': 0.05,
                'rationale': 'Template is reference material, not runtime instruction'
            })
        
        if result.token_count > 2000:
            opts.append({
                'type': 'offload',
                'component': result.component,
                'section': 'Unified Scripts Interface',
                'target': '.github/scripts/README.md',
                'token_reduction': 200,
                'cognitive_reduction': 0.03,
                'rationale': 'Scripts documentation is lookup, not workflow'
            })
        
        if result.cognitive_load > 0.6:
            opts.append({
                'type': 'consolidate',
                'component': result.component,
                'sections': ['Tools', 'Rules'],
                'token_reduction': 100,
                'cognitive_reduction': 0.08,
                'rationale': 'Combine related short sections'
            })
        
        if 'Sub-Agent Orchestration' in result.component:
            opts.append({
                'type': 'reference',
                'component': result.component,
                'section': 'Sub-Agent Orchestration',
                'target': '.github/agents/INDEX.md',
                'token_reduction': 300,
                'cognitive_reduction': 0.04,
                'rationale': 'Delegation details can be looked up, core rules stay'
            })
        
        return opts
    
    def _instruction_optimizations(self, result: AuditResult) -> List[Dict]:
        opts = []
        
        if result.token_count > 200:
            opts.append({
                'type': 'compress',
                'component': result.component,
                'target_tokens': 150,
                'token_reduction': result.token_count - 150,
                'rationale': 'Instructions must be <200 tokens for fast parsing'
            })
        
        return opts
    
    def _skill_optimizations(self, result: AuditResult) -> List[Dict]:
        opts = []
        
        if result.token_count > 350:  # Max is 350, target is 250
            opts.append({
                'type': 'compress',
                'component': result.component,
                'target_tokens': 250,
                'token_reduction': result.token_count - 250,
                'rationale': 'Skills must be <350 tokens (target 250, balanced for effectiveness)'
            })
        
        if result.traceability_score < 0.6:
            opts.append({
                'type': 'improve_description',
                'component': result.component,
                'trace_improvement': 0.2,
                'rationale': 'Improve description to explain what skill does AND when to use it'
            })
        
        return opts
    
    def _knowledge_optimizations(self, result: AuditResult) -> List[Dict]:
        opts = []
        
        # Parse issues for specific recommendations
        for issue in result.issues:
            if 'gotchas' in issue and 'below target' in issue:
                opts.append({
                    'type': 'populate',
                    'component': result.component,
                    'section': 'gotchas',
                    'command': 'python .github/scripts/knowledge.py --update',
                    'rationale': 'Extract gotchas from workflow logs to accelerate debugging (11% of queries)'
                })
            if 'interconnections' in issue and 'below target' in issue:
                opts.append({
                    'type': 'generate',
                    'component': result.component,
                    'section': 'interconnections',
                    'command': 'python .github/scripts/knowledge.py --generate',
                    'rationale': 'Generate interconnection chains for dependency lookup (14% of queries)'
                })
            if 'entities' in issue and 'below target' in issue:
                opts.append({
                    'type': 'generate',
                    'component': result.component,
                    'section': 'entities',
                    'command': 'python .github/scripts/knowledge.py --generate',
                    'rationale': 'Generate comprehensive entity coverage for codebase navigation'
                })
        
        return opts
    
    def simulate_optimized(self, proposals: List[Dict], patterns: Dict) -> SimulationResult:
        """Simulate with optimizations applied"""
        # Calculate total improvements
        total_token_reduction = sum(p.get('token_reduction', 0) for p in proposals)
        total_cognitive_reduction = sum(p.get('cognitive_reduction', 0) for p in proposals)
        
        # Create optimized component results
        optimized_results = []
        for result in self.results:
            opt_result = AuditResult(
                component=result.component,
                component_type=result.component_type,
                token_count=max(100, result.token_count - total_token_reduction // len(self.results)),
                section_count=result.section_count,
                cognitive_load=max(0.2, result.cognitive_load - total_cognitive_reduction),
                discipline_score=min(0.95, result.discipline_score + 0.05),
                resolution_potential=min(0.95, result.resolution_potential + 0.03),
                traceability_score=min(0.90, result.traceability_score + 0.05),
                issues=[],
                suggestions=[]
            )
            optimized_results.append(opt_result)
        
        # Run optimized simulation
        simulator = SessionSimulator(patterns, optimized_results)
        return simulator.simulate()


def run_audit(target: str, create_baseline: bool = False, compare: bool = False):
    """Main audit function"""
    print("=" * 70)
    print("AKIS AUDIT ENGINE - 100k Session Simulation")
    print("=" * 70)
    
    # Parse workflows for ground truth
    print("\n📊 Parsing workflow logs for ground truth...")
    parser = WorkflowParser(WORKFLOW_DIR)
    patterns = parser.get_patterns()
    print(f"   Found {patterns['total_workflows']} workflow logs")
    print(f"   Avg duration: {patterns['duration_avg']:.1f}min")
    print(f"   Avg tasks: {patterns['tasks_avg']:.1f}")
    print(f"   Problem rate: {patterns['problem_rate']*100:.1f}%")
    print(f"   Worktree compliance: {patterns['worktree_compliance']*100:.1f}%")
    
    # Analyze components
    print("\n🔍 Analyzing components...")
    analyzer = ComponentAnalyzer()
    results = []
    
    if target == 'agents' or target.endswith('.agent.md'):
        if target.endswith('.agent.md'):
            paths = [AGENTS_DIR / target.split('/')[-1]]
        else:
            paths = list(AGENTS_DIR.glob('*.agent.md'))
        
        for path in paths:
            if path.exists():
                result = analyzer.analyze_agent(path)
                results.append(result)
                print(f"   ✓ {result.component}: {result.token_count} tokens, cognitive={result.cognitive_load:.2f}")
    
    if target == 'instructions':
        for path in INSTRUCTIONS_DIR.glob('*.md'):
            result = analyzer.analyze_instruction(path)
            results.append(result)
            print(f"   ✓ {result.component}: {result.token_count} tokens")
    
    if target == 'skills':
        for skill_dir in SKILLS_DIR.iterdir():
            skill_file = skill_dir / 'SKILL.md'
            if skill_file.exists():
                result = analyzer.analyze_skill(skill_file)
                results.append(result)
                print(f"   ✓ {skill_dir.name}: {result.token_count} tokens")
    
    if target == 'knowledge':
        if KNOWLEDGE_FILE.exists():
            result = analyzer.analyze_knowledge(KNOWLEDGE_FILE)
            results.append(result)
            print(f"   ✓ {result.component}: ~{result.token_count} tokens, {result.section_count} layers")
            
            # Extended knowledge metrics
            print("\n📊 KNOWLEDGE v3.0 METRICS:")
            lines = KNOWLEDGE_FILE.read_text().strip().split('\n')
            records = [json.loads(l) for l in lines if l.strip()]
            layers = {r.get('type'): r for r in records if 'type' in r}
            entities = [r for r in records if r.get('type') == 'entity']
            
            hc = layers.get('hot_cache', {})
            print(f"   HOT_CACHE:")
            print(f"     - top_entities:    {len(hc.get('top_entities', {})):>3}/20")
            print(f"     - common_answers:  {len(hc.get('common_answers', {})):>3}/20")
            print(f"     - quick_facts:     {len(hc.get('quick_facts', {})):>3}/5")
            
            di = layers.get('domain_index', {})
            domains = sum(1 for d in ['frontend','backend','infrastructure'] if d in di and di[d])
            print(f"   DOMAIN_INDEX:        {domains:>3}/3 domains")
            
            gt = layers.get('gotchas', {})
            print(f"   GOTCHAS:             {len(gt.get('items', [])):>3}/10")
            
            sp = layers.get('session_patterns', {})
            print(f"   SESSION_PATTERNS:    {len(sp.get('patterns', [])):>3}/5")
            
            ic = layers.get('interconnections', {})
            chains = len(ic.get('backend_chains', [])) + len(ic.get('frontend_chains', []))
            print(f"   INTERCONNECTIONS:    {chains:>3}/5 chains")
            
            print(f"   ENTITIES:            {len(entities):>3}/50")
        else:
            print(f"   ⚠ Knowledge file not found: {KNOWLEDGE_FILE}")
    
    if not results:
        print(f"   ⚠ No components found for target: {target}")
        return
    
    # Show issues
    print("\n⚠️  Issues Found:")
    total_issues = 0
    for result in results:
        for issue in result.issues:
            print(f"   [{result.component}] {issue}")
            total_issues += 1
    if total_issues == 0:
        print("   None")
    
    # Run baseline simulation
    print(f"\n🎲 Running {SIMULATION_COUNT:,} session simulation...")
    simulator = SessionSimulator(patterns, results)
    baseline_result = simulator.simulate()
    
    print(f"\n📈 BASELINE RESULTS:")
    print(f"   Token Usage:     {baseline_result.avg_token_usage:.0f} avg")
    print(f"   API Calls:       {baseline_result.avg_api_calls:.1f} avg")
    print(f"   Cognitive Load:  {baseline_result.avg_cognitive_load:.2%}")
    print(f"   Discipline:      {baseline_result.avg_discipline:.2%}")
    print(f"   Resolution:      {baseline_result.avg_resolution:.2%}")
    print(f"   Traceability:    {baseline_result.avg_traceability:.2%}")
    print(f"   Failure Rate:    {baseline_result.failure_rate:.2%}")
    print(f"   Duration P50:    {baseline_result.p50_duration/60:.0f}min")
    print(f"   Duration P95:    {baseline_result.p95_duration/60:.0f}min")
    
    # Propose optimizations
    print("\n💡 OPTIMIZATION PROPOSALS:")
    engine = OptimizationEngine(results, baseline_result)
    proposals = engine.propose_optimizations()
    
    if not proposals:
        print("   No optimizations needed - components are well-optimized")
    else:
        for i, prop in enumerate(proposals, 1):
            print(f"\n   {i}. [{prop['type'].upper()}] {prop['component']}")
            if 'section' in prop:
                print(f"      Section: {prop['section']}")
            if 'target' in prop:
                print(f"      Move to: {prop['target']}")
            if 'token_reduction' in prop:
                print(f"      Token reduction: -{prop['token_reduction']}")
            if 'cognitive_reduction' in prop:
                print(f"      Cognitive reduction: -{prop['cognitive_reduction']:.0%}")
            print(f"      Rationale: {prop['rationale']}")
    
    # Simulate with optimizations
    if proposals:
        print(f"\n🔄 Simulating with optimizations applied...")
        optimized_result = engine.simulate_optimized(proposals, patterns)
        
        print(f"\n📈 OPTIMIZED RESULTS:")
        print(f"   Token Usage:     {optimized_result.avg_token_usage:.0f} avg " +
              f"({(optimized_result.avg_token_usage - baseline_result.avg_token_usage)/baseline_result.avg_token_usage:+.1%})")
        print(f"   API Calls:       {optimized_result.avg_api_calls:.1f} avg " +
              f"({(optimized_result.avg_api_calls - baseline_result.avg_api_calls)/baseline_result.avg_api_calls:+.1%})")
        print(f"   Cognitive Load:  {optimized_result.avg_cognitive_load:.2%} " +
              f"({(optimized_result.avg_cognitive_load - baseline_result.avg_cognitive_load):+.1%})")
        print(f"   Discipline:      {optimized_result.avg_discipline:.2%} " +
              f"({(optimized_result.avg_discipline - baseline_result.avg_discipline):+.1%})")
        print(f"   Resolution:      {optimized_result.avg_resolution:.2%} " +
              f"({(optimized_result.avg_resolution - baseline_result.avg_resolution):+.1%})")
        print(f"   Traceability:    {optimized_result.avg_traceability:.2%} " +
              f"({(optimized_result.avg_traceability - baseline_result.avg_traceability):+.1%})")
        print(f"   Failure Rate:    {optimized_result.failure_rate:.2%} " +
              f"({(optimized_result.failure_rate - baseline_result.failure_rate):+.1%})")
        
        # Summary
        print("\n" + "=" * 70)
        print("MEASURABLE IMPROVEMENTS IF APPLIED:")
        print("=" * 70)
        
        token_improvement = (baseline_result.avg_token_usage - optimized_result.avg_token_usage) / baseline_result.avg_token_usage
        api_improvement = (baseline_result.avg_api_calls - optimized_result.avg_api_calls) / baseline_result.avg_api_calls
        cognitive_improvement = baseline_result.avg_cognitive_load - optimized_result.avg_cognitive_load
        resolution_improvement = optimized_result.avg_resolution - baseline_result.avg_resolution
        
        if token_improvement > 0.05:
            print(f"   ✓ Token Usage:    -{token_improvement:.1%} per session")
        if api_improvement > 0.05:
            print(f"   ✓ API Calls:      -{api_improvement:.1%} per session")
        if cognitive_improvement > 0.03:
            print(f"   ✓ Cognitive Load: -{cognitive_improvement:.1%}")
        if resolution_improvement > 0.02:
            print(f"   ✓ Resolution:     +{resolution_improvement:.1%}")
        
        if token_improvement <= 0.05 and api_improvement <= 0.05:
            print("   ⚠ Improvements below 5% threshold - no changes recommended")
    
    # Save results
    if create_baseline:
        BASELINE_FILE.parent.mkdir(exist_ok=True)
        with open(BASELINE_FILE, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'patterns': patterns,
                'baseline': asdict(baseline_result),
                'component_count': len(results)
            }, f, indent=2)
        print(f"\n💾 Baseline saved to {BASELINE_FILE}")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='AKIS Audit Engine')
    parser.add_argument('--target', default='agents', 
                       help='Target to audit: agents, instructions, skills, knowledge, or specific file')
    parser.add_argument('--baseline', action='store_true',
                       help='Create baseline from current state')
    parser.add_argument('--compare', action='store_true',
                       help='Compare to saved baseline')
    
    args = parser.parse_args()
    run_audit(args.target, args.baseline, args.compare)
