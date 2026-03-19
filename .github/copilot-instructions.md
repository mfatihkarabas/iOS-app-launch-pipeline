# iOS Software Factory – Copilot Instructions

This is a **crewAI**-based multi-agent project for iOS feature development.

## Project Overview
- **Framework:** crewAI (Python)
- **Target Platform:** iOS (Swift, SpriteKit)
- **Architecture:** Multi-agent pipeline with YAML-configured personas and tasks

## Agent Pipeline
1. **Product Owner** → Strategic alignment with Apple HIG
2. **iOS Systems Analyst** → Technical Study Document (TSD) creation
3. **Lead iOS Developer** → Swift/SpriteKit implementation
4. **iOS QA SDET** → XCTest, Instruments, performance verification

## Conventions
- Agent definitions live in `src/ios_factory/config/agents.yaml`
- Task definitions live in `src/ios_factory/config/tasks.yaml`
- Crew orchestration is in `src/ios_factory/crew.py`
- Entry point is `src/ios_factory/main.py`
- All feature ideas are passed via the `{user_idea}` placeholder
- Python 3.11+ required
