"""
iOS Software Factory – App Store Launch Pipeline
=================================================
Gate (0):  GoNoGoCrew  →  Idea Brightness + Market Opportunity → GO / NO-GO
Sequential (1-4): iOSFactoryCrew → Market Research → Copywriting → ASO → Legal
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"


def _build_llm() -> LLM:
    """Return an LLM instance, always loading .env first."""
    load_dotenv(_ENV_FILE, override=True)
    github_token = os.getenv("GITHUB_TOKEN")
    if github_token:
        return LLM(
            model=f"openai/{os.getenv('GITHUB_MODEL', 'gpt-4o')}",
            base_url="https://models.inference.ai.azure.com",
            api_key=github_token,
            max_tokens=4096,
        )
    return LLM(model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o"), max_tokens=4096)


# ══════════════════════════════════════════════════════════════════════════════
# GATE CREW  –  Step 0: Evaluate idea brightness & market opportunity
# ══════════════════════════════════════════════════════════════════════════════

@CrewBase
class GoNoGoCrew:
    """Single-agent gate that scores an idea and returns GO or NO-GO."""

    agents_config = "config/agents.yaml"
    tasks_config  = "config/tasks.yaml"

    @agent
    def idea_evaluator(self) -> Agent:
        return Agent(
            config=self.agents_config["idea_evaluator"],  # type: ignore[index]
            llm=_build_llm(),
            verbose=True,
        )

    @task
    def idea_evaluation(self) -> Task:
        return Task(config=self.tasks_config["idea_evaluation"])  # type: ignore[index]

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )


# ══════════════════════════════════════════════════════════════════════════════
# LAUNCH CREW  –  Steps 1-4: Full App Store pipeline (runs only on GO)
# ══════════════════════════════════════════════════════════════════════════════

@CrewBase
class iOSFactoryCrew:
    """App Store Launch Pipeline – four sequential specialist agents."""

    agents_config = "config/agents.yaml"
    tasks_config  = "config/tasks.yaml"

    # ── Agents ──────────────────────────────────────────────────────

    @agent
    def market_researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["market_researcher"],  # type: ignore[index]
            llm=_build_llm(),
            verbose=True,
        )

    @agent
    def app_store_copywriter(self) -> Agent:
        return Agent(
            config=self.agents_config["app_store_copywriter"],  # type: ignore[index]
            llm=_build_llm(),
            verbose=True,
        )

    @agent
    def aso_specialist(self) -> Agent:
        return Agent(
            config=self.agents_config["aso_specialist"],  # type: ignore[index]
            llm=_build_llm(),
            verbose=True,
        )

    @agent
    def legal_reviewer(self) -> Agent:
        return Agent(
            config=self.agents_config["legal_reviewer"],  # type: ignore[index]
            llm=_build_llm(),
            verbose=True,
        )

    # ── Tasks ────────────────────────────────────────────────────────

    @task
    def market_research(self) -> Task:
        return Task(config=self.tasks_config["market_research"])  # type: ignore[index]

    @task
    def app_store_copy(self) -> Task:
        return Task(config=self.tasks_config["app_store_copy"])  # type: ignore[index]

    @task
    def aso_optimization(self) -> Task:
        return Task(config=self.tasks_config["aso_optimization"])  # type: ignore[index]

    @task
    def legal_review(self) -> Task:
        return Task(config=self.tasks_config["legal_review"])  # type: ignore[index]

    # ── Crew Assembly ────────────────────────────────────────────────

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )

