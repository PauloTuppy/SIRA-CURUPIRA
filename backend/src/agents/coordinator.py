"""
Coordinator Agent - Orchestrates the multi-agent analysis workflow
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog
from google.generativeai import GenerativeModel
import google.generativeai as genai

from .base import BaseAgent, AgentResponse, AgentStatus
from ..config import settings
from ..models.analysis import AnalysisResult, InvasiveSpecies, RiskLevel, ViabilityLevel
from ..utils.exceptions import AnalysisError, ServiceError


class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent that orchestrates the analysis workflow
    Uses Gemini Pro to coordinate between specialized agents
    """
    
    def __init__(self):
        super().__init__(
            name="coordinator",
            version="1.0.0",
            timeout_seconds=600.0,  # 10 minutes for full analysis
            max_retries=2
        )
        
        # Initialize Gemini Pro
        genai.configure(api_key=settings.gemini_api_key)
        self.model = GenerativeModel(settings.coordinator_model)
        
        # Agent references (will be injected)
        self.image_analysis_agent = None
        self.ecosystem_balance_agent = None
        self.recovery_plan_agent = None
        
        self.logger = structlog.get_logger("agent.coordinator")
    
    def set_agents(
        self,
        image_analysis_agent,
        ecosystem_balance_agent,
        recovery_plan_agent
    ):
        """
        Inject specialized agent references
        
        Args:
            image_analysis_agent: Image analysis agent instance
            ecosystem_balance_agent: Ecosystem balance agent instance
            recovery_plan_agent: Recovery plan agent instance
        """
        self.image_analysis_agent = image_analysis_agent
        self.ecosystem_balance_agent = ecosystem_balance_agent
        self.recovery_plan_agent = recovery_plan_agent
        
        self.logger.info("Specialized agents configured")
    
    async def _process_request(
        self,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Coordinate the multi-agent analysis workflow
        
        Args:
            request_data: Analysis request data
            request_id: Request ID
            
        Returns:
            Coordinated analysis result
        """
        self.logger.info(
            "Starting coordinated analysis",
            request_id=str(request_id),
            filename=request_data.get("filename")
        )
        
        # Validate required agents
        if not all([
            self.image_analysis_agent,
            self.ecosystem_balance_agent,
            self.recovery_plan_agent
        ]):
            raise AnalysisError(
                message="Specialized agents not configured",
                analysis_id=str(request_id),
                agent_name=self.name
            )
        
        # Step 1: Image Analysis (parallel with ecosystem analysis)
        self.logger.info("Step 1: Starting image analysis", request_id=str(request_id))
        
        image_task = asyncio.create_task(
            self.image_analysis_agent.process(request_data, request_id)
        )
        
        # Step 2: Ecosystem Balance Analysis (can run in parallel)
        self.logger.info("Step 2: Starting ecosystem analysis", request_id=str(request_id))
        
        ecosystem_task = asyncio.create_task(
            self.ecosystem_balance_agent.process(request_data, request_id)
        )
        
        # Wait for both analyses to complete
        try:
            image_response, ecosystem_response = await asyncio.gather(
                image_task, ecosystem_task, return_exceptions=True
            )
            
            # Handle potential exceptions
            if isinstance(image_response, Exception):
                self.logger.error(
                    "Image analysis failed",
                    request_id=str(request_id),
                    error=str(image_response)
                )
                raise AnalysisError(
                    message=f"Image analysis failed: {str(image_response)}",
                    analysis_id=str(request_id),
                    agent_name="image_analysis"
                )
            
            if isinstance(ecosystem_response, Exception):
                self.logger.error(
                    "Ecosystem analysis failed",
                    request_id=str(request_id),
                    error=str(ecosystem_response)
                )
                raise AnalysisError(
                    message=f"Ecosystem analysis failed: {str(ecosystem_response)}",
                    analysis_id=str(request_id),
                    agent_name="ecosystem_balance"
                )
            
        except Exception as e:
            self.logger.error(
                "Parallel analysis failed",
                request_id=str(request_id),
                error=str(e)
            )
            raise
        
        # Step 3: Synthesize results and prepare recovery plan input
        self.logger.info("Step 3: Synthesizing analysis results", request_id=str(request_id))
        
        synthesis_data = await self._synthesize_results(
            image_response, ecosystem_response, request_data, request_id
        )
        
        # Step 4: Recovery Plan Generation (depends on previous results)
        self.logger.info("Step 4: Generating recovery plan", request_id=str(request_id))
        
        recovery_input = {
            **request_data,
            "image_analysis": image_response.data,
            "ecosystem_analysis": ecosystem_response.data,
            "synthesis": synthesis_data
        }
        
        recovery_response = await self.recovery_plan_agent.process(
            recovery_input, request_id
        )
        
        if recovery_response.status != AgentStatus.COMPLETED:
            raise AnalysisError(
                message=f"Recovery plan generation failed: {recovery_response.error_message}",
                analysis_id=str(request_id),
                agent_name="recovery_plan"
            )
        
        # Step 5: Final coordination and result assembly
        self.logger.info("Step 5: Assembling final results", request_id=str(request_id))
        
        final_result = await self._assemble_final_result(
            image_response,
            ecosystem_response,
            recovery_response,
            synthesis_data,
            request_id
        )
        
        # Calculate overall confidence
        confidence_scores = [
            resp.confidence_score for resp in [image_response, ecosystem_response, recovery_response]
            if resp.confidence_score is not None
        ]
        
        overall_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else None
        
        self.logger.info(
            "Coordinated analysis completed",
            request_id=str(request_id),
            overall_confidence=overall_confidence,
            processing_steps=5
        )
        
        return {
            "data": final_result,
            "metadata": {
                "agent_responses": {
                    "image_analysis": image_response.dict(),
                    "ecosystem_balance": ecosystem_response.dict(),
                    "recovery_plan": recovery_response.dict()
                },
                "synthesis_data": synthesis_data,
                "processing_steps": 5,
                "coordination_version": self.version
            },
            "confidence_score": overall_confidence,
            "quality_metrics": {
                "image_analysis_confidence": image_response.confidence_score,
                "ecosystem_analysis_confidence": ecosystem_response.confidence_score,
                "recovery_plan_confidence": recovery_response.confidence_score,
                "synthesis_quality": synthesis_data.get("quality_score", 0.8)
            }
        }
    
    async def _synthesize_results(
        self,
        image_response: AgentResponse,
        ecosystem_response: AgentResponse,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Synthesize results from image and ecosystem analysis using Gemini Pro
        
        Args:
            image_response: Image analysis response
            ecosystem_response: Ecosystem analysis response
            request_data: Original request data
            request_id: Request ID
            
        Returns:
            Synthesis data
        """
        try:
            # Prepare synthesis prompt
            synthesis_prompt = f"""
            Como especialista em recuperação ambiental, sintetize os resultados das análises:

            ANÁLISE DE IMAGEM:
            {image_response.data}

            ANÁLISE DE ECOSSISTEMA:
            {ecosystem_response.data}

            CONTEXTO:
            - Arquivo: {request_data.get('filename', 'N/A')}
            - Coordenadas: {request_data.get('coordinates', 'N/A')}

            Forneça uma síntese que:
            1. Identifique correlações entre as análises
            2. Avalie riscos combinados
            3. Priorize áreas de intervenção
            4. Sugira abordagem integrada

            Responda em JSON com:
            {{
                "correlacoes": ["lista de correlações identificadas"],
                "riscos_combinados": "avaliação de riscos integrada",
                "prioridades": ["lista de prioridades de intervenção"],
                "abordagem_integrada": "estratégia de recuperação integrada",
                "quality_score": 0.0-1.0
            }}
            """
            
            response = await asyncio.to_thread(
                self.model.generate_content,
                synthesis_prompt
            )
            
            # Parse JSON response
            import json
            synthesis_data = json.loads(response.text)
            
            self.logger.debug(
                "Synthesis completed",
                request_id=str(request_id),
                quality_score=synthesis_data.get("quality_score")
            )
            
            return synthesis_data
            
        except Exception as e:
            self.logger.error(
                "Synthesis failed",
                request_id=str(request_id),
                error=str(e)
            )
            
            # Return fallback synthesis
            return {
                "correlacoes": ["Análise automática de correlações"],
                "riscos_combinados": "Avaliação baseada em análises individuais",
                "prioridades": ["Recuperação baseada em análises especializadas"],
                "abordagem_integrada": "Estratégia multi-agente coordenada",
                "quality_score": 0.6
            }
    
    async def _assemble_final_result(
        self,
        image_response: AgentResponse,
        ecosystem_response: AgentResponse,
        recovery_response: AgentResponse,
        synthesis_data: Dict[str, Any],
        request_id: UUID
    ) -> AnalysisResult:
        """
        Assemble final analysis result compatible with frontend
        
        Args:
            image_response: Image analysis response
            ecosystem_response: Ecosystem analysis response
            recovery_response: Recovery plan response
            synthesis_data: Synthesis data
            request_id: Request ID
            
        Returns:
            Final analysis result
        """
        try:
            # Extract data from responses
            image_data = image_response.data or {}
            ecosystem_data = ecosystem_response.data or {}
            recovery_data = recovery_response.data or {}
            
            # Build invasive species list
            especies_invasoras = []
            if "especies_invasoras" in image_data:
                for especie in image_data["especies_invasoras"]:
                    especies_invasoras.append(InvasiveSpecies(
                        nome=especie.get("nome", "Espécie não identificada"),
                        risco=RiskLevel(especie.get("risco", "Médio")),
                        descricao=especie.get("descricao", "Descrição não disponível"),
                        confianca=especie.get("confianca"),
                        localizacao=especie.get("localizacao")
                    ))
            
            # Determine risk levels
            risco_dengue = RiskLevel(image_data.get("risco_dengue", "Médio"))
            viabilidade_restauracao = ViabilityLevel(
                ecosystem_data.get("viabilidade_restauracao", "Média")
            )
            
            # Get recovery plan actions
            plano_recuperacao = recovery_data.get("acoes", [
                "Plano de recuperação em desenvolvimento"
            ])
            
            # Create ecosystem summary
            resumo_ecossistema = synthesis_data.get(
                "abordagem_integrada",
                ecosystem_data.get("resumo", "Análise de ecossistema concluída")
            )
            
            result = AnalysisResult(
                riscoDengue=risco_dengue,
                especiesInvasoras=especies_invasoras,
                viabilidadeRestauracao=viabilidade_restauracao,
                planoRecuperacao=plano_recuperacao,
                resumoEcossistema=resumo_ecossistema
            )
            
            self.logger.info(
                "Final result assembled",
                request_id=str(request_id),
                especies_count=len(especies_invasoras),
                acoes_count=len(plano_recuperacao)
            )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Result assembly failed",
                request_id=str(request_id),
                error=str(e)
            )
            
            # Return minimal fallback result
            return AnalysisResult(
                riscoDengue=RiskLevel.MEDIO,
                especiesInvasoras=[],
                viabilidadeRestauracao=ViabilityLevel.MEDIA,
                planoRecuperacao=["Análise em processamento"],
                resumoEcossistema="Análise coordenada concluída com limitações"
            )
