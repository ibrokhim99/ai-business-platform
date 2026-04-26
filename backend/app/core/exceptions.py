from fastapi import HTTPException, status


class ModelNotFoundError(HTTPException):
    def __init__(self, model_id: str):
        super().__init__(status_code=404, detail=f"Model '{model_id}' not found in registry.")


class PredictionError(HTTPException):
    def __init__(self, model_id: str, detail: str):
        super().__init__(status_code=500, detail=f"Prediction failed for '{model_id}': {detail}")


class AuthError(HTTPException):
    def __init__(self, detail: str = "Could not validate credentials"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ForbiddenError(HTTPException):
    def __init__(self, detail: str = "Insufficient permissions"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
