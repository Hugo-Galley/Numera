from fastapi import HTTPException


def api_error(status_code: int, code: str, detail: str, context: dict | None = None) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={
            "code": code,
            "detail": detail,
            "context": context or {},
        },
    )
