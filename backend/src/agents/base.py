"""
Base agent class and common interfaces for SIRA agents
"""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field
import structlog

from ..utils.exceptions import AnalysisError, ServiceError, TimeoutError


class AgentStatus(str, Enum):
    """Agent status enumeration"""
    IDLE = "idle"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class AgentResponse(BaseModel):
    """Standard agent response model"""
    agent_name: str = Field(..., description="Nome do agente")
    agent_version: str = Field(default="1.0.0", description="Versão do agente")
    request_id: UUID = Field(..., description="ID da requisição")
    status: AgentStatus = Field(..., description="Status da resposta")
    
    # Timing information
    started_at: datetime = Field(..., description="Timestamp de início")
    completed_at: Optional[datetime] = Field(None, description="Timestamp de conclusão")
    processing_time_seconds: Optional[float] = Field(None, description="Tempo de processamento")
    
    # Response data
    data: Optional[Dict[str, Any]] = Field(None, description="Dados da resposta")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadados adicionais")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
    error_code: Optional[str] = Field(None, description="Código do erro")
    
    # Confidence and quality metrics
    confidence_score: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Score de confiança (0-1)"
    )
    quality_metrics: Optional[Dict[str, float]] = Field(
        None, 
        description="Métricas de qualidade"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }


class BaseAgent(ABC):
    """
    Base class for all SIRA agents
    """
    
    def __init__(
        self,
        name: str,
        version: str = "1.0.0",
        timeout_seconds: float = 300.0,
        max_retries: int = 3
    ):
        """
        Initialize base agent
        
        Args:
            name: Agent name
            version: Agent version
            timeout_seconds: Processing timeout
            max_retries: Maximum retry attempts
        """
        self.name = name
        self.version = version
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.logger = structlog.get_logger(f"agent.{name}")
        self._status = AgentStatus.IDLE
        self._current_request_id: Optional[UUID] = None
        
    @property
    def status(self) -> AgentStatus:
        """Get current agent status"""
        return self._status
    
    @property
    def is_available(self) -> bool:
        """Check if agent is available for processing"""
        return self._status == AgentStatus.IDLE
    
    async def process(
        self,
        request_data: Dict[str, Any],
        request_id: Optional[UUID] = None
    ) -> AgentResponse:
        """
        Process a request with timeout and retry logic
        
        Args:
            request_data: Request data to process
            request_id: Optional request ID
            
        Returns:
            Agent response
            
        Raises:
            AnalysisError: If processing fails
            TimeoutError: If processing times out
        """
        if request_id is None:
            request_id = uuid4()
            
        self._current_request_id = request_id
        started_at = datetime.utcnow()
        
        self.logger.info(
            "Starting agent processing",
            request_id=str(request_id),
            agent_name=self.name
        )
        
        # Update status
        self._status = AgentStatus.PROCESSING
        
        try:
            # Process with timeout
            response_data = await asyncio.wait_for(
                self._process_with_retry(request_data, request_id),
                timeout=self.timeout_seconds
            )
            
            completed_at = datetime.utcnow()
            processing_time = (completed_at - started_at).total_seconds()
            
            # Create successful response
            response = AgentResponse(
                agent_name=self.name,
                agent_version=self.version,
                request_id=request_id,
                status=AgentStatus.COMPLETED,
                started_at=started_at,
                completed_at=completed_at,
                processing_time_seconds=processing_time,
                data=response_data.get("data"),
                metadata=response_data.get("metadata"),
                confidence_score=response_data.get("confidence_score"),
                quality_metrics=response_data.get("quality_metrics")
            )
            
            self.logger.info(
                "Agent processing completed",
                request_id=str(request_id),
                processing_time=processing_time,
                confidence_score=response.confidence_score
            )
            
            self._status = AgentStatus.COMPLETED
            return response
            
        except asyncio.TimeoutError:
            self._status = AgentStatus.TIMEOUT
            error_msg = f"Agent {self.name} processing timed out after {self.timeout_seconds}s"
            
            self.logger.error(
                "Agent processing timeout",
                request_id=str(request_id),
                timeout_seconds=self.timeout_seconds
            )
            
            return AgentResponse(
                agent_name=self.name,
                agent_version=self.version,
                request_id=request_id,
                status=AgentStatus.TIMEOUT,
                started_at=started_at,
                error_message=error_msg,
                error_code="AGENT_TIMEOUT"
            )
            
        except Exception as e:
            self._status = AgentStatus.FAILED
            error_msg = f"Agent {self.name} processing failed: {str(e)}"
            
            self.logger.error(
                "Agent processing failed",
                request_id=str(request_id),
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            
            return AgentResponse(
                agent_name=self.name,
                agent_version=self.version,
                request_id=request_id,
                status=AgentStatus.FAILED,
                started_at=started_at,
                error_message=error_msg,
                error_code="AGENT_PROCESSING_ERROR"
            )
            
        finally:
            # Reset status to idle
            self._status = AgentStatus.IDLE
            self._current_request_id = None
    
    async def _process_with_retry(
        self,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Process request with retry logic
        
        Args:
            request_data: Request data
            request_id: Request ID
            
        Returns:
            Processing result
        """
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                self.logger.debug(
                    "Processing attempt",
                    request_id=str(request_id),
                    attempt=attempt + 1,
                    max_retries=self.max_retries
                )
                
                result = await self._process_request(request_data, request_id)
                return result
                
            except Exception as e:
                last_error = e
                
                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    
                    self.logger.warning(
                        "Processing attempt failed, retrying",
                        request_id=str(request_id),
                        attempt=attempt + 1,
                        error=str(e),
                        wait_time=wait_time
                    )
                    
                    await asyncio.sleep(wait_time)
                else:
                    self.logger.error(
                        "All processing attempts failed",
                        request_id=str(request_id),
                        attempts=self.max_retries,
                        final_error=str(e)
                    )
        
        # If we get here, all retries failed
        raise AnalysisError(
            message=f"Agent {self.name} failed after {self.max_retries} attempts",
            analysis_id=str(request_id),
            agent_name=self.name
        ) from last_error
    
    @abstractmethod
    async def _process_request(
        self,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Abstract method for processing requests
        
        Args:
            request_data: Request data to process
            request_id: Request ID
            
        Returns:
            Processing result dictionary with keys:
            - data: Main response data
            - metadata: Optional metadata
            - confidence_score: Optional confidence score (0-1)
            - quality_metrics: Optional quality metrics
        """
        pass
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform agent health check
        
        Returns:
            Health status information
        """
        return {
            "agent_name": self.name,
            "version": self.version,
            "status": self.status.value,
            "is_available": self.is_available,
            "current_request_id": str(self._current_request_id) if self._current_request_id else None,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries
        }
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self.name}', version='{self.version}', status='{self.status.value}')"
