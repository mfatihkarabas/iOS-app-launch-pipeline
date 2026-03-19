# 🍎 iOS Software Factory

A **crewAI**-powered multi-agent pipeline that transforms a feature idea into a fully analyzed, implemented, tested, and release-reviewed iOS deliverable.

## Architecture

```
User Idea
    │
    ▼
┌─────────────────────┐
│  iOS Systems Analyst │  ← Technical Study Document (TSD)
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ Lead iOS Developer   │  ← Swift / SpriteKit implementation
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  iOS QA SDET         │  ← XCTest, Instruments verification
└────────┬────────────┘
         ▼
┌─────────────────────┐
│  Product Owner       │  ← Release readiness audit
└─────────────────────┘
```

## Quick Start

### Prerequisites
- Python 3.11+
- A GitHub Copilot subscription (or an OpenAI API key)

### 1 – Get your GitHub Token (Copilot users)

1. Go to **https://github.com/settings/tokens**
2. Click **Generate new token (classic)**
3. Give it any name (no special scopes required)
4. Copy the token

### 2 – Configure environment

```bash
cp .env.example .env
# Open .env and paste your token:
#   GITHUB_TOKEN=github_pat_...
#   GITHUB_MODEL=gpt-4o          # or gpt-4o-mini for faster/cheaper runs
```

### 3 – Install dependencies

```bash
# Using the crewAI CLI (recommended)
crewai install

# Or manually with pip
pip install -e .
```

### 4 – Run the pipeline

```bash
crewai run
# or
python -m ios_factory.main
```

## Project Structure

```
src/ios_factory/
├── config/
│   ├── agents.yaml    # Agent personas (Product Owner, Analyst, Dev, QA)
│   └── tasks.yaml     # Task definitions & handover protocol
├── crew.py            # Crew orchestration (sequential pipeline)
├── main.py            # CLI entry point
└── __init__.py
```

## Agent Roles

| Agent | Role | Focus |
|-------|------|-------|
| **Product Owner** | iOS Product Strategist | Apple HIG alignment, App Store readiness |
| **Systems Analyst** | Senior iOS Architect | TSD creation, state machines, ARC strategy |
| **Lead Developer** | Swift & SpriteKit Engineer | 60/120 FPS code, Clean Architecture |
| **QA SDET** | Test Automation Engineer | XCTest, Instruments, retain cycle detection |

## Excellence Guardrails

- **16ms Budget**: No `update(_:)` call may exceed 16ms (60 FPS guarantee)
- **Retain Cycle Audit**: Mandatory in every QA verification pass
- **State Diagrams**: Required for all interactive game elements
- **Protocol-Oriented Design**: All implementations must be testable via protocols

## License

Private – All rights reserved.
