class AppError(Exception):
    def __init__(self, message: str, code: str = "APP_ERROR"):
        self.message = message
        self.code = code
        super().__init__(message)


class DatabaseError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "DB_ERROR")


class AIError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "AI_ERROR")


class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")
