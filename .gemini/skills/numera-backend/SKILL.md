---
name: numera-backend
description: Expert backend development standards for Numera (FastAPI, SQLAlchemy, Pydantic). Use this skill when creating new API endpoints, modifying database models, or implementing financial logic in the backend.
---

# Numera Backend Development Standards

This skill defines the rigorous standards for backend development in the Numera project.

## 1. FastAPI Endpoint Structure
- **Router**: Always use `APIRouter` with a semantic `prefix` and `tags`.
- **Dependency Injection**: 
    - Use `db: Session = Depends(get_db)` for database access.
    - Use `current_user = Depends(get_current_user)` for protected routes.
- **Async/Await**: 
    - Use `async def` for endpoints, especially when calling other async functions (like exchange rate fetches).
    - Use synchronous `def` only for purely CPU-bound logic or simple CRUD that doesn't benefit from async.
- **Response Models**: Always define `response_model` to ensure data validation and documentation.

## 2. Database & SQLAlchemy (2.0+)
- **Models**: Use `Mapped` and `mapped_column`.
- **Queries**:
    - Prefer the `db.query(Model)` syntax (or `select(Model)` in newer parts).
    - Use `.first()` or `.all()` explicitly.
    - Use `.scalar()` for counts or single value results.
- **Transactions**: 
    - Always `db.commit()` after mutations.
    - Use `db.refresh(obj)` if you need the updated object (e.g., after ID generation).
- **Recalculation**: If modifying transactions, you MUST call `recalculate_running_balances(db, account_id)`.

## 3. Pydantic Schemas (v2)
- **Separation**: Create separate schemas for `Create`, `Update`, and `Read`.
- **Validation**: Use `Field` for constraints (min/max, descriptions).
- **ORM Mode**: Ensure `model_config = ConfigDict(from_attributes=True)` is set for Read schemas.

## 4. Financial Logic Integrity
- **Currency Conversion**:
    - Never assume 1:1 conversion.
    - Use `app.core.currency.convert_amount` for on-the-fly conversion.
    - Store `amount` (converted to account currency) and `original_amount` + `currency` (saisie originale).
- **Transaction Sens**: 
    - `Entree` / `Interets` are positive.
    - `Sortie` is negative.
    - `Solde Initial` is a reset point.

## 5. Error Handling
- **HTTPException**: Always use `fastapi.HTTPException` with clear status codes.
    - `404`: Not Found.
    - `400`: Bad Request (business logic violation).
    - `401`: Unauthorized.
- **Traceability**: Log errors before raising if they are unexpected or critical.

## 6. What NOT to do
- **❌ No direct DB execution**: Do not use `db.execute(text("..."))` unless absolutely necessary for performance optimization on complex queries.
- **❌ No logic in models**: Keep models as data structures. Logic goes in `app/core/` or `app/api/`.
- **❌ No secret leaks**: Never log or return sensitive data like password hashes or secret keys.
- **❌ No N+1 queries**: Use `joinedload` or `subqueryload` when fetching related objects in lists.
