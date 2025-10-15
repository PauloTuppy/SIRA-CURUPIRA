"""
Custom exceptions for the SIRA Backend Service
"""

from datetime import datetime
from typing import Any, Dict, Optional
from uuid import uuid4


class SIRAException(Exception):
    """
    Base exception class for SIRA Backend Service
    """
    
    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize SIRA exception
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            status_code: HTTP status code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        self.timestamp = datetime.utcnow()
        self.error_id = str(uuid4())
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_id": self.error_id,
            "error_code": self.error_code,
            "message": self.message,
            "status_code": self.status_code,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }


class ValidationError(SIRAException):
    """
    Exception for validation errors
    """
    
    def __init__(
        self,
        message: str = "Dados de entrada inválidos",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=422,
            details=details
        )


class AuthenticationError(SIRAException):
    """
    Exception for authentication errors
    """
    
    def __init__(
        self,
        message: str = "Falha na autenticação",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401,
            details=details
        )


class AuthorizationError(SIRAException):
    """
    Exception for authorization errors
    """
    
    def __init__(
        self,
        message: str = "Acesso negado",
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message=message,
            error_code="AUTHORIZATION_ERROR",
            status_code=403,
            details=details
        )


class NotFoundError(SIRAException):
    """
    Exception for resource not found errors
    """
    
    def __init__(
        self,
        message: str = "Recurso não encontrado",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
            
        super().__init__(
            message=message,
            error_code="NOT_FOUND_ERROR",
            status_code=404,
            details=details
        )


class ServiceError(SIRAException):
    """
    Exception for external service errors
    """
    
    def __init__(
        self,
        message: str = "Erro no serviço externo",
        service_name: Optional[str] = None,
        original_error: Optional[str] = None
    ):
        details = {}
        if service_name:
            details["service_name"] = service_name
        if original_error:
            details["original_error"] = original_error
            
        super().__init__(
            message=message,
            error_code="SERVICE_ERROR",
            status_code=502,
            details=details
        )


class RateLimitError(SIRAException):
    """
    Exception for rate limit errors
    """
    
    def __init__(
        self,
        message: str = "Limite de taxa excedido",
        retry_after: Optional[int] = None
    ):
        details = {}
        if retry_after:
            details["retry_after"] = retry_after
            
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_ERROR",
            status_code=429,
            details=details
        )


class FileProcessingError(SIRAException):
    """
    Exception for file processing errors
    """
    
    def __init__(
        self,
        message: str = "Erro no processamento do arquivo",
        filename: Optional[str] = None,
        file_type: Optional[str] = None
    ):
        details = {}
        if filename:
            details["filename"] = filename
        if file_type:
            details["file_type"] = file_type
            
        super().__init__(
            message=message,
            error_code="FILE_PROCESSING_ERROR",
            status_code=422,
            details=details
        )


class AnalysisError(SIRAException):
    """
    Exception for analysis processing errors
    """
    
    def __init__(
        self,
        message: str = "Erro na análise",
        analysis_id: Optional[str] = None,
        agent_name: Optional[str] = None,
        stage: Optional[str] = None
    ):
        details = {}
        if analysis_id:
            details["analysis_id"] = analysis_id
        if agent_name:
            details["agent_name"] = agent_name
        if stage:
            details["stage"] = stage
            
        super().__init__(
            message=message,
            error_code="ANALYSIS_ERROR",
            status_code=500,
            details=details
        )


class ConfigurationError(SIRAException):
    """
    Exception for configuration errors
    """
    
    def __init__(
        self,
        message: str = "Erro de configuração",
        config_key: Optional[str] = None
    ):
        details = {}
        if config_key:
            details["config_key"] = config_key
            
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class DatabaseError(SIRAException):
    """
    Exception for database errors
    """
    
    def __init__(
        self,
        message: str = "Erro no banco de dados",
        operation: Optional[str] = None,
        collection: Optional[str] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if collection:
            details["collection"] = collection
            
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class TimeoutError(SIRAException):
    """
    Exception for timeout errors
    """
    
    def __init__(
        self,
        message: str = "Operação expirou",
        operation: Optional[str] = None,
        timeout_seconds: Optional[float] = None
    ):
        details = {}
        if operation:
            details["operation"] = operation
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
            
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            status_code=408,
            details=details
        )


class ResourceExhaustedError(SIRAException):
    """
    Exception for resource exhaustion errors
    """
    
    def __init__(
        self,
        message: str = "Recursos esgotados",
        resource_type: Optional[str] = None
    ):
        details = {}
        if resource_type:
            details["resource_type"] = resource_type
            
        super().__init__(
            message=message,
            error_code="RESOURCE_EXHAUSTED_ERROR",
            status_code=503,
            details=details
        )
