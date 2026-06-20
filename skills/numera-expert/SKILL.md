---
name: numera-expert
description: Specialized guidance for developing and maintaining the Numera personal finance application. Use this skill when working on backend API, frontend React components, or data integrity tasks within the Numera repository.
---

# Numera Expert Skill

This skill provides the comprehensive procedural knowledge required to develop, test, and maintain the Numera project.

## Core Workflows

### 1. Backend Development
- **Models**: Defined in `backend/app/models/`. Use SQLAlchemy 2.0 syntax.
- **Schemas**: Defined in `backend/app/schemas/`. Use Pydantic v2.
- **API**: Implement endpoints in `backend/app/api/`.
- **Validation**: Run `cd backend && PYTHONPATH=. pytest`.

### 2. Frontend Development
- **Pages**: Located in `frontend/src/pages/`.
- **Components**: UI components in `frontend/src/components/ui/`.
- **API Calls**: Always use `apiFetch` from `@/lib/api`.
- **Styling**: Tailwind CSS.

### 3. Financial Logic & Features
- **Currency**: Always use the conversion logic in `backend/app/core/currency.py`.
- **Running Balance**: Must be updated whenever transactions are modified.
- **Merchant Normalization**: Link transactions to canonical `Merchant` names via `merchant_id` using `MerchantAlias` patterns to simplify visualizations without altering original bank labels.
- **Salary & TT Calendar**: Manage net salary configurations with `SalaryConfig`. Log telecommuting days (`TelecommutingDay`) to auto-compute and generate salary and ticket restaurant transactions.
- **Account Verification**: Keep `last_verified_at` updated to audit balances periodically.

## Reference Documentation
For detailed rules, refer to the following files in the repository:
- `GEMINI.md`: Global standards and architecture.
- `backend/GEMINI.md`: Detailed backend development rules.
- `frontend/src/GEMINI.md`: Detailed frontend development rules.
- `ARCHITECTURE.md`: High-level system design.
- `docs/ACTION_CENTER.md`: Guide for the Action Center and audits.

## Essential Commands
- **Test Backend**: `cd backend && PYTHONPATH=. pytest`
- **Build Frontend**: `cd frontend && npm run build`
- **Run Migrations**: `cd backend && alembic upgrade head`
