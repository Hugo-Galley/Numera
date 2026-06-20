---
name: numera-testing
description: Comprehensive testing and validation procedures for the Numera project. Use this skill when you need to verify code changes, debug backend issues, or ensure the application builds correctly before committing.
---

# Numera Testing & Validation

This skill defines the exact procedures to follow to ensure that modifications to Numera are correct and don't introduce regressions.

## 1. The "Golden Rule" of Validation
Always run the full validation suite before considering a task complete:
```bash
make validate
```
This command runs both the backend tests and the frontend build.

## 2. Backend Testing (Pytest)

### Running All Tests
From the project root:
```bash
cd backend && PYTHONPATH=. ./venv/bin/pytest tests/
```
*Note: Adjust the path to `./venv/bin/pytest` or `./venv_new/bin/pytest` depending on which one is available and functional.*

### Running a Specific Test File
```bash
cd backend && PYTHONPATH=. ./venv/bin/pytest tests/test_merchants.py
```
Or `test_data_audit.py`.

### Critical Verification Points
- **Running Balances**: After any transaction creation/update, verify that the `running_balance` in the database is consistent.
- **Currency Conversion**: Verify that `original_amount` is preserved and `amount` is correctly converted to the account's currency.
- **Audit Center**: After a fix, verify that the `/analytics/actions` endpoint no longer returns the resolved issue.
- **Merchant Normalization**: Verify that transactions correctly bind to `merchant_id` and can be auto-normalized without altering original bank labels.
- **Salary/TT Generation**: Verify that `generate_salary_transactions` computes correct amounts for net salary and ticket restaurants and marks the salary month as generated.
- **Account Verification**: Verify that accounts save the correct `last_verified_at` timestamp.

## 3. Frontend Validation

### Build Verification
Since there is no automated test runner for the frontend yet, the primary validation is ensuring the project builds without TypeScript or Vite errors:
```bash
cd frontend && npm run build
```

### Manual UI Verification
- **Privacy Mode**: Toggle the eye icon and verify that sensitive amounts are blurred.
- **Toast Notifications**: Ensure every action (save, delete, import) triggers a clear success or error message.

## 4. Troubleshooting Common Testing Issues

### ModuleNotFoundError: No module named 'app'
Always ensure `PYTHONPATH=.` is set when running `pytest` or scripts from within the `backend/` directory.

### Database Locking
If you get `sqlite3.OperationalError: database is locked`, ensure no other background process is holding a write lock on the test database.

### Auth Failures in Tests
Tests use a mock admin user. If a test fails with `401 Unauthorized`, ensure the `client` fixture in `conftest.py` is correctly overriding `get_current_user`.

## 5. Adding New Tests
When adding a feature, create a corresponding `test_*.py` in `backend/tests/`. 
Use the `client` and `db_session` fixtures to perform isolated API calls.
