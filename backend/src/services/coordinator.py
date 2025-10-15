"""
Coordinator Service - Manages the multi-agent system
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

import structlog
from google.cloud import firestore

from ..agents import (
    CoordinatorAgent,
    ImageAnalysisAgent,
    EcosystemBalanceAgent,
    RecoveryPlanAgent
)
from ..config import settings
from ..models.analysis import AnalysisResponse, AnalysisStatus, AnalysisProgress
from ..utils.exceptions import AnalysisError, ServiceError, ConfigurationError


class CoordinatorService:
    """
    Service that coordinates the multi-agent analysis system
    """
    
    def __init__(self):
        self.logger = structlog.get_logger("service.coordinator")
        
        # Firestore client
        self.db = None
        
        # Agent instances
        self.coordinator_agent = None
        self.image_analysis_agent = None
        self.ecosystem_balance_agent = None
        self.recovery_plan_agent = None
        
        # Active analyses tracking
        self.active_analyses: Dict[UUID, AnalysisResponse] = {}
        
        # Service status
        self.is_initialized = False
        self.initialization_error = None
    
    async def initialize(self):
        """
        Initialize the coordinator service and all agents
        """
        try:
            self.logger.info("Initializing coordinator service")
            
            # Initialize Firestore
            self.db = firestore.AsyncClient(
                project=settings.google_cloud_project,
                database=settings.firestore_database
            )
            
            # Initialize agents
            await self._initialize_agents()
            
            # Configure agent relationships
            self.coordinator_agent.set_agents(
                self.image_analysis_agent,
                self.ecosystem_balance_agent,
                self.recovery_plan_agent
            )
            
            self.is_initialized = True
            self.logger.info("Coordinator service initialized successfully")
            
        except Exception as e:
            self.initialization_error = str(e)
            self.logger.error(
                "Failed to initialize coordinator service",
                error=str(e),
                exc_info=True
            )
            raise ConfigurationError(
                message=f"Coordinator service initialization failed: {str(e)}"
            )
    
    async def _initialize_agents(self):
        """Initialize all agent instances"""
        try:
            # Create agent instances
            self.coordinator_agent = CoordinatorAgent()
            self.image_analysis_agent = ImageAnalysisAgent()
            self.ecosystem_balance_agent = EcosystemBalanceAgent()
            self.recovery_plan_agent = RecoveryPlanAgent()
            
            # Perform health checks
            agents = [
                self.coordinator_agent,
                self.image_analysis_agent,
                self.ecosystem_balance_agent,
                self.recovery_plan_agent
            ]
            
            health_checks = await asyncio.gather(
                *[agent.health_check() for agent in agents],
                return_exceptions=True
            )
            
            for i, health in enumerate(health_checks):
                if isinstance(health, Exception):
                    raise ServiceError(
                        message=f"Agent {agents[i].name} health check failed",
                        service_name=agents[i].name,
                        original_error=str(health)
                    )
            
            self.logger.info("All agents initialized and healthy")
            
        except Exception as e:
            self.logger.error("Agent initialization failed", error=str(e))
            raise
    
    async def start_analysis(
        self,
        request_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> AnalysisResponse:
        """
        Start a new analysis
        
        Args:
            request_data: Analysis request data
            user_id: Optional user ID
            
        Returns:
            Analysis response with tracking information
        """
        if not self.is_initialized:
            raise ServiceError(
                message="Coordinator service not initialized",
                service_name="coordinator"
            )
        
        analysis_id = uuid4()
        
        # Create analysis response
        analysis_response = AnalysisResponse(
            analysis_id=analysis_id,
            status=AnalysisStatus.PENDING,
            filename=request_data.get("filename", "unknown"),
            coordinates=request_data.get("coordinates")
        )
        
        # Store in active analyses
        self.active_analyses[analysis_id] = analysis_response
        
        # Store in Firestore
        await self._store_analysis(analysis_response, user_id)
        
        # Start processing asynchronously
        asyncio.create_task(
            self._process_analysis(analysis_id, request_data, user_id)
        )
        
        self.logger.info(
            "Analysis started",
            analysis_id=str(analysis_id),
            filename=request_data.get("filename"),
            user_id=user_id
        )
        
        return analysis_response
    
    async def _process_analysis(
        self,
        analysis_id: UUID,
        request_data: Dict[str, Any],
        user_id: Optional[str] = None
    ):
        """
        Process analysis asynchronously
        
        Args:
            analysis_id: Analysis ID
            request_data: Request data
            user_id: Optional user ID
        """
        analysis_response = self.active_analyses.get(analysis_id)
        if not analysis_response:
            self.logger.error("Analysis not found", analysis_id=str(analysis_id))
            return
        
        try:
            # Update status to processing
            analysis_response.status = AnalysisStatus.PROCESSING
            analysis_response.updated_at = datetime.utcnow()
            
            await self._update_analysis_progress(
                analysis_id,
                AnalysisProgress(
                    analysis_id=analysis_id,
                    status=AnalysisStatus.PROCESSING,
                    progress_percentage=10.0,
                    current_step="Iniciando análise coordenada",
                    message="Preparando agentes especializados"
                )
            )
            
            # Process with coordinator agent
            coordinator_response = await self.coordinator_agent.process(
                request_data, analysis_id
            )
            
            if coordinator_response.status.value == "completed":
                # Success
                analysis_response.status = AnalysisStatus.COMPLETED
                analysis_response.result = coordinator_response.data
                analysis_response.processing_time = coordinator_response.processing_time_seconds
                analysis_response.agent_responses = coordinator_response.metadata.get("agent_responses")
                
                await self._update_analysis_progress(
                    analysis_id,
                    AnalysisProgress(
                        analysis_id=analysis_id,
                        status=AnalysisStatus.COMPLETED,
                        progress_percentage=100.0,
                        current_step="Análise concluída",
                        message="Resultados disponíveis"
                    )
                )
                
                self.logger.info(
                    "Analysis completed successfully",
                    analysis_id=str(analysis_id),
                    processing_time=coordinator_response.processing_time_seconds
                )
                
            else:
                # Failed
                analysis_response.status = AnalysisStatus.FAILED
                analysis_response.error_message = coordinator_response.error_message
                
                await self._update_analysis_progress(
                    analysis_id,
                    AnalysisProgress(
                        analysis_id=analysis_id,
                        status=AnalysisStatus.FAILED,
                        progress_percentage=0.0,
                        current_step="Análise falhou",
                        message=coordinator_response.error_message,
                        error_message=coordinator_response.error_message
                    )
                )
                
                self.logger.error(
                    "Analysis failed",
                    analysis_id=str(analysis_id),
                    error=coordinator_response.error_message
                )
            
        except Exception as e:
            # Handle unexpected errors
            analysis_response.status = AnalysisStatus.FAILED
            analysis_response.error_message = str(e)
            
            await self._update_analysis_progress(
                analysis_id,
                AnalysisProgress(
                    analysis_id=analysis_id,
                    status=AnalysisStatus.FAILED,
                    progress_percentage=0.0,
                    current_step="Erro inesperado",
                    message="Falha no processamento",
                    error_message=str(e)
                )
            )
            
            self.logger.error(
                "Unexpected analysis error",
                analysis_id=str(analysis_id),
                error=str(e),
                exc_info=True
            )
        
        finally:
            # Update final status in Firestore
            analysis_response.updated_at = datetime.utcnow()
            await self._store_analysis(analysis_response, user_id)
            
            # Clean up from active analyses after some time
            await asyncio.sleep(300)  # Keep for 5 minutes
            self.active_analyses.pop(analysis_id, None)
    
    async def get_analysis(self, analysis_id: UUID) -> Optional[AnalysisResponse]:
        """
        Get analysis by ID
        
        Args:
            analysis_id: Analysis ID
            
        Returns:
            Analysis response or None if not found
        """
        # Check active analyses first
        if analysis_id in self.active_analyses:
            return self.active_analyses[analysis_id]
        
        # Check Firestore
        try:
            doc_ref = self.db.collection(settings.analyses_collection).document(str(analysis_id))
            doc = await doc_ref.get()
            
            if doc.exists:
                data = doc.to_dict()
                return AnalysisResponse(**data)
            
        except Exception as e:
            self.logger.error(
                "Failed to retrieve analysis",
                analysis_id=str(analysis_id),
                error=str(e)
            )
        
        return None
    
    async def _store_analysis(
        self,
        analysis_response: AnalysisResponse,
        user_id: Optional[str] = None
    ):
        """Store analysis in Firestore"""
        try:
            doc_ref = self.db.collection(settings.analyses_collection).document(
                str(analysis_response.analysis_id)
            )
            
            data = analysis_response.dict()
            if user_id:
                data["user_id"] = user_id
            
            await doc_ref.set(data, merge=True)
            
        except Exception as e:
            self.logger.error(
                "Failed to store analysis",
                analysis_id=str(analysis_response.analysis_id),
                error=str(e)
            )
    
    async def _update_analysis_progress(
        self,
        analysis_id: UUID,
        progress: AnalysisProgress
    ):
        """Update analysis progress"""
        # Update in active analyses
        if analysis_id in self.active_analyses:
            self.active_analyses[analysis_id].progress = progress
        
        # Store progress update in Firestore
        try:
            doc_ref = self.db.collection(settings.analyses_collection).document(str(analysis_id))
            await doc_ref.update({"progress": progress.dict()})
            
        except Exception as e:
            self.logger.warning(
                "Failed to update analysis progress",
                analysis_id=str(analysis_id),
                error=str(e)
            )
    
    async def health_check(self) -> Dict[str, Any]:
        """
        Perform service health check
        
        Returns:
            Health status information
        """
        if not self.is_initialized:
            return {
                "status": "unhealthy",
                "error": self.initialization_error or "Not initialized",
                "agents": {}
            }
        
        try:
            # Check all agents
            agent_health = {}
            agents = [
                self.coordinator_agent,
                self.image_analysis_agent,
                self.ecosystem_balance_agent,
                self.recovery_plan_agent
            ]
            
            for agent in agents:
                if agent:
                    agent_health[agent.name] = await agent.health_check()
                else:
                    agent_health[f"unknown_agent"] = {"status": "not_initialized"}
            
            return {
                "status": "healthy",
                "initialized": self.is_initialized,
                "active_analyses": len(self.active_analyses),
                "agents": agent_health
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "agents": {}
            }
    
    async def cleanup(self):
        """Cleanup service resources"""
        self.logger.info("Cleaning up coordinator service")
        
        # Cancel active analyses
        for analysis_id in list(self.active_analyses.keys()):
            analysis = self.active_analyses[analysis_id]
            if analysis.status in [AnalysisStatus.PENDING, AnalysisStatus.PROCESSING]:
                analysis.status = AnalysisStatus.CANCELLED
                analysis.updated_at = datetime.utcnow()
        
        # Close Firestore client
        if self.db:
            self.db.close()
        
        self.is_initialized = False
        self.logger.info("Coordinator service cleanup completed")
