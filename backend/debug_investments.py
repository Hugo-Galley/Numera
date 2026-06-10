from app.db.session import SessionLocal
from app.api.analytics import investments_analytics
from datetime import datetime
import asyncio
import json

async def main():
    db = SessionLocal()
    # Mocking May 2026
    month = 5
    year = 2026
    
    print(f"DEBUG: Running investments_analytics for {month}/{year}")
    try:
        result = await investments_analytics(month=month, year=year, db=db)
        print("RESULT:")
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    asyncio.run(main())
