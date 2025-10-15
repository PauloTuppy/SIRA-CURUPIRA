"""
Recovery Plan Agent - Specialized in Gemini + RAG for restoration plan generation
"""

import asyncio
import json
import httpx
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, timedelta

import structlog
from google.generativeai import GenerativeModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseAgent
from ..config import settings
from ..utils.exceptions import AnalysisError, ServiceError, ValidationError


class RecoveryPlanAgent(BaseAgent):
    """
    Recovery Plan Agent using Gemini + RAG
    Specialized in generating environmental restoration plans
    """
    
    def __init__(self):
        super().__init__(
            name="recovery_plan",
            version="1.0.0",
            timeout_seconds=150.0,  # 2.5 minutes for plan generation
            max_retries=3
        )

        # Initialize Gemini Pro with safety settings
        genai.configure(api_key=settings.gemini_api_key)
        self.model = GenerativeModel(
            settings.recovery_plan_model,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        self.rag_service_url = settings.rag_service_url

        self.logger = structlog.get_logger("agent.recovery_plan")

        # Recovery action categories
        self.action_categories = {
            "controle_invasoras": "Controle de Espécies Invasoras",
            "revegetacao": "Revegetação e Plantio",
            "controle_vetores": "Controle de Vetores de Doenças",
            "conservacao_solo": "Conservação do Solo",
            "manejo_agua": "Manejo de Recursos Hídricos",
            "monitoramento": "Monitoramento Ambiental",
            "educacao": "Educação Ambiental",
            "manutencao": "Manutenção e Cuidados"
        }

        # Cost estimation factors (R$ per unit)
        self.cost_factors = {
            "mudas_nativas": 15.0,  # per seedling
            "remocao_invasoras": 50.0,  # per m²
            "sistema_monitoramento": 5000.0,  # per system
            "educacao_ambiental": 2000.0,  # per program
            "manutencao_mensal": 800.0,  # per month
            "equipamentos": 3000.0,  # per set
            "mao_obra_especializada": 150.0  # per day
        }
    
    async def _process_request(
        self,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Process recovery plan generation request
        
        Args:
            request_data: Request data with previous analysis results
            request_id: Request ID
            
        Returns:
            Recovery plan results
        """
        self.logger.info(
            "Starting recovery plan generation",
            request_id=str(request_id)
        )
        
        try:
            # Extract and validate previous analysis results
            image_analysis = request_data.get("image_analysis", {})
            ecosystem_analysis = request_data.get("ecosystem_analysis", {})
            synthesis = request_data.get("synthesis", {})
            coordinates = request_data.get("coordinates")
            area_size = request_data.get("area_size", 1000)  # m² default
            budget_range = request_data.get("budget_range")

            # Validate required data
            if not image_analysis and not ecosystem_analysis:
                raise ValidationError(
                    message="At least one analysis (image or ecosystem) is required",
                    field="analysis_data"
                )

            # Step 1: Get recovery strategies from RAG
            recovery_context = await self._get_recovery_context(
                image_analysis, ecosystem_analysis, coordinates, request_id
            )

            # Step 2: Generate comprehensive plan with Gemini Pro
            recovery_plan = await self._generate_comprehensive_plan(
                image_analysis, ecosystem_analysis, synthesis, recovery_context,
                area_size, budget_range, request_id
            )

            # Step 3: Calculate detailed costs and timeline
            enhanced_plan = await self._enhance_plan_with_details(
                recovery_plan, area_size, request_id
            )

            # Step 4: Generate monitoring framework
            monitoring_plan = await self._generate_monitoring_plan(
                enhanced_plan, image_analysis, ecosystem_analysis, request_id
            )

            # Combine all components
            final_plan = {
                **enhanced_plan,
                "monitoramento": monitoring_plan,
                "area_estimada_m2": area_size,
                "data_criacao": datetime.now().isoformat(),
                "versao_plano": "1.0"
            }

            self.logger.info(
                "Recovery plan generation completed",
                request_id=str(request_id),
                actions_count=len(final_plan.get("acoes", [])),
                estimated_cost=final_plan.get("custo_detalhado", {}).get("total", 0),
                timeline_months=final_plan.get("cronograma_detalhado", {}).get("duracao_total_meses", 0)
            )

            return {
                "data": final_plan,
                "metadata": {
                    "model_used": settings.recovery_plan_model,
                    "rag_strategies_used": len(recovery_context.get("strategies", [])),
                    "analysis_type": "comprehensive_recovery_planning",
                    "area_size_m2": area_size,
                    "plan_complexity": self._assess_plan_complexity(final_plan)
                },
                "confidence_score": final_plan.get("confianca_geral", 0.8),
                "quality_metrics": {
                    "plan_completeness": self._calculate_plan_completeness(final_plan),
                    "strategy_relevance": recovery_context.get("relevance_score", 0.85),
                    "implementation_feasibility": self._assess_feasibility(final_plan),
                    "cost_accuracy": 0.8,
                    "timeline_realism": 0.85
                }
            }
            
        except Exception as e:
            self.logger.error(
                "Recovery plan generation failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )
            raise AnalysisError(
                message=f"Recovery plan generation failed: {str(e)}",
                analysis_id=str(request_id),
                agent_name=self.name
            )
    
    async def _get_recovery_context(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        coordinates: Optional[Dict[str, float]],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Get recovery strategies from RAG service

        Args:
            image_analysis: Image analysis results
            ecosystem_analysis: Ecosystem analysis results
            coordinates: GPS coordinates
            request_id: Request ID

        Returns:
            Recovery context data with strategies and best practices
        """
        try:
            # Build comprehensive query based on analysis results
            query_components = []

            # Add ecosystem-specific queries
            ecosystem_type = ecosystem_analysis.get("tipo_ecossistema", "")
            bioma = ecosystem_analysis.get("bioma_identificado", "")
            viabilidade = ecosystem_analysis.get("viabilidade_restauracao", "")

            if ecosystem_type:
                query_components.append(f"restauração {ecosystem_type}")
            if bioma:
                query_components.append(f"recuperação {bioma}")
            if viabilidade:
                query_components.append(f"viabilidade {viabilidade.lower()}")

            # Add threat-specific queries
            threats = ecosystem_analysis.get("ameacas_identificadas", [])
            for threat in threats[:3]:  # Top 3 threats
                if threat:
                    query_components.append(f"controle {threat}")

            # Add invasive species queries
            invasive_species = image_analysis.get("especies_invasoras", [])
            for species in invasive_species[:2]:  # Top 2 species
                if isinstance(species, dict) and "nome" in species:
                    species_name = species["nome"]
                    query_components.append(f"manejo {species_name}")

            # Add vector control queries if dengue risk is present
            risco_dengue = image_analysis.get("risco_dengue", "")
            if risco_dengue in ["Alto", "Médio"]:
                query_components.append("controle Aedes aegypti")
                query_components.append("eliminação criadouros")

            # Add vegetation coverage queries
            cobertura_vegetal = image_analysis.get("cobertura_vegetal", 0.5)
            if cobertura_vegetal < 0.4:
                query_components.append("revegetação área degradada")
                query_components.append("plantio espécies nativas")
            elif cobertura_vegetal > 0.7:
                query_components.append("conservação vegetação existente")

            # Build final queries (multiple specific queries for better results)
            queries = [
                "recuperação ambiental restauração ecológica Brasil",
                " ".join(query_components[:4]) if query_components else "restauração ambiental",
                f"plano recuperação {bioma}" if bioma else "plano restauração ecossistema",
                "cronograma custos restauração ambiental"
            ]

            # Prepare RAG requests
            all_strategies = []
            total_relevance = 0.0

            for i, query in enumerate(queries):
                if not query.strip():
                    continue

                rag_request = {
                    "query": query,
                    "coordinates": coordinates,
                    "search_type": "recovery_restoration",
                    "filters": {
                        "sources": ["Manual_Restauracao", "SMA", "IBAMA", "ICMBio", "Academico"],
                        "content_types": ["strategy", "methodology", "best_practice", "case_study"]
                    },
                    "limit": 8,
                    "include_metadata": True
                }

                self.logger.debug(
                    f"Sending RAG query {i+1}",
                    request_id=str(request_id),
                    query=query
                )

                # Call RAG service
                if self.rag_service_url and self.rag_service_url != "http://localhost:8002":
                    try:
                        async with httpx.AsyncClient(timeout=30.0) as client:
                            response = await client.post(
                                f"{self.rag_service_url}/api/v1/search",
                                json=rag_request,
                                headers={"Content-Type": "application/json"}
                            )
                            response.raise_for_status()
                            rag_result = response.json()

                            strategies = rag_result.get("documents", [])
                            all_strategies.extend(strategies)
                            total_relevance += rag_result.get("relevance_score", 0.5)

                    except (httpx.RequestError, httpx.HTTPStatusError) as e:
                        self.logger.warning(
                            f"RAG query {i+1} failed",
                            request_id=str(request_id),
                            error=str(e)
                        )

            # Process and deduplicate strategies
            if all_strategies:
                # Remove duplicates and sort by relevance
                unique_strategies = []
                seen_titles = set()

                for strategy in sorted(all_strategies, key=lambda x: x.get("relevance", 0), reverse=True):
                    title = strategy.get("title", "")
                    if title and title not in seen_titles:
                        unique_strategies.append(strategy)
                        seen_titles.add(title)
                        if len(unique_strategies) >= 12:  # Limit to top 12
                            break

                avg_relevance = total_relevance / len(queries) if queries else 0.5

                recovery_context = {
                    "strategies": unique_strategies,
                    "relevance_score": avg_relevance,
                    "total_strategies": len(unique_strategies),
                    "queries_used": queries,
                    "source": "rag_service"
                }

                self.logger.info(
                    "Recovery context retrieved successfully",
                    request_id=str(request_id),
                    strategies_count=len(unique_strategies),
                    avg_relevance=avg_relevance
                )

                return recovery_context

            # Fallback: Generate context based on analysis
            return await self._generate_fallback_recovery_context(
                image_analysis, ecosystem_analysis, request_id
            )

        except Exception as e:
            self.logger.error(
                "Failed to get recovery context",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return fallback context
            return await self._generate_fallback_recovery_context(
                image_analysis, ecosystem_analysis, request_id
            )

    async def _generate_comprehensive_plan(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        synthesis: Dict[str, Any],
        recovery_context: Dict[str, Any],
        area_size: float,
        budget_range: Optional[Dict[str, float]],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate comprehensive recovery plan with Gemini Pro

        Args:
            image_analysis: Image analysis results
            ecosystem_analysis: Ecosystem analysis results
            synthesis: Synthesis results
            recovery_context: Recovery strategies from RAG
            area_size: Area size in m²
            budget_range: Optional budget constraints
            request_id: Request ID

        Returns:
            Comprehensive recovery plan
        """
        try:
            # Build comprehensive prompt
            plan_prompt = self._build_comprehensive_prompt(
                image_analysis, ecosystem_analysis, synthesis, recovery_context,
                area_size, budget_range
            )

            self.logger.debug(
                "Generating plan with Gemini Pro",
                request_id=str(request_id),
                prompt_length=len(plan_prompt),
                area_size=area_size
            )

            # Generate with Gemini Pro
            response = await asyncio.to_thread(
                self.model.generate_content,
                plan_prompt
            )

            if not response.text:
                raise AnalysisError(
                    message="Empty response from Gemini Pro",
                    analysis_id=str(request_id),
                    agent_name=self.name
                )

            # Parse response
            recovery_plan = self._parse_gemini_plan_response(response.text, request_id)

            # Validate and enhance plan
            validated_plan = self._validate_and_enhance_plan(
                recovery_plan, image_analysis, ecosystem_analysis, request_id
            )

            self.logger.info(
                "Comprehensive plan generated successfully",
                request_id=str(request_id),
                actions_count=len(validated_plan.get("acoes", [])),
                timeline_phases=len(validated_plan.get("cronograma", {}))
            )

            return validated_plan

        except Exception as e:
            self.logger.error(
                "Comprehensive plan generation failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return fallback plan
            return await self._generate_fallback_plan(
                image_analysis, ecosystem_analysis, area_size, request_id
            )

    def _build_comprehensive_prompt(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        synthesis: Dict[str, Any],
        recovery_context: Dict[str, Any],
        area_size: float,
        budget_range: Optional[Dict[str, float]]
    ) -> str:
        """
        Build comprehensive prompt for Gemini Pro

        Args:
            image_analysis: Image analysis results
            ecosystem_analysis: Ecosystem analysis results
            synthesis: Synthesis results
            recovery_context: Recovery context from RAG
            area_size: Area size in m²
            budget_range: Budget constraints

        Returns:
            Comprehensive prompt
        """
        # Extract key information
        risco_dengue = image_analysis.get("risco_dengue", "N/A")
        especies_invasoras = image_analysis.get("especies_invasoras", [])
        cobertura_vegetal = image_analysis.get("cobertura_vegetal", 0)
        sinais_degradacao = image_analysis.get("sinais_degradacao", [])

        tipo_ecossistema = ecosystem_analysis.get("tipo_ecossistema", "N/A")
        bioma = ecosystem_analysis.get("bioma_identificado", "N/A")
        viabilidade = ecosystem_analysis.get("viabilidade_restauracao", "N/A")
        biodiversidade_score = ecosystem_analysis.get("biodiversidade_score", 0)
        ameacas = ecosystem_analysis.get("ameacas_identificadas", [])
        especies_nativas = ecosystem_analysis.get("especies_nativas_esperadas", [])

        # Build strategies context
        strategies_text = ""
        strategies = recovery_context.get("strategies", [])
        if strategies:
            strategies_text = "\n".join([
                f"• {strategy.get('title', 'Estratégia')}: {strategy.get('content', '')[:200]}..."
                for strategy in strategies[:8]  # Top 8 strategies
            ])
        else:
            strategies_text = "Estratégias específicas não disponíveis - usar conhecimento geral."

        # Build budget context
        budget_text = ""
        if budget_range:
            min_budget = budget_range.get("min", 0)
            max_budget = budget_range.get("max", 0)
            if min_budget > 0 or max_budget > 0:
                budget_text = f"\nRESTRIÇÕES ORÇAMENTÁRIAS:\n- Orçamento mínimo: R$ {min_budget:,.2f}\n- Orçamento máximo: R$ {max_budget:,.2f}"

        # Build comprehensive prompt
        prompt = f"""
Você é um especialista em recuperação ambiental e restauração ecológica com 20 anos de experiência no Brasil. Desenvolva um plano DETALHADO e PRÁTICO de recuperação ambiental baseado nas análises científicas fornecidas.

DADOS DA ANÁLISE DE IMAGEM:
- Risco de Dengue: {risco_dengue}
- Cobertura Vegetal: {cobertura_vegetal:.1%}
- Espécies Invasoras Detectadas: {len(especies_invasoras)}
{chr(10).join([f"  * {esp.get('nome', 'N/A')} (Risco: {esp.get('risco', 'N/A')}, Confiança: {esp.get('confianca', 0):.1%})" for esp in especies_invasoras[:3]])}
- Sinais de Degradação: {', '.join(sinais_degradacao[:5]) if sinais_degradacao else 'Nenhum identificado'}

DADOS DA ANÁLISE DE ECOSSISTEMA:
- Tipo de Ecossistema: {tipo_ecossistema}
- Bioma: {bioma}
- Viabilidade de Restauração: {viabilidade}
- Score de Biodiversidade: {biodiversidade_score:.1%}
- Principais Ameaças: {', '.join(ameacas[:5]) if ameacas else 'Nenhuma identificada'}
- Espécies Nativas Esperadas: {', '.join(especies_nativas[:5]) if especies_nativas else 'A determinar'}

ÁREA DO PROJETO:
- Tamanho: {area_size:,.0f} m² ({area_size/10000:.2f} hectares)
{budget_text}

ESTRATÉGIAS E MELHORES PRÁTICAS DISPONÍVEIS:
{strategies_text}

INSTRUÇÕES PARA O PLANO:

1. AÇÕES ESPECÍFICAS: Liste 8-15 ações concretas, práticas e mensuráveis, ordenadas por prioridade
2. CRONOGRAMA DETALHADO: Organize as ações em fases temporais realistas
3. RECURSOS NECESSÁRIOS: Especifique materiais, equipamentos, mão de obra
4. ESTIMATIVA DE CUSTOS: Forneça valores realistas em reais (R$)
5. MÉTRICAS DE SUCESSO: Defina indicadores quantificáveis
6. RESPONSÁVEIS: Identifique atores e instituições envolvidas
7. RISCOS E CONTINGÊNCIAS: Antecipe problemas e soluções

RESPONDA EXCLUSIVAMENTE EM JSON VÁLIDO:
{{
    "resumo_executivo": "Resumo do plano em 2-3 frases",
    "objetivo_principal": "Objetivo principal do projeto de recuperação",
    "acoes": [
        {{
            "id": 1,
            "categoria": "controle_invasoras|revegetacao|controle_vetores|conservacao_solo|manejo_agua|monitoramento|educacao|manutencao",
            "titulo": "Título da ação",
            "descricao": "Descrição detalhada da ação",
            "prioridade": "Alta|Média|Baixa",
            "recursos_necessarios": ["lista de recursos específicos"],
            "custo_estimado": 0000.00,
            "duracao_dias": 00,
            "responsavel": "Quem executa",
            "pre_requisitos": ["ações que devem ser feitas antes"],
            "resultados_esperados": ["resultados mensuráveis"]
        }}
    ],
    "cronograma": {{
        "fase_1_imediato": {{
            "periodo": "0-3 meses",
            "acoes_ids": [1, 2, 3],
            "objetivo": "Objetivo da fase",
            "custo_fase": 0000.00
        }},
        "fase_2_curto_prazo": {{
            "periodo": "3-12 meses",
            "acoes_ids": [4, 5, 6],
            "objetivo": "Objetivo da fase",
            "custo_fase": 0000.00
        }},
        "fase_3_medio_prazo": {{
            "periodo": "1-3 anos",
            "acoes_ids": [7, 8, 9],
            "objetivo": "Objetivo da fase",
            "custo_fase": 0000.00
        }},
        "fase_4_longo_prazo": {{
            "periodo": "3+ anos",
            "acoes_ids": [10, 11],
            "objetivo": "Objetivo da fase",
            "custo_fase": 0000.00
        }}
    }},
    "custo_total_estimado": 00000.00,
    "duracao_total_meses": 00,
    "metricas_sucesso": [
        {{
            "indicador": "Nome do indicador",
            "meta": "Meta quantificada",
            "prazo": "Prazo para atingir",
            "metodo_medicao": "Como medir"
        }}
    ],
    "riscos_contingencias": [
        {{
            "risco": "Descrição do risco",
            "probabilidade": "Alta|Média|Baixa",
            "impacto": "Alto|Médio|Baixo",
            "mitigacao": "Como mitigar"
        }}
    ],
    "responsaveis": [
        {{
            "ator": "Nome do responsável",
            "papel": "Papel no projeto",
            "responsabilidades": ["lista de responsabilidades"]
        }}
    ],
    "confianca_geral": 0.0-1.0
}}

IMPORTANTE:
- Use valores realistas de custos baseados no mercado brasileiro
- Considere a sazonalidade para plantios e ações
- Priorize ações com maior impacto ambiental
- Seja específico e prático nas recomendações
"""

        return prompt

    def _parse_gemini_plan_response(self, response_text: str, request_id: UUID) -> Dict[str, Any]:
        """
        Parse Gemini Pro response and extract JSON plan

        Args:
            response_text: Raw response from Gemini Pro
            request_id: Request ID

        Returns:
            Parsed recovery plan
        """
        try:
            # Clean and extract JSON
            response_text = response_text.strip()

            # Look for JSON block
            if "```json" in response_text:
                start = response_text.find("```json") + 7
                end = response_text.find("```", start)
                if end != -1:
                    json_text = response_text[start:end].strip()
                else:
                    json_text = response_text[start:].strip()
            elif "{" in response_text and "}" in response_text:
                start = response_text.find("{")
                end = response_text.rfind("}") + 1
                json_text = response_text[start:end]
            else:
                raise ValueError("No JSON found in response")

            # Parse JSON
            plan = json.loads(json_text)

            self.logger.debug(
                "Successfully parsed Gemini plan response",
                request_id=str(request_id),
                actions_count=len(plan.get("acoes", [])),
                phases_count=len(plan.get("cronograma", {}))
            )

            return plan

        except Exception as e:
            self.logger.warning(
                "Failed to parse Gemini plan response, using text extraction",
                request_id=str(request_id),
                error=str(e),
                response_preview=response_text[:300] if response_text else None
            )

            # Fallback: extract basic plan from text
            return self._extract_plan_from_text(response_text, request_id)

    def _validate_and_enhance_plan(
        self,
        plan: Dict[str, Any],
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate and enhance recovery plan

        Args:
            plan: Raw plan from Gemini
            image_analysis: Image analysis results
            ecosystem_analysis: Ecosystem analysis results
            request_id: Request ID

        Returns:
            Validated and enhanced plan
        """
        try:
            # Ensure required fields exist
            required_fields = {
                "resumo_executivo": "Plano de recuperação ambiental personalizado",
                "objetivo_principal": "Restaurar e conservar o ecossistema local",
                "acoes": [],
                "cronograma": {},
                "custo_total_estimado": 0.0,
                "duracao_total_meses": 12,
                "metricas_sucesso": [],
                "riscos_contingencias": [],
                "responsaveis": [],
                "confianca_geral": 0.7
            }

            for field, default_value in required_fields.items():
                if field not in plan:
                    plan[field] = default_value

            # Validate and enhance actions
            if not isinstance(plan["acoes"], list):
                plan["acoes"] = []

            enhanced_actions = []
            for i, action in enumerate(plan["acoes"]):
                if isinstance(action, dict):
                    enhanced_action = self._validate_action(action, i + 1)
                    enhanced_actions.append(enhanced_action)

            plan["acoes"] = enhanced_actions

            # Validate cronograma
            if not isinstance(plan["cronograma"], dict):
                plan["cronograma"] = {}

            plan["cronograma"] = self._validate_timeline(plan["cronograma"], len(enhanced_actions))

            # Validate costs
            try:
                plan["custo_total_estimado"] = float(plan["custo_total_estimado"])
            except (ValueError, TypeError):
                plan["custo_total_estimado"] = sum([
                    action.get("custo_estimado", 0) for action in enhanced_actions
                ])

            # Validate duration
            try:
                plan["duracao_total_meses"] = int(plan["duracao_total_meses"])
            except (ValueError, TypeError):
                plan["duracao_total_meses"] = 24  # Default 2 years

            # Validate confidence
            try:
                confidence = float(plan["confianca_geral"])
                plan["confianca_geral"] = max(0.0, min(1.0, confidence))
            except (ValueError, TypeError):
                plan["confianca_geral"] = 0.7

            # Ensure lists are properly formatted
            for list_field in ["metricas_sucesso", "riscos_contingencias", "responsaveis"]:
                if not isinstance(plan[list_field], list):
                    plan[list_field] = []

            # Add missing metrics if none provided
            if not plan["metricas_sucesso"]:
                plan["metricas_sucesso"] = self._generate_default_metrics(
                    image_analysis, ecosystem_analysis
                )

            # Add missing risks if none provided
            if not plan["riscos_contingencias"]:
                plan["riscos_contingencias"] = self._generate_default_risks()

            # Add missing responsaveis if none provided
            if not plan["responsaveis"]:
                plan["responsaveis"] = self._generate_default_responsaveis()

            self.logger.debug(
                "Plan validation completed",
                request_id=str(request_id),
                actions_count=len(plan["acoes"]),
                total_cost=plan["custo_total_estimado"],
                duration_months=plan["duracao_total_meses"]
            )

            return plan

        except Exception as e:
            self.logger.error(
                "Plan validation failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return minimal valid plan
            return {
                "resumo_executivo": "Plano básico de recuperação ambiental",
                "objetivo_principal": "Restaurar ecossistema degradado",
                "acoes": [
                    {
                        "id": 1,
                        "categoria": "monitoramento",
                        "titulo": "Avaliação inicial da área",
                        "descricao": "Realizar diagnóstico detalhado da área",
                        "prioridade": "Alta",
                        "recursos_necessarios": ["Equipe técnica"],
                        "custo_estimado": 2000.0,
                        "duracao_dias": 30,
                        "responsavel": "Equipe técnica",
                        "pre_requisitos": [],
                        "resultados_esperados": ["Diagnóstico completo"]
                    }
                ],
                "cronograma": {
                    "fase_1_imediato": {
                        "periodo": "0-3 meses",
                        "acoes_ids": [1],
                        "objetivo": "Diagnóstico inicial",
                        "custo_fase": 2000.0
                    }
                },
                "custo_total_estimado": 2000.0,
                "duracao_total_meses": 12,
                "metricas_sucesso": [
                    {
                        "indicador": "Diagnóstico completo",
                        "meta": "100% da área avaliada",
                        "prazo": "3 meses",
                        "metodo_medicao": "Relatório técnico"
                    }
                ],
                "riscos_contingencias": [
                    {
                        "risco": "Condições climáticas adversas",
                        "probabilidade": "Média",
                        "impacto": "Médio",
                        "mitigacao": "Planejamento sazonal"
                    }
                ],
                "responsaveis": [
                    {
                        "ator": "Equipe técnica",
                        "papel": "Execução",
                        "responsabilidades": ["Diagnóstico e implementação"]
                    }
                ],
                "confianca_geral": 0.6
            }

    def _validate_action(self, action: Dict[str, Any], action_id: int) -> Dict[str, Any]:
        """Validate and normalize a single action"""
        try:
            validated = {
                "id": action.get("id", action_id),
                "categoria": action.get("categoria", "monitoramento"),
                "titulo": action.get("titulo", f"Ação {action_id}"),
                "descricao": action.get("descricao", "Descrição não fornecida"),
                "prioridade": action.get("prioridade", "Média"),
                "recursos_necessarios": action.get("recursos_necessarios", []),
                "custo_estimado": 0.0,
                "duracao_dias": action.get("duracao_dias", 30),
                "responsavel": action.get("responsavel", "A definir"),
                "pre_requisitos": action.get("pre_requisitos", []),
                "resultados_esperados": action.get("resultados_esperados", [])
            }

            # Validate category
            if validated["categoria"] not in self.action_categories:
                validated["categoria"] = "monitoramento"

            # Validate priority
            if validated["prioridade"] not in ["Alta", "Média", "Baixa"]:
                validated["prioridade"] = "Média"

            # Validate cost
            try:
                validated["custo_estimado"] = float(action.get("custo_estimado", 0))
            except (ValueError, TypeError):
                validated["custo_estimado"] = 1000.0  # Default cost

            # Validate duration
            try:
                validated["duracao_dias"] = int(action.get("duracao_dias", 30))
            except (ValueError, TypeError):
                validated["duracao_dias"] = 30

            # Ensure lists
            for list_field in ["recursos_necessarios", "pre_requisitos", "resultados_esperados"]:
                if not isinstance(validated[list_field], list):
                    validated[list_field] = []

            return validated

        except Exception:
            return {
                "id": action_id,
                "categoria": "monitoramento",
                "titulo": f"Ação {action_id}",
                "descricao": "Ação de recuperação ambiental",
                "prioridade": "Média",
                "recursos_necessarios": [],
                "custo_estimado": 1000.0,
                "duracao_dias": 30,
                "responsavel": "A definir",
                "pre_requisitos": [],
                "resultados_esperados": []
            }

    def _validate_timeline(self, cronograma: Dict[str, Any], total_actions: int) -> Dict[str, Any]:
        """Validate and normalize timeline"""
        try:
            phases = ["fase_1_imediato", "fase_2_curto_prazo", "fase_3_medio_prazo", "fase_4_longo_prazo"]
            periods = ["0-3 meses", "3-12 meses", "1-3 anos", "3+ anos"]

            validated_cronograma = {}

            for i, phase in enumerate(phases):
                if phase in cronograma and isinstance(cronograma[phase], dict):
                    phase_data = cronograma[phase]
                    validated_cronograma[phase] = {
                        "periodo": phase_data.get("periodo", periods[i]),
                        "acoes_ids": phase_data.get("acoes_ids", []),
                        "objetivo": phase_data.get("objetivo", f"Objetivos da {phase.replace('_', ' ')}"),
                        "custo_fase": float(phase_data.get("custo_fase", 0))
                    }
                else:
                    validated_cronograma[phase] = {
                        "periodo": periods[i],
                        "acoes_ids": [],
                        "objetivo": f"Objetivos da {phase.replace('_', ' ')}",
                        "custo_fase": 0.0
                    }

            return validated_cronograma

        except Exception:
            return {
                "fase_1_imediato": {
                    "periodo": "0-3 meses",
                    "acoes_ids": list(range(1, min(4, total_actions + 1))),
                    "objetivo": "Ações imediatas",
                    "custo_fase": 0.0
                },
                "fase_2_curto_prazo": {
                    "periodo": "3-12 meses",
                    "acoes_ids": [],
                    "objetivo": "Implementação inicial",
                    "custo_fase": 0.0
                },
                "fase_3_medio_prazo": {
                    "periodo": "1-3 anos",
                    "acoes_ids": [],
                    "objetivo": "Consolidação",
                    "custo_fase": 0.0
                },
                "fase_4_longo_prazo": {
                    "periodo": "3+ anos",
                    "acoes_ids": [],
                    "objetivo": "Monitoramento de longo prazo",
                    "custo_fase": 0.0
                }
            }

    def _generate_default_metrics(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate default success metrics based on analysis"""
        metrics = []

        # Vegetation coverage metric
        cobertura_atual = image_analysis.get("cobertura_vegetal", 0)
        meta_cobertura = min(0.9, cobertura_atual + 0.3)
        metrics.append({
            "indicador": "Cobertura vegetal",
            "meta": f"{meta_cobertura:.0%} da área",
            "prazo": "24 meses",
            "metodo_medicao": "Análise de imagens de satélite"
        })

        # Invasive species control
        especies_invasoras = image_analysis.get("especies_invasoras", [])
        if especies_invasoras:
            metrics.append({
                "indicador": "Controle de espécies invasoras",
                "meta": "Redução de 80% da população",
                "prazo": "12 meses",
                "metodo_medicao": "Monitoramento de campo"
            })

        # Biodiversity improvement
        biodiversidade_atual = ecosystem_analysis.get("biodiversidade_score", 0.5)
        meta_biodiversidade = min(0.9, biodiversidade_atual + 0.2)
        metrics.append({
            "indicador": "Índice de biodiversidade",
            "meta": f"{meta_biodiversidade:.0%}",
            "prazo": "36 meses",
            "metodo_medicao": "Inventário de fauna e flora"
        })

        # Vector control if applicable
        risco_dengue = image_analysis.get("risco_dengue", "")
        if risco_dengue in ["Alto", "Médio"]:
            metrics.append({
                "indicador": "Eliminação de criadouros",
                "meta": "Zero criadouros de Aedes aegypti",
                "prazo": "6 meses",
                "metodo_medicao": "Inspeção mensal"
            })

        return metrics

    def _generate_default_risks(self) -> List[Dict[str, Any]]:
        """Generate default risk assessment"""
        return [
            {
                "risco": "Condições climáticas adversas",
                "probabilidade": "Média",
                "impacto": "Médio",
                "mitigacao": "Planejamento sazonal e proteção de mudas"
            },
            {
                "risco": "Reinfestação por espécies invasoras",
                "probabilidade": "Alta",
                "impacto": "Alto",
                "mitigacao": "Monitoramento contínuo e controle preventivo"
            },
            {
                "risco": "Limitações orçamentárias",
                "probabilidade": "Média",
                "impacto": "Alto",
                "mitigacao": "Busca por financiamentos e parcerias"
            },
            {
                "risco": "Falta de engajamento comunitário",
                "probabilidade": "Baixa",
                "impacto": "Médio",
                "mitigacao": "Programa de educação ambiental"
            }
        ]

    def _generate_default_responsaveis(self) -> List[Dict[str, Any]]:
        """Generate default responsible parties"""
        return [
            {
                "ator": "Órgão ambiental municipal",
                "papel": "Coordenação geral",
                "responsabilidades": [
                    "Supervisão do projeto",
                    "Licenciamento ambiental",
                    "Articulação institucional"
                ]
            },
            {
                "ator": "Equipe técnica especializada",
                "papel": "Execução técnica",
                "responsabilidades": [
                    "Implementação das ações",
                    "Monitoramento técnico",
                    "Relatórios de progresso"
                ]
            },
            {
                "ator": "Comunidade local",
                "papel": "Participação e manutenção",
                "responsabilidades": [
                    "Apoio às ações",
                    "Manutenção básica",
                    "Vigilância ambiental"
                ]
            },
            {
                "ator": "Instituições de pesquisa",
                "papel": "Suporte científico",
                "responsabilidades": [
                    "Monitoramento científico",
                    "Avaliação de resultados",
                    "Capacitação técnica"
                ]
            }
        ]

    async def _enhance_plan_with_details(
        self,
        plan: Dict[str, Any],
        area_size: float,
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Enhance plan with detailed costs and timeline calculations

        Args:
            plan: Base recovery plan
            area_size: Area size in m²
            request_id: Request ID

        Returns:
            Enhanced plan with detailed calculations
        """
        try:
            enhanced_plan = plan.copy()

            # Calculate detailed costs
            detailed_costs = self._calculate_detailed_costs(plan["acoes"], area_size)
            enhanced_plan["custo_detalhado"] = detailed_costs

            # Update total cost if calculated cost is more accurate
            if detailed_costs["total"] > 0:
                enhanced_plan["custo_total_estimado"] = detailed_costs["total"]

            # Calculate detailed timeline
            detailed_timeline = self._calculate_detailed_timeline(plan["acoes"], plan["cronograma"])
            enhanced_plan["cronograma_detalhado"] = detailed_timeline

            # Add implementation recommendations
            enhanced_plan["recomendacoes_implementacao"] = self._generate_implementation_recommendations(
                plan, area_size
            )

            # Add seasonal considerations
            enhanced_plan["consideracoes_sazonais"] = self._generate_seasonal_considerations(plan["acoes"])

            self.logger.debug(
                "Plan enhanced with details",
                request_id=str(request_id),
                total_cost=detailed_costs["total"],
                timeline_months=detailed_timeline.get("duracao_total_meses", 0)
            )

            return enhanced_plan

        except Exception as e:
            self.logger.warning(
                "Plan enhancement failed, returning base plan",
                request_id=str(request_id),
                error=str(e)
            )
            return plan

    def _calculate_detailed_costs(self, acoes: List[Dict[str, Any]], area_size: float) -> Dict[str, Any]:
        """Calculate detailed cost breakdown"""
        try:
            costs_by_category = {}
            total_cost = 0.0

            for action in acoes:
                categoria = action.get("categoria", "monitoramento")
                custo = action.get("custo_estimado", 0)

                if categoria not in costs_by_category:
                    costs_by_category[categoria] = 0.0

                costs_by_category[categoria] += custo
                total_cost += custo

            # Add area-based adjustments
            area_hectares = area_size / 10000
            if area_hectares > 1:
                # Scale costs for larger areas
                scale_factor = min(2.0, 1 + (area_hectares - 1) * 0.3)
                total_cost *= scale_factor
                for categoria in costs_by_category:
                    costs_by_category[categoria] *= scale_factor

            # Add contingency (15%)
            contingency = total_cost * 0.15
            total_with_contingency = total_cost + contingency

            return {
                "por_categoria": costs_by_category,
                "subtotal": total_cost,
                "contingencia": contingency,
                "total": total_with_contingency,
                "custo_por_hectare": total_with_contingency / area_hectares if area_hectares > 0 else 0,
                "moeda": "BRL"
            }

        except Exception:
            return {
                "por_categoria": {},
                "subtotal": 0.0,
                "contingencia": 0.0,
                "total": 0.0,
                "custo_por_hectare": 0.0,
                "moeda": "BRL"
            }

    def _calculate_detailed_timeline(
        self,
        acoes: List[Dict[str, Any]],
        cronograma: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Calculate detailed timeline with dependencies"""
        try:
            # Calculate total duration considering dependencies
            max_duration = 0
            phase_durations = {}

            for phase_name, phase_data in cronograma.items():
                phase_actions = phase_data.get("acoes_ids", [])
                phase_duration = 0

                for action_id in phase_actions:
                    # Find action by ID
                    action = next((a for a in acoes if a.get("id") == action_id), None)
                    if action:
                        action_duration_months = action.get("duracao_dias", 30) / 30
                        phase_duration = max(phase_duration, action_duration_months)

                phase_durations[phase_name] = phase_duration
                max_duration += phase_duration

            # Generate milestone schedule
            milestones = []
            cumulative_months = 0

            for phase_name, duration in phase_durations.items():
                if duration > 0:
                    cumulative_months += duration
                    milestones.append({
                        "fase": phase_name.replace("_", " ").title(),
                        "mes": int(cumulative_months),
                        "descricao": cronograma.get(phase_name, {}).get("objetivo", "Marco da fase")
                    })

            return {
                "duracao_total_meses": int(max_duration),
                "duracao_por_fase": phase_durations,
                "marcos_principais": milestones,
                "data_inicio_sugerida": "Início da estação chuvosa (outubro-novembro)",
                "data_conclusao_estimada": f"{int(max_duration)} meses após início"
            }

        except Exception:
            return {
                "duracao_total_meses": 24,
                "duracao_por_fase": {},
                "marcos_principais": [],
                "data_inicio_sugerida": "A definir",
                "data_conclusao_estimada": "24 meses"
            }

    def _generate_implementation_recommendations(
        self,
        plan: Dict[str, Any],
        area_size: float
    ) -> List[str]:
        """Generate implementation recommendations"""
        recommendations = []

        # Area size recommendations
        area_hectares = area_size / 10000
        if area_hectares < 0.5:
            recommendations.append("Área pequena: priorizar ações de alto impacto e baixo custo")
        elif area_hectares > 5:
            recommendations.append("Área extensa: considerar implementação por etapas/setores")

        # Cost recommendations
        total_cost = plan.get("custo_total_estimado", 0)
        if total_cost > 50000:
            recommendations.append("Custo elevado: buscar parcerias e financiamentos externos")

        # Timeline recommendations
        duration = plan.get("duracao_total_meses", 12)
        if duration > 36:
            recommendations.append("Projeto longo prazo: estabelecer marcos intermediários")

        # Action-specific recommendations
        acoes = plan.get("acoes", [])
        invasive_actions = [a for a in acoes if a.get("categoria") == "controle_invasoras"]
        if invasive_actions:
            recommendations.append("Controle de invasoras: executar preferencialmente na estação seca")

        revegetation_actions = [a for a in acoes if a.get("categoria") == "revegetacao"]
        if revegetation_actions:
            recommendations.append("Plantio: realizar no início da estação chuvosa para melhor estabelecimento")

        # General recommendations
        recommendations.extend([
            "Estabelecer parcerias com universidades para monitoramento científico",
            "Envolver a comunidade local desde o planejamento",
            "Documentar todas as ações para replicação em outras áreas",
            "Manter flexibilidade para ajustes baseados em resultados intermediários"
        ])

        return recommendations

    def _generate_seasonal_considerations(self, acoes: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        """Generate seasonal considerations for actions"""
        seasonal_plan = {
            "estacao_seca": [],
            "estacao_chuvosa": [],
            "ano_todo": []
        }

        for action in acoes:
            categoria = action.get("categoria", "")
            titulo = action.get("titulo", "")

            if categoria in ["controle_invasoras", "conservacao_solo"]:
                seasonal_plan["estacao_seca"].append(titulo)
            elif categoria in ["revegetacao", "manejo_agua"]:
                seasonal_plan["estacao_chuvosa"].append(titulo)
            else:
                seasonal_plan["ano_todo"].append(titulo)

        return seasonal_plan

    async def _generate_monitoring_plan(
        self,
        recovery_plan: Dict[str, Any],
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate comprehensive monitoring plan

        Args:
            recovery_plan: Recovery plan
            image_analysis: Image analysis results
            ecosystem_analysis: Ecosystem analysis results
            request_id: Request ID

        Returns:
            Monitoring plan
        """
        try:
            monitoring_plan = {
                "frequencia_monitoramento": {
                    "mensal": ["Controle de espécies invasoras", "Eliminação de criadouros"],
                    "trimestral": ["Crescimento da vegetação", "Indicadores de fauna"],
                    "semestral": ["Cobertura vegetal", "Qualidade do solo"],
                    "anual": ["Biodiversidade geral", "Avaliação de impacto"]
                },
                "indicadores_principais": [],
                "metodos_coleta": {},
                "responsaveis_monitoramento": [],
                "cronograma_avaliacoes": [],
                "relatorios_previstos": []
            }

            # Generate indicators based on analysis
            indicators = []

            # Vegetation indicators
            cobertura_atual = image_analysis.get("cobertura_vegetal", 0)
            indicators.append({
                "nome": "Cobertura vegetal",
                "baseline": f"{cobertura_atual:.1%}",
                "meta": f"{min(0.9, cobertura_atual + 0.3):.1%}",
                "metodo": "Análise de imagens de drone/satélite"
            })

            # Invasive species indicators
            especies_invasoras = image_analysis.get("especies_invasoras", [])
            if especies_invasoras:
                for especie in especies_invasoras[:3]:
                    indicators.append({
                        "nome": f"População de {especie.get('nome', 'espécie invasora')}",
                        "baseline": "Presente",
                        "meta": "Redução de 80%",
                        "metodo": "Contagem em transectos"
                    })

            # Biodiversity indicators
            biodiversidade_atual = ecosystem_analysis.get("biodiversidade_score", 0.5)
            indicators.append({
                "nome": "Índice de biodiversidade",
                "baseline": f"{biodiversidade_atual:.1%}",
                "meta": f"{min(0.9, biodiversidade_atual + 0.2):.1%}",
                "metodo": "Inventário de fauna e flora"
            })

            # Vector control indicators
            risco_dengue = image_analysis.get("risco_dengue", "")
            if risco_dengue in ["Alto", "Médio"]:
                indicators.append({
                    "nome": "Criadouros de Aedes aegypti",
                    "baseline": "Presentes",
                    "meta": "Zero criadouros",
                    "metodo": "Inspeção visual mensal"
                })

            monitoring_plan["indicadores_principais"] = indicators

            # Generate collection methods
            monitoring_plan["metodos_coleta"] = {
                "imagens_aereas": "Drone ou satélite para cobertura vegetal",
                "transectos": "Caminhadas para fauna e flora",
                "armadilhas": "Monitoramento de insetos vetores",
                "parcelas_permanentes": "Acompanhamento de crescimento",
                "entrevistas": "Percepção da comunidade"
            }

            # Generate responsible parties
            monitoring_plan["responsaveis_monitoramento"] = [
                {
                    "responsavel": "Equipe técnica",
                    "indicadores": ["Cobertura vegetal", "Espécies invasoras"],
                    "frequencia": "Mensal"
                },
                {
                    "responsavel": "Universidade parceira",
                    "indicadores": ["Biodiversidade", "Qualidade do solo"],
                    "frequencia": "Semestral"
                },
                {
                    "responsavel": "Comunidade local",
                    "indicadores": ["Criadouros de vetores", "Vigilância geral"],
                    "frequencia": "Contínua"
                }
            ]

            # Generate evaluation schedule
            duration_months = recovery_plan.get("duracao_total_meses", 24)
            evaluations = []

            for month in [3, 6, 12, 18, 24, 36]:
                if month <= duration_months:
                    evaluations.append({
                        "mes": month,
                        "tipo": "Avaliação intermediária" if month < duration_months else "Avaliação final",
                        "indicadores": "Todos os indicadores principais",
                        "relatorio": f"Relatório de {month} meses"
                    })

            monitoring_plan["cronograma_avaliacoes"] = evaluations

            # Generate report schedule
            monitoring_plan["relatorios_previstos"] = [
                {
                    "tipo": "Relatório mensal",
                    "conteudo": "Progresso das ações, indicadores básicos",
                    "responsavel": "Equipe técnica"
                },
                {
                    "tipo": "Relatório semestral",
                    "conteudo": "Avaliação completa de indicadores",
                    "responsavel": "Coordenação do projeto"
                },
                {
                    "tipo": "Relatório final",
                    "conteudo": "Avaliação completa do projeto e recomendações",
                    "responsavel": "Equipe técnica + Universidade"
                }
            ]

            self.logger.debug(
                "Monitoring plan generated",
                request_id=str(request_id),
                indicators_count=len(indicators),
                evaluations_count=len(evaluations)
            )

            return monitoring_plan

        except Exception as e:
            self.logger.warning(
                "Monitoring plan generation failed",
                request_id=str(request_id),
                error=str(e)
            )

            # Return basic monitoring plan
            return {
                "frequencia_monitoramento": {
                    "mensal": ["Progresso geral"],
                    "semestral": ["Avaliação de resultados"]
                },
                "indicadores_principais": [
                    {
                        "nome": "Progresso geral",
                        "baseline": "0%",
                        "meta": "100%",
                        "metodo": "Avaliação visual"
                    }
                ],
                "metodos_coleta": {"visual": "Inspeção visual"},
                "responsaveis_monitoramento": [
                    {
                        "responsavel": "Equipe técnica",
                        "indicadores": ["Progresso geral"],
                        "frequencia": "Mensal"
                    }
                ],
                "cronograma_avaliacoes": [
                    {
                        "mes": 12,
                        "tipo": "Avaliação final",
                        "indicadores": "Progresso geral",
                        "relatorio": "Relatório final"
                    }
                ],
                "relatorios_previstos": [
                    {
                        "tipo": "Relatório final",
                        "conteudo": "Avaliação do projeto",
                        "responsavel": "Equipe técnica"
                    }
                ]
            }

    async def _generate_fallback_recovery_context(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """Generate fallback recovery context when RAG is unavailable"""
        try:
            strategies = []

            # Generate strategies based on image analysis
            especies_invasoras = image_analysis.get("especies_invasoras", [])
            if especies_invasoras:
                strategies.append({
                    "title": "Controle de Espécies Invasoras",
                    "content": "Implementar programa de remoção manual e controle biológico das espécies invasoras identificadas, com monitoramento contínuo para prevenir reinfestação.",
                    "source": "Conhecimento Base",
                    "relevance": 0.9
                })

            risco_dengue = image_analysis.get("risco_dengue", "")
            if risco_dengue in ["Alto", "Médio"]:
                strategies.append({
                    "title": "Controle de Vetores de Doenças",
                    "content": "Eliminação sistemática de criadouros de Aedes aegypti através de remoção de recipientes com água parada e manejo ambiental adequado.",
                    "source": "Manual de Controle de Vetores",
                    "relevance": 0.95
                })

            cobertura_vegetal = image_analysis.get("cobertura_vegetal", 0.5)
            if cobertura_vegetal < 0.6:
                strategies.append({
                    "title": "Revegetação com Espécies Nativas",
                    "content": "Programa de plantio de espécies nativas adequadas ao bioma local, com preparação do solo e cuidados de estabelecimento.",
                    "source": "Guia de Restauração Ecológica",
                    "relevance": 0.85
                })

            # Generate strategies based on ecosystem analysis
            viabilidade = ecosystem_analysis.get("viabilidade_restauracao", "")
            if viabilidade == "Baixa":
                strategies.append({
                    "title": "Recuperação de Áreas Degradadas",
                    "content": "Técnicas intensivas de recuperação incluindo correção do solo, controle de erosão e estabelecimento gradual de vegetação.",
                    "source": "Manual de Recuperação",
                    "relevance": 0.8
                })

            ameacas = ecosystem_analysis.get("ameacas_identificadas", [])
            if "fragmentação" in str(ameacas).lower():
                strategies.append({
                    "title": "Conectividade de Habitats",
                    "content": "Criação de corredores ecológicos e stepping stones para conectar fragmentos de habitat e facilitar o fluxo gênico.",
                    "source": "Ecologia da Paisagem",
                    "relevance": 0.75
                })

            # Add general strategies
            strategies.extend([
                {
                    "title": "Monitoramento Ambiental",
                    "content": "Sistema de monitoramento contínuo dos indicadores ambientais para acompanhar o progresso da recuperação.",
                    "source": "Protocolos de Monitoramento",
                    "relevance": 0.8
                },
                {
                    "title": "Educação Ambiental",
                    "content": "Programa de educação ambiental para envolver a comunidade local na conservação e manutenção da área recuperada.",
                    "source": "Educação Ambiental",
                    "relevance": 0.7
                }
            ])

            return {
                "strategies": strategies,
                "relevance_score": 0.8,
                "total_strategies": len(strategies),
                "source": "fallback_generation"
            }

        except Exception as e:
            self.logger.error(
                "Fallback context generation failed",
                request_id=str(request_id),
                error=str(e)
            )

            return {
                "strategies": [
                    {
                        "title": "Recuperação Ambiental Básica",
                        "content": "Implementar ações básicas de recuperação ambiental adequadas ao contexto local.",
                        "source": "Conhecimento Geral",
                        "relevance": 0.6
                    }
                ],
                "relevance_score": 0.6,
                "total_strategies": 1,
                "source": "minimal_fallback"
            }

    async def _generate_fallback_plan(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        area_size: float,
        request_id: UUID
    ) -> Dict[str, Any]:
        """Generate fallback recovery plan when Gemini fails"""
        try:
            # Generate basic actions based on analysis
            acoes = []
            action_id = 1

            # Always include assessment
            acoes.append({
                "id": action_id,
                "categoria": "monitoramento",
                "titulo": "Diagnóstico detalhado da área",
                "descricao": "Realizar levantamento completo das condições ambientais da área",
                "prioridade": "Alta",
                "recursos_necessarios": ["Equipe técnica", "Equipamentos de medição"],
                "custo_estimado": 3000.0,
                "duracao_dias": 30,
                "responsavel": "Equipe técnica especializada",
                "pre_requisitos": [],
                "resultados_esperados": ["Relatório de diagnóstico completo"]
            })
            action_id += 1

            # Add invasive species control if needed
            especies_invasoras = image_analysis.get("especies_invasoras", [])
            if especies_invasoras:
                acoes.append({
                    "id": action_id,
                    "categoria": "controle_invasoras",
                    "titulo": "Controle de espécies invasoras",
                    "descricao": f"Remoção e controle das espécies invasoras identificadas: {', '.join([e.get('nome', '') for e in especies_invasoras[:3]])}",
                    "prioridade": "Alta",
                    "recursos_necessarios": ["Equipe de campo", "Ferramentas de remoção"],
                    "custo_estimado": area_size * 0.05,  # R$ 0.05 per m²
                    "duracao_dias": 60,
                    "responsavel": "Equipe de manejo",
                    "pre_requisitos": [1],
                    "resultados_esperados": ["Redução de 80% das espécies invasoras"]
                })
                action_id += 1

            # Add vector control if needed
            risco_dengue = image_analysis.get("risco_dengue", "")
            if risco_dengue in ["Alto", "Médio"]:
                acoes.append({
                    "id": action_id,
                    "categoria": "controle_vetores",
                    "titulo": "Eliminação de criadouros de Aedes aegypti",
                    "descricao": "Remoção de recipientes com água parada e manejo para prevenir formação de criadouros",
                    "prioridade": "Alta",
                    "recursos_necessarios": ["Equipe de campo", "Materiais de vedação"],
                    "custo_estimado": 1500.0,
                    "duracao_dias": 15,
                    "responsavel": "Equipe de saúde ambiental",
                    "pre_requisitos": [1],
                    "resultados_esperados": ["Zero criadouros identificados"]
                })
                action_id += 1

            # Add revegetation if needed
            cobertura_vegetal = image_analysis.get("cobertura_vegetal", 0.5)
            if cobertura_vegetal < 0.7:
                mudas_necessarias = int((area_size * (0.8 - cobertura_vegetal)) / 4)  # 1 muda per 4m²
                acoes.append({
                    "id": action_id,
                    "categoria": "revegetacao",
                    "titulo": "Plantio de espécies nativas",
                    "descricao": f"Plantio de aproximadamente {mudas_necessarias} mudas de espécies nativas adequadas ao bioma",
                    "prioridade": "Média",
                    "recursos_necessarios": [f"{mudas_necessarias} mudas nativas", "Ferramentas de plantio", "Sistema de irrigação"],
                    "custo_estimado": mudas_necessarias * 15.0,  # R$ 15 per seedling
                    "duracao_dias": 45,
                    "responsavel": "Equipe de revegetação",
                    "pre_requisitos": [1, 2] if especies_invasoras else [1],
                    "resultados_esperados": ["80% de sobrevivência das mudas"]
                })
                action_id += 1

            # Add monitoring
            acoes.append({
                "id": action_id,
                "categoria": "monitoramento",
                "titulo": "Monitoramento contínuo",
                "descricao": "Sistema de monitoramento dos indicadores ambientais e progresso da recuperação",
                "prioridade": "Média",
                "recursos_necessarios": ["Equipamentos de monitoramento", "Sistema de registro"],
                "custo_estimado": 2000.0,
                "duracao_dias": 365,
                "responsavel": "Equipe de monitoramento",
                "pre_requisitos": list(range(1, action_id)),
                "resultados_esperados": ["Relatórios mensais de progresso"]
            })

            # Calculate total cost
            total_cost = sum([action.get("custo_estimado", 0) for action in acoes])

            # Generate basic timeline
            cronograma = {
                "fase_1_imediato": {
                    "periodo": "0-3 meses",
                    "acoes_ids": [1, 2] if len(acoes) > 1 else [1],
                    "objetivo": "Diagnóstico e ações emergenciais",
                    "custo_fase": sum([a.get("custo_estimado", 0) for a in acoes[:2]])
                },
                "fase_2_curto_prazo": {
                    "periodo": "3-12 meses",
                    "acoes_ids": list(range(3, min(len(acoes), 5) + 1)),
                    "objetivo": "Implementação das ações principais",
                    "custo_fase": sum([a.get("custo_estimado", 0) for a in acoes[2:4]])
                },
                "fase_3_medio_prazo": {
                    "periodo": "1-2 anos",
                    "acoes_ids": [len(acoes)] if len(acoes) > 4 else [],
                    "objetivo": "Monitoramento e manutenção",
                    "custo_fase": acoes[-1].get("custo_estimado", 0) if acoes else 0
                },
                "fase_4_longo_prazo": {
                    "periodo": "2+ anos",
                    "acoes_ids": [],
                    "objetivo": "Monitoramento de longo prazo",
                    "custo_fase": 0.0
                }
            }

            return {
                "resumo_executivo": f"Plano de recuperação para área de {area_size:,.0f} m² com foco em {len(acoes)} ações prioritárias",
                "objetivo_principal": "Recuperar e restaurar o ecossistema local através de ações baseadas no diagnóstico ambiental",
                "acoes": acoes,
                "cronograma": cronograma,
                "custo_total_estimado": total_cost,
                "duracao_total_meses": 24,
                "metricas_sucesso": self._generate_default_metrics(image_analysis, ecosystem_analysis),
                "riscos_contingencias": self._generate_default_risks(),
                "responsaveis": self._generate_default_responsaveis(),
                "confianca_geral": 0.7
            }

        except Exception as e:
            self.logger.error(
                "Fallback plan generation failed",
                request_id=str(request_id),
                error=str(e)
            )

            # Return minimal plan
            return {
                "resumo_executivo": "Plano básico de recuperação ambiental",
                "objetivo_principal": "Recuperar área degradada",
                "acoes": [
                    {
                        "id": 1,
                        "categoria": "monitoramento",
                        "titulo": "Avaliação da área",
                        "descricao": "Diagnóstico básico da área",
                        "prioridade": "Alta",
                        "recursos_necessarios": ["Equipe técnica"],
                        "custo_estimado": 2000.0,
                        "duracao_dias": 30,
                        "responsavel": "Equipe técnica",
                        "pre_requisitos": [],
                        "resultados_esperados": ["Diagnóstico completo"]
                    }
                ],
                "cronograma": {
                    "fase_1_imediato": {
                        "periodo": "0-3 meses",
                        "acoes_ids": [1],
                        "objetivo": "Diagnóstico",
                        "custo_fase": 2000.0
                    }
                },
                "custo_total_estimado": 2000.0,
                "duracao_total_meses": 12,
                "metricas_sucesso": [],
                "riscos_contingencias": [],
                "responsaveis": [],
                "confianca_geral": 0.5
            }

    def _extract_plan_from_text(self, response_text: str, request_id: UUID) -> Dict[str, Any]:
        """Extract basic plan from text when JSON parsing fails"""
        try:
            # This is a simplified extraction - in production would be more sophisticated
            return {
                "resumo_executivo": "Plano extraído de resposta textual",
                "objetivo_principal": "Recuperação ambiental baseada em análise",
                "acoes": [
                    {
                        "id": 1,
                        "categoria": "monitoramento",
                        "titulo": "Ação baseada em texto",
                        "descricao": response_text[:200] if response_text else "Descrição não disponível",
                        "prioridade": "Média",
                        "recursos_necessarios": ["Recursos básicos"],
                        "custo_estimado": 5000.0,
                        "duracao_dias": 60,
                        "responsavel": "Equipe técnica",
                        "pre_requisitos": [],
                        "resultados_esperados": ["Resultados baseados em texto"]
                    }
                ],
                "cronograma": {
                    "fase_1_imediato": {
                        "periodo": "0-6 meses",
                        "acoes_ids": [1],
                        "objetivo": "Implementação básica",
                        "custo_fase": 5000.0
                    }
                },
                "custo_total_estimado": 5000.0,
                "duracao_total_meses": 12,
                "metricas_sucesso": [],
                "riscos_contingencias": [],
                "responsaveis": [],
                "confianca_geral": 0.4
            }
        except Exception:
            return {
                "resumo_executivo": "Plano mínimo de recuperação",
                "objetivo_principal": "Recuperação básica",
                "acoes": [],
                "cronograma": {},
                "custo_total_estimado": 0.0,
                "duracao_total_meses": 12,
                "metricas_sucesso": [],
                "riscos_contingencias": [],
                "responsaveis": [],
                "confianca_geral": 0.3
            }

    def _calculate_plan_completeness(self, plan: Dict[str, Any]) -> float:
        """Calculate plan completeness score"""
        try:
            score = 0.0

            # Check required fields
            required_fields = [
                "resumo_executivo", "objetivo_principal", "acoes", "cronograma",
                "custo_total_estimado", "metricas_sucesso", "responsaveis"
            ]

            for field in required_fields:
                if field in plan and plan[field]:
                    if isinstance(plan[field], list):
                        score += 0.1 if len(plan[field]) > 0 else 0
                    else:
                        score += 0.1

            # Bonus for detailed actions
            acoes = plan.get("acoes", [])
            if len(acoes) >= 5:
                score += 0.2
            elif len(acoes) >= 3:
                score += 0.1

            # Bonus for detailed timeline
            cronograma = plan.get("cronograma", {})
            if len(cronograma) >= 3:
                score += 0.1

            return min(1.0, score)

        except Exception:
            return 0.5

    def _assess_feasibility(self, plan: Dict[str, Any]) -> float:
        """Assess implementation feasibility"""
        try:
            feasibility = 0.8  # Base feasibility

            # Adjust based on cost
            total_cost = plan.get("custo_total_estimado", 0)
            if total_cost > 100000:
                feasibility -= 0.2
            elif total_cost > 50000:
                feasibility -= 0.1

            # Adjust based on duration
            duration = plan.get("duracao_total_meses", 12)
            if duration > 48:
                feasibility -= 0.2
            elif duration > 24:
                feasibility -= 0.1

            # Adjust based on action complexity
            acoes = plan.get("acoes", [])
            complex_actions = [a for a in acoes if a.get("duracao_dias", 30) > 90]
            if len(complex_actions) > len(acoes) * 0.5:
                feasibility -= 0.1

            return max(0.3, min(1.0, feasibility))

        except Exception:
            return 0.7

    def _assess_plan_complexity(self, plan: Dict[str, Any]) -> str:
        """Assess plan complexity level"""
        try:
            acoes_count = len(plan.get("acoes", []))
            total_cost = plan.get("custo_total_estimado", 0)
            duration = plan.get("duracao_total_meses", 12)

            complexity_score = 0

            if acoes_count > 10:
                complexity_score += 2
            elif acoes_count > 5:
                complexity_score += 1

            if total_cost > 50000:
                complexity_score += 2
            elif total_cost > 20000:
                complexity_score += 1

            if duration > 36:
                complexity_score += 2
            elif duration > 18:
                complexity_score += 1

            if complexity_score >= 5:
                return "Alta"
            elif complexity_score >= 3:
                return "Média"
            else:
                return "Baixa"

        except Exception:
            return "Média"
    
    async def _generate_plan_with_gemini(
        self,
        image_analysis: Dict[str, Any],
        ecosystem_analysis: Dict[str, Any],
        synthesis: Dict[str, Any],
        recovery_context: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate recovery plan with Gemini Pro
        
        Args:
            image_analysis: Image analysis results
            ecosystem_analysis: Ecosystem analysis results
            synthesis: Synthesis results
            recovery_context: Recovery strategies from RAG
            request_id: Request ID
            
        Returns:
            Recovery plan
        """
        try:
            # Prepare context from recovery strategies
            strategies_text = "\n".join([
                f"- {strategy['title']}: {strategy['content'][:150]}..."
                for strategy in recovery_context.get("strategies", [])
            ])
            
            # Build comprehensive prompt
            plan_prompt = f"""
            Como especialista em recuperação ambiental, desenvolva um plano detalhado baseado nas análises:

            ANÁLISE DE IMAGEM:
            - Risco Dengue: {image_analysis.get('risco_dengue', 'N/A')}
            - Espécies Invasoras: {[s.get('nome') for s in image_analysis.get('especies_invasoras', [])]}
            - Cobertura Vegetal: {image_analysis.get('cobertura_vegetal', 'N/A')}

            ANÁLISE DE ECOSSISTEMA:
            - Tipo: {ecosystem_analysis.get('tipo_ecossistema', 'N/A')}
            - Viabilidade: {ecosystem_analysis.get('viabilidade_restauracao', 'N/A')}
            - Ameaças: {ecosystem_analysis.get('ameacas_identificadas', [])}

            SÍNTESE:
            - Prioridades: {synthesis.get('prioridades', [])}
            - Abordagem: {synthesis.get('abordagem_integrada', 'N/A')}

            ESTRATÉGIAS DISPONÍVEIS:
            {strategies_text}

            Desenvolva um plano com:
            1. Ações específicas e práticas
            2. Cronograma realista
            3. Recursos necessários
            4. Métricas de sucesso

            Responda em JSON:
            {{
                "acoes": ["lista de ações específicas ordenadas por prioridade"],
                "cronograma": {{
                    "imediato": ["ações para 0-3 meses"],
                    "curto_prazo": ["ações para 3-12 meses"],
                    "medio_prazo": ["ações para 1-3 anos"],
                    "longo_prazo": ["ações para 3+ anos"]
                }},
                "recursos_necessarios": ["lista de recursos"],
                "custo_estimado": "estimativa de custo",
                "metricas_sucesso": ["indicadores de sucesso"],
                "responsaveis": ["atores envolvidos"],
                "confianca_geral": 0.0-1.0
            }}
            """
            
            # Generate with Gemini Pro (simulated for now)
            # In real implementation:
            # response = await asyncio.to_thread(
            #     self.model.generate_content,
            #     plan_prompt
            # )
            # import json
            # recovery_plan = json.loads(response.text)
            
            # Simulated recovery plan
            simulated_plan = {
                "acoes": [
                    "Remoção imediata de caramujos africanos identificados",
                    "Eliminação de criadouros de Aedes aegypti",
                    "Plantio de espécies nativas para aumentar cobertura vegetal",
                    "Instalação de sistema de monitoramento ambiental",
                    "Educação ambiental para comunidade local"
                ],
                "cronograma": {
                    "imediato": [
                        "Remoção de espécies invasoras",
                        "Eliminação de água parada"
                    ],
                    "curto_prazo": [
                        "Plantio de mudas nativas",
                        "Instalação de monitoramento"
                    ],
                    "medio_prazo": [
                        "Consolidação da vegetação",
                        "Programa de educação ambiental"
                    ],
                    "longo_prazo": [
                        "Monitoramento de longo prazo",
                        "Expansão da área recuperada"
                    ]
                },
                "recursos_necessarios": [
                    "Mudas de espécies nativas",
                    "Equipamentos de remoção",
                    "Sistema de monitoramento",
                    "Equipe técnica especializada"
                ],
                "custo_estimado": "R$ 15.000 - R$ 25.000",
                "metricas_sucesso": [
                    "Redução de 90% das espécies invasoras",
                    "Aumento de 50% na cobertura vegetal",
                    "Zero criadouros de Aedes aegypti",
                    "Estabelecimento de 80% das mudas plantadas"
                ],
                "responsaveis": [
                    "Órgão ambiental municipal",
                    "ONGs ambientais",
                    "Comunidade local",
                    "Universidades parceiras"
                ],
                "confianca_geral": 0.85
            }
            
            self.logger.debug(
                "Recovery plan generated",
                request_id=str(request_id),
                actions_count=len(simulated_plan["acoes"])
            )
            
            return simulated_plan
            
        except Exception as e:
            self.logger.error(
                "Plan generation with Gemini failed",
                request_id=str(request_id),
                error=str(e)
            )
            
            # Return minimal fallback plan
            return {
                "acoes": [
                    "Avaliação detalhada da área",
                    "Remoção de elementos degradantes",
                    "Plantio de espécies adequadas",
                    "Monitoramento contínuo"
                ],
                "cronograma": {
                    "imediato": ["Avaliação inicial"],
                    "curto_prazo": ["Intervenções básicas"],
                    "medio_prazo": ["Consolidação"],
                    "longo_prazo": ["Monitoramento"]
                },
                "recursos_necessarios": ["Recursos básicos de recuperação"],
                "custo_estimado": "A definir",
                "metricas_sucesso": ["Melhoria geral do ambiente"],
                "responsaveis": ["Equipe técnica"],
                "confianca_geral": 0.6
            }
