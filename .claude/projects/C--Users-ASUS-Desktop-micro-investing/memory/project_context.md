# Project Context

## Overview
Micro-investing application with Next.js frontend and Python FastAPI backend. The application helps users set financial goals, track investments, and get AI-powered financial advice.

## Architecture
- Frontend: Next.js 16.2.4 with TypeScript, Turbopack, Recharts for data visualization
- Backend: Python FastAPI with SQLAlchemy + SQLite
- Data flow: Onboarding → Financial profile stored in DB → `/users/analysis` endpoint returns full analysis
- localStorage used to cache `user_analysis` for frontend speed

## Key Components
- Goals page: Displays financial goals and progress tracking
- Analysis page: Shows expense breakdown and financial analysis
- Dashboard: Overview of financial health, alerts, and recommendations
- AI Chat: Conversational interface for financial advice
- Onboarding: User setup flow for financial profile creation

## Data Models
- OnboardResponse: Basic user info from `/users/onboard-financial` endpoint
- AnalyzeUserResponse: Full analysis data from `/users/analysis` endpoint including:
  - expense_summary
  - financial_snapshot
  - health_score
  - risk_metrics
  - ai_insights