"""
Ecosystem Balance Agent - Specialized in Gemma 3 + RAG for biodiversity analysis
"""

import asyncio
import json
import httpx
from typing import Any, Dict, List, Optional
from uuid import UUID

import structlog

from .base import BaseAgent
from ..config import settings
from ..utils.exceptions import AnalysisError, ServiceError, ValidationError


class EcosystemBalanceAgent(BaseAgent):
    """
    Ecosystem Balance Agent using Gemma 3 + RAG
    Specialized in biodiversity and ecological balance analysis
    """
    
    def __init__(self):
        super().__init__(
            name="ecosystem_balance",
            version="1.0.0",
            timeout_seconds=180.0,  # 3 minutes for ecosystem analysis
            max_retries=3
        )

        self.gpu_service_url = settings.gpu_service_url
        self.rag_service_url = settings.rag_service_url

        self.logger = structlog.get_logger("agent.ecosystem_balance")

        # Ecosystem types mapping for Brazilian biomes
        self.biome_mapping = {
            "amazonia": "Amazônia",
            "cerrado": "Cerrado",
            "mata_atlantica": "Mata Atlântica",
            "caatinga": "Caatinga",
            "pampa": "Pampa",
            "pantanal": "Pantanal",
            "costeiro": "Ecossistema Costeiro"
        }

        # Threat categories
        self.threat_categories = [
            "desmatamento", "fragmentacao", "especies_invasoras", "poluicao",
            "mudancas_climaticas", "urbanizacao", "agricultura", "mineracao"
        ]
    
    async def _process_request(
        self,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Process ecosystem balance analysis request
        
        Args:
            request_data: Request data
            request_id: Request ID
            
        Returns:
            Ecosystem analysis results
        """
        self.logger.info(
            "Starting ecosystem balance analysis",
            request_id=str(request_id),
            coordinates=request_data.get("coordinates")
        )
        
        try:
            # Extract and validate request data
            coordinates = request_data.get("coordinates")
            image_analysis = request_data.get("image_analysis", {})
            location_context = request_data.get("location_context", {})

            # Step 1: Get contextual data from RAG service
            rag_context = await self._get_rag_context(
                coordinates, image_analysis, location_context, request_id
            )

            # Step 2: Analyze with Gemma 3 on GPU service
            ecosystem_analysis = await self._analyze_with_gemma(
                request_data, rag_context, request_id
            )

            # Step 3: Enhance analysis with biodiversity assessment
            enhanced_analysis = await self._enhance_biodiversity_analysis(
                ecosystem_analysis, rag_context, coordinates, request_id
            )

            self.logger.info(
                "Ecosystem balance analysis completed",
                request_id=str(request_id),
                tipo_ecossistema=enhanced_analysis.get("tipo_ecossistema"),
                viabilidade=enhanced_analysis.get("viabilidade_restauracao"),
                biodiversidade_score=enhanced_analysis.get("biodiversidade_score")
            )

            return {
                "data": enhanced_analysis,
                "metadata": {
                    "model_used": settings.ecosystem_balance_model,
                    "rag_documents_used": len(rag_context.get("documents", [])),
                    "analysis_type": "gemma3_rag_enhanced",
                    "biome_detected": enhanced_analysis.get("bioma_identificado"),
                    "coordinates": coordinates
                },
                "confidence_score": enhanced_analysis.get("confianca_geral", 0.75),
                "quality_metrics": {
                    "rag_relevance": rag_context.get("relevance_score", 0.8),
                    "analysis_depth": self._calculate_analysis_depth(enhanced_analysis),
                    "biodiversity_coverage": enhanced_analysis.get("biodiversidade_score", 0.5),
                    "contextual_accuracy": rag_context.get("contextual_accuracy", 0.8)
                }
            }
            
        except Exception as e:
            self.logger.error(
                "Ecosystem balance analysis failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )
            raise AnalysisError(
                message=f"Ecosystem balance analysis failed: {str(e)}",
                analysis_id=str(request_id),
                agent_name=self.name
            )
    
    async def _get_rag_context(
        self,
        coordinates: Optional[Dict[str, float]],
        image_analysis: Dict[str, Any],
        location_context: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Get contextual information from RAG service

        Args:
            coordinates: GPS coordinates
            image_analysis: Results from image analysis
            location_context: Additional location context
            request_id: Request ID

        Returns:
            RAG context data with biodiversity information
        """
        try:
            # Build comprehensive query based on available data
            query_components = []

            # Add location-based queries
            if coordinates:
                lat, lng = coordinates.get("latitude"), coordinates.get("longitude")
                if lat and lng:
                    # Determine biome based on coordinates (simplified)
                    biome = self._determine_biome_from_coordinates(lat, lng)
                    query_components.append(f"biodiversidade {biome}")
                    query_components.append(f"espécies nativas {biome}")

            # Add image analysis context
            if image_analysis:
                especies_invasoras = image_analysis.get("especies_invasoras", [])
                for especie in especies_invasoras:
                    if isinstance(especie, dict) and "nome" in especie:
                        query_components.append(f"controle {especie['nome']}")

                cobertura_vegetal = image_analysis.get("cobertura_vegetal", 0)
                if cobertura_vegetal < 0.3:
                    query_components.append("restauração ecológica área degradada")
                elif cobertura_vegetal > 0.7:
                    query_components.append("conservação biodiversidade")

            # Build final query
            base_query = "recuperação ambiental ecossistema brasileiro"
            if query_components:
                full_query = f"{base_query} {' '.join(query_components[:3])}"
            else:
                full_query = base_query

            # Prepare RAG request
            rag_request = {
                "query": full_query,
                "coordinates": coordinates,
                "search_type": "ecosystem_biodiversity",
                "filters": {
                    "sources": ["GBIF", "IUCN", "OBIS", "eBird"],
                    "content_types": ["species", "habitat", "conservation", "restoration"]
                },
                "limit": 15,
                "include_metadata": True
            }

            self.logger.debug(
                "Sending RAG query",
                request_id=str(request_id),
                query=full_query,
                coordinates=coordinates
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
                        rag_context = response.json()

                        self.logger.info(
                            "RAG context retrieved successfully",
                            request_id=str(request_id),
                            documents_count=len(rag_context.get("documents", [])),
                            relevance_score=rag_context.get("relevance_score", 0)
                        )

                        return rag_context

                except httpx.RequestError as e:
                    self.logger.warning(
                        "RAG service request failed",
                        request_id=str(request_id),
                        error=str(e)
                    )
                except httpx.HTTPStatusError as e:
                    self.logger.warning(
                        "RAG service returned error",
                        request_id=str(request_id),
                        status_code=e.response.status_code,
                        error=str(e)
                    )

            # Fallback: Generate contextual information based on available data
            return await self._generate_fallback_context(
                coordinates, image_analysis, full_query, request_id
            )

        except Exception as e:
            self.logger.error(
                "Failed to get RAG context",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return minimal fallback context
            return {
                "documents": [],
                "relevance_score": 0.3,
                "total_documents": 0,
                "query_used": "fallback",
                "contextual_accuracy": 0.3
            }
    
    async def _analyze_with_gemma(
        self,
        request_data: Dict[str, Any],
        rag_context: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Analyze ecosystem with Gemma 3 model

        Args:
            request_data: Request data with image analysis and location info
            rag_context: RAG context with scientific data
            request_id: Request ID

        Returns:
            Ecosystem analysis results
        """
        try:
            # Build comprehensive analysis prompt
            analysis_prompt = self._build_gemma_prompt(request_data, rag_context)

            # Prepare GPU service request
            gpu_request = {
                "prompt": analysis_prompt,
                "model": settings.ecosystem_balance_model,
                "max_tokens": 1500,
                "temperature": 0.7,
                "top_p": 0.9,
                "stop_sequences": ["</analysis>"],
                "response_format": "json"
            }

            self.logger.debug(
                "Sending request to GPU service",
                request_id=str(request_id),
                model=settings.ecosystem_balance_model,
                prompt_length=len(analysis_prompt)
            )

            # Call GPU service with Gemma 3
            if self.gpu_service_url and self.gpu_service_url != "http://localhost:8003":
                try:
                    async with httpx.AsyncClient(timeout=120.0) as client:
                        response = await client.post(
                            f"{self.gpu_service_url}/api/v1/generate",
                            json=gpu_request,
                            headers={"Content-Type": "application/json"}
                        )
                        response.raise_for_status()
                        gpu_result = response.json()

                        # Parse Gemma 3 response
                        analysis_result = self._parse_gemma_response(
                            gpu_result.get("generated_text", ""), request_id
                        )

                        self.logger.info(
                            "Gemma 3 analysis completed successfully",
                            request_id=str(request_id),
                            tipo_ecossistema=analysis_result.get("tipo_ecossistema"),
                            viabilidade=analysis_result.get("viabilidade_restauracao")
                        )

                        return analysis_result

                except httpx.RequestError as e:
                    self.logger.warning(
                        "GPU service request failed",
                        request_id=str(request_id),
                        error=str(e)
                    )
                except httpx.HTTPStatusError as e:
                    self.logger.warning(
                        "GPU service returned error",
                        request_id=str(request_id),
                        status_code=e.response.status_code,
                        error=str(e)
                    )

            # Fallback: Generate analysis based on available context
            return await self._generate_fallback_analysis(
                request_data, rag_context, request_id
            )

        except Exception as e:
            self.logger.error(
                "Gemma 3 analysis failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return safe fallback
            return await self._generate_fallback_analysis(
                request_data, rag_context, request_id
            )

    def _determine_biome_from_coordinates(self, lat: float, lng: float) -> str:
        """
        Determine Brazilian biome from coordinates (simplified)

        Args:
            lat: Latitude
            lng: Longitude

        Returns:
            Biome name
        """
        # Simplified biome determination based on coordinates
        # In production, this would use more sophisticated geospatial data

        if -5 <= lat <= 5 and -75 <= lng <= -45:
            return "Amazônia"
        elif -25 <= lat <= -5 and -60 <= lng <= -40:
            return "Cerrado"
        elif -30 <= lat <= -10 and -50 <= lng <= -35:
            return "Mata Atlântica"
        elif -15 <= lat <= 0 and -45 <= lng <= -35:
            return "Caatinga"
        elif -35 <= lat <= -25 and -60 <= lng <= -50:
            return "Pampa"
        elif -22 <= lat <= -15 and -60 <= lng <= -55:
            return "Pantanal"
        elif lat < -20 and lng > -50:
            return "Ecossistema Costeiro"
        else:
            return "Ecossistema Brasileiro"

    async def _generate_fallback_context(
        self,
        coordinates: Optional[Dict[str, float]],
        image_analysis: Dict[str, Any],
        query: str,
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate fallback context when RAG service is unavailable

        Args:
            coordinates: GPS coordinates
            image_analysis: Image analysis results
            query: Original query
            request_id: Request ID

        Returns:
            Fallback context data
        """
        try:
            documents = []

            # Generate context based on coordinates
            if coordinates:
                lat, lng = coordinates.get("latitude"), coordinates.get("longitude")
                if lat and lng:
                    biome = self._determine_biome_from_coordinates(lat, lng)
                    documents.append({
                        "title": f"Características do {biome}",
                        "content": self._get_biome_characteristics(biome),
                        "source": "Sistema Local",
                        "relevance": 0.8,
                        "type": "biome_info"
                    })

            # Generate context based on image analysis
            if image_analysis:
                especies_invasoras = image_analysis.get("especies_invasoras", [])
                if especies_invasoras:
                    for especie in especies_invasoras[:2]:  # Limit to 2 species
                        if isinstance(especie, dict) and "nome" in especie:
                            documents.append({
                                "title": f"Controle de {especie['nome']}",
                                "content": self._get_invasive_species_info(especie['nome']),
                                "source": "Base de Conhecimento",
                                "relevance": 0.7,
                                "type": "species_control"
                            })

                cobertura = image_analysis.get("cobertura_vegetal", 0.5)
                if cobertura < 0.4:
                    documents.append({
                        "title": "Técnicas de Restauração Ecológica",
                        "content": "Restauração de áreas degradadas através de plantio de espécies nativas, controle de erosão e manejo adequado do solo.",
                        "source": "Guia de Restauração",
                        "relevance": 0.9,
                        "type": "restoration"
                    })

            # Add general biodiversity context
            documents.append({
                "title": "Biodiversidade Brasileira",
                "content": "O Brasil possui uma das maiores biodiversidades do mundo, com milhões de espécies distribuídas em diferentes biomas.",
                "source": "Conhecimento Geral",
                "relevance": 0.6,
                "type": "general"
            })

            return {
                "documents": documents,
                "relevance_score": 0.7,
                "total_documents": len(documents),
                "query_used": query,
                "contextual_accuracy": 0.6,
                "source": "fallback_generation"
            }

        except Exception as e:
            self.logger.error(
                "Fallback context generation failed",
                request_id=str(request_id),
                error=str(e)
            )

            return {
                "documents": [],
                "relevance_score": 0.3,
                "total_documents": 0,
                "query_used": query,
                "contextual_accuracy": 0.3,
                "source": "minimal_fallback"
            }

    def _get_biome_characteristics(self, biome: str) -> str:
        """
        Get characteristics of Brazilian biomes

        Args:
            biome: Biome name

        Returns:
            Biome characteristics description
        """
        characteristics = {
            "Amazônia": "Floresta tropical úmida com alta biodiversidade, solos pobres, clima quente e úmido. Rica em espécies arbóreas, epífitas e fauna diversificada.",
            "Cerrado": "Savana tropical com vegetação de gramíneas e árvores esparsas. Solo ácido, estações seca e chuvosa bem definidas. Importante para recursos hídricos.",
            "Mata Atlântica": "Floresta tropical costeira altamente ameaçada. Alta biodiversidade e endemismo. Clima tropical úmido, relevo montanhoso.",
            "Caatinga": "Vegetação xerófila adaptada ao clima semiárido. Plantas com espinhos, caules suculentos. Importante para populações rurais.",
            "Pampa": "Campos nativos com gramíneas. Clima subtropical, relevo de planícies. Importante para pecuária sustentável.",
            "Pantanal": "Maior planície alagável do mundo. Biodiversidade aquática e terrestre. Ciclos de cheia e seca.",
            "Ecossistema Costeiro": "Manguezais, restingas, dunas. Importante para reprodução de espécies marinhas e proteção costeira."
        }

        return characteristics.get(biome, "Ecossistema brasileiro com características específicas da região.")

    def _get_invasive_species_info(self, species_name: str) -> str:
        """
        Get information about invasive species control

        Args:
            species_name: Species name

        Returns:
            Control information
        """
        species_info = {
            "Caramujo-africano": "Controle através de coleta manual, barreiras físicas e manejo integrado. Evitar uso de moluscicidas que afetam fauna nativa.",
            "Baronesa": "Remoção mecânica, controle biológico com insetos específicos. Monitoramento constante de corpos d'água.",
            "Capim-colonião": "Roçada antes da floração, plantio de espécies nativas competitivas, manejo do solo.",
            "Achatina fulica": "Coleta manual com proteção, destinação adequada, educação ambiental para prevenção."
        }

        for key in species_info:
            if key.lower() in species_name.lower():
                return species_info[key]

        return "Controle de espécie invasora através de métodos integrados, priorizando técnicas que não prejudiquem a fauna nativa."

    def _build_gemma_prompt(
        self,
        request_data: Dict[str, Any],
        rag_context: Dict[str, Any]
    ) -> str:
        """
        Build comprehensive prompt for Gemma 3 analysis

        Args:
            request_data: Request data
            rag_context: RAG context

        Returns:
            Analysis prompt
        """
        # Extract data
        coordinates = request_data.get("coordinates", {})
        image_analysis = request_data.get("image_analysis", {})
        filename = request_data.get("filename", "N/A")

        # Build context section
        context_docs = rag_context.get("documents", [])
        context_text = ""
        if context_docs:
            context_text = "\n".join([
                f"• {doc.get('title', 'Documento')}: {doc.get('content', '')[:300]}..."
                for doc in context_docs[:5]  # Limit to 5 most relevant documents
            ])
        else:
            context_text = "Contexto científico limitado disponível."

        # Build image analysis section
        image_context = ""
        if image_analysis:
            especies_invasoras = image_analysis.get("especies_invasoras", [])
            cobertura_vegetal = image_analysis.get("cobertura_vegetal", 0)
            sinais_degradacao = image_analysis.get("sinais_degradacao", [])

            image_context = f"""
ANÁLISE DE IMAGEM DISPONÍVEL:
- Cobertura vegetal: {cobertura_vegetal:.1%}
- Espécies invasoras detectadas: {len(especies_invasoras)}
- Sinais de degradação: {', '.join(sinais_degradacao[:3]) if sinais_degradacao else 'Nenhum identificado'}
"""

            if especies_invasoras:
                especies_text = ", ".join([
                    esp.get("nome", "Espécie não identificada")
                    for esp in especies_invasoras[:3]
                ])
                image_context += f"- Espécies invasoras: {especies_text}\n"

        # Build location section
        location_context = ""
        if coordinates:
            lat, lng = coordinates.get("latitude"), coordinates.get("longitude")
            if lat and lng:
                biome = self._determine_biome_from_coordinates(lat, lng)
                location_context = f"""
CONTEXTO GEOGRÁFICO:
- Coordenadas: {lat:.4f}, {lng:.4f}
- Bioma provável: {biome}
- Características do bioma: {self._get_biome_characteristics(biome)[:200]}...
"""

        # Build complete prompt
        prompt = f"""
Você é um especialista em ecologia e recuperação ambiental com foco no Brasil. Analise o ecossistema com base nos dados disponíveis e forneça uma avaliação científica detalhada.

CONTEXTO CIENTÍFICO:
{context_text}

{location_context}

{image_context}

ARQUIVO ANALISADO: {filename}

INSTRUÇÕES:
1. Identifique o tipo de ecossistema com base em todos os dados disponíveis
2. Avalie a condição atual do ambiente
3. Calcule um score de biodiversidade (0.0 a 1.0)
4. Determine a viabilidade de restauração (Alta/Média/Baixa)
5. Liste espécies nativas esperadas para a região
6. Identifique principais ameaças ao ecossistema
7. Forneça um resumo com recomendações práticas

RESPONDA EXCLUSIVAMENTE EM JSON VÁLIDO:
{{
    "tipo_ecossistema": "Nome específico do ecossistema identificado",
    "bioma_identificado": "Bioma brasileiro correspondente",
    "condicao_geral": "Descrição detalhada da condição atual",
    "biodiversidade_score": 0.0-1.0,
    "viabilidade_restauracao": "Alta|Média|Baixa",
    "especies_nativas_esperadas": [
        "Lista de 5-10 espécies nativas típicas da região"
    ],
    "ameacas_identificadas": [
        "Lista das principais ameaças ao ecossistema"
    ],
    "indicadores_ecologicos": {{
        "conectividade": 0.0-1.0,
        "integridade_habitat": 0.0-1.0,
        "pressao_antropica": 0.0-1.0
    }},
    "recomendacoes_prioritarias": [
        "Lista de 3-5 recomendações específicas e práticas"
    ],
    "resumo": "Resumo executivo da análise com foco em ações práticas",
    "confianca_geral": 0.0-1.0
}}
"""

        return prompt

    def _parse_gemma_response(self, response_text: str, request_id: UUID) -> Dict[str, Any]:
        """
        Parse Gemma 3 response and extract JSON

        Args:
            response_text: Raw response from Gemma 3
            request_id: Request ID

        Returns:
            Parsed analysis results
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
            result = json.loads(json_text)

            # Validate and normalize result
            result = self._validate_gemma_result(result, request_id)

            self.logger.debug(
                "Successfully parsed Gemma response",
                request_id=str(request_id),
                tipo_ecossistema=result.get("tipo_ecossistema"),
                viabilidade=result.get("viabilidade_restauracao")
            )

            return result

        except Exception as e:
            self.logger.warning(
                "Failed to parse Gemma response, using text extraction",
                request_id=str(request_id),
                error=str(e),
                response_preview=response_text[:200] if response_text else None
            )

            # Fallback: extract information from text
            return self._extract_from_text_response(response_text, request_id)

    def _validate_gemma_result(self, result: Dict[str, Any], request_id: UUID) -> Dict[str, Any]:
        """
        Validate and normalize Gemma analysis result

        Args:
            result: Raw result from Gemma
            request_id: Request ID

        Returns:
            Validated and normalized result
        """
        try:
            # Ensure required fields
            required_fields = {
                "tipo_ecossistema": "Ecossistema brasileiro",
                "bioma_identificado": "Não identificado",
                "condicao_geral": "Condição não determinada",
                "biodiversidade_score": 0.5,
                "viabilidade_restauracao": "Média",
                "especies_nativas_esperadas": [],
                "ameacas_identificadas": [],
                "resumo": "Análise em processamento",
                "confianca_geral": 0.6
            }

            for field, default_value in required_fields.items():
                if field not in result:
                    result[field] = default_value

            # Validate data types and ranges
            if not isinstance(result["especies_nativas_esperadas"], list):
                result["especies_nativas_esperadas"] = []

            if not isinstance(result["ameacas_identificadas"], list):
                result["ameacas_identificadas"] = []

            # Validate scores (0.0 to 1.0)
            score_fields = ["biodiversidade_score", "confianca_geral"]
            for field in score_fields:
                if field in result:
                    try:
                        score = float(result[field])
                        result[field] = max(0.0, min(1.0, score))
                    except (ValueError, TypeError):
                        result[field] = 0.5

            # Validate viability levels
            valid_viability = ["Alta", "Média", "Baixa"]
            if result["viabilidade_restauracao"] not in valid_viability:
                result["viabilidade_restauracao"] = "Média"

            # Add missing optional fields
            if "indicadores_ecologicos" not in result:
                result["indicadores_ecologicos"] = {
                    "conectividade": 0.5,
                    "integridade_habitat": 0.5,
                    "pressao_antropica": 0.5
                }

            if "recomendacoes_prioritarias" not in result:
                result["recomendacoes_prioritarias"] = [
                    "Avaliação detalhada do ecossistema",
                    "Controle de espécies invasoras",
                    "Plantio de espécies nativas"
                ]

            return result

        except Exception as e:
            self.logger.error(
                "Result validation failed",
                request_id=str(request_id),
                error=str(e)
            )

            # Return safe default
            return {
                "tipo_ecossistema": "Ecossistema brasileiro",
                "bioma_identificado": "Não identificado",
                "condicao_geral": "Análise limitada disponível",
                "biodiversidade_score": 0.5,
                "viabilidade_restauracao": "Média",
                "especies_nativas_esperadas": ["Análise em desenvolvimento"],
                "ameacas_identificadas": ["Avaliação em andamento"],
                "indicadores_ecologicos": {
                    "conectividade": 0.5,
                    "integridade_habitat": 0.5,
                    "pressao_antropica": 0.5
                },
                "recomendacoes_prioritarias": [
                    "Análise detalhada necessária"
                ],
                "resumo": "Análise de ecossistema com dados limitados",
                "confianca_geral": 0.4
            }

    def _extract_from_text_response(self, response_text: str, request_id: UUID) -> Dict[str, Any]:
        """
        Extract analysis information from text response when JSON parsing fails

        Args:
            response_text: Raw text response
            request_id: Request ID

        Returns:
            Extracted analysis results
        """
        try:
            text_lower = response_text.lower() if response_text else ""

            # Extract ecosystem type
            tipo_ecossistema = "Ecossistema brasileiro"
            for biome in self.biome_mapping.values():
                if biome.lower() in text_lower:
                    tipo_ecossistema = f"{biome} (identificado por texto)"
                    break

            # Extract viability
            viabilidade = "Média"
            if any(word in text_lower for word in ["alta viabilidade", "muito viável", "excelente"]):
                viabilidade = "Alta"
            elif any(word in text_lower for word in ["baixa viabilidade", "pouco viável", "difícil"]):
                viabilidade = "Baixa"

            # Extract biodiversity score
            biodiversidade_score = 0.5
            if any(word in text_lower for word in ["alta biodiversidade", "rica", "diversa"]):
                biodiversidade_score = 0.8
            elif any(word in text_lower for word in ["baixa biodiversidade", "pobre", "degradada"]):
                biodiversidade_score = 0.3

            # Extract threats
            ameacas = []
            for threat in self.threat_categories:
                if threat in text_lower or threat.replace("_", " ") in text_lower:
                    ameacas.append(threat.replace("_", " ").title())

            if not ameacas:
                ameacas = ["Ameaças não especificadas"]

            return {
                "tipo_ecossistema": tipo_ecossistema,
                "bioma_identificado": "Extraído do texto",
                "condicao_geral": "Análise baseada em texto não estruturado",
                "biodiversidade_score": biodiversidade_score,
                "viabilidade_restauracao": viabilidade,
                "especies_nativas_esperadas": ["Análise textual limitada"],
                "ameacas_identificadas": ameacas,
                "indicadores_ecologicos": {
                    "conectividade": 0.5,
                    "integridade_habitat": biodiversidade_score,
                    "pressao_antropica": 0.6
                },
                "recomendacoes_prioritarias": [
                    "Análise mais detalhada necessária",
                    "Avaliação de campo recomendada"
                ],
                "resumo": f"Análise baseada em texto: {response_text[:200]}..." if response_text else "Análise limitada",
                "confianca_geral": 0.4
            }

        except Exception as e:
            self.logger.error(
                "Text extraction failed",
                request_id=str(request_id),
                error=str(e)
            )

            # Return minimal fallback
            return {
                "tipo_ecossistema": "Ecossistema brasileiro",
                "bioma_identificado": "Não identificado",
                "condicao_geral": "Análise não disponível",
                "biodiversidade_score": 0.5,
                "viabilidade_restauracao": "Média",
                "especies_nativas_esperadas": [],
                "ameacas_identificadas": [],
                "indicadores_ecologicos": {
                    "conectividade": 0.5,
                    "integridade_habitat": 0.5,
                    "pressao_antropica": 0.5
                },
                "recomendacoes_prioritarias": [],
                "resumo": "Análise falhou",
                "confianca_geral": 0.3
            }

    async def _generate_fallback_analysis(
        self,
        request_data: Dict[str, Any],
        rag_context: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Generate fallback analysis when GPU service is unavailable

        Args:
            request_data: Request data
            rag_context: RAG context
            request_id: Request ID

        Returns:
            Fallback analysis results
        """
        try:
            coordinates = request_data.get("coordinates", {})
            image_analysis = request_data.get("image_analysis", {})

            # Determine ecosystem based on available data
            tipo_ecossistema = "Ecossistema brasileiro"
            bioma = "Não identificado"

            if coordinates:
                lat, lng = coordinates.get("latitude"), coordinates.get("longitude")
                if lat and lng:
                    bioma = self._determine_biome_from_coordinates(lat, lng)
                    tipo_ecossistema = f"{bioma} (baseado em coordenadas)"

            # Assess condition based on image analysis
            biodiversidade_score = 0.5
            viabilidade = "Média"
            ameacas = ["Avaliação limitada"]

            if image_analysis:
                cobertura = image_analysis.get("cobertura_vegetal", 0.5)
                especies_invasoras = image_analysis.get("especies_invasoras", [])
                sinais_degradacao = image_analysis.get("sinais_degradacao", [])

                # Adjust scores based on image analysis
                biodiversidade_score = min(0.9, cobertura + 0.2)

                if cobertura > 0.7 and len(especies_invasoras) == 0:
                    viabilidade = "Alta"
                elif cobertura < 0.3 or len(especies_invasoras) > 2:
                    viabilidade = "Baixa"

                # Extract threats from image analysis
                ameacas = []
                if especies_invasoras:
                    ameacas.append("Espécies invasoras")
                if sinais_degradacao:
                    ameacas.extend(sinais_degradacao[:3])
                if not ameacas:
                    ameacas = ["Nenhuma ameaça identificada"]

            # Use RAG context if available
            especies_nativas = ["Análise limitada"]
            if rag_context.get("documents"):
                especies_nativas = ["Espécies típicas da região (baseado em contexto)"]

            return {
                "tipo_ecossistema": tipo_ecossistema,
                "bioma_identificado": bioma,
                "condicao_geral": f"Análise baseada em dados disponíveis. Cobertura vegetal estimada: {image_analysis.get('cobertura_vegetal', 0.5):.1%}",
                "biodiversidade_score": biodiversidade_score,
                "viabilidade_restauracao": viabilidade,
                "especies_nativas_esperadas": especies_nativas,
                "ameacas_identificadas": ameacas,
                "indicadores_ecologicos": {
                    "conectividade": 0.5,
                    "integridade_habitat": biodiversidade_score,
                    "pressao_antropica": 0.6 if len(image_analysis.get("especies_invasoras", [])) > 0 else 0.4
                },
                "recomendacoes_prioritarias": [
                    "Análise de campo detalhada",
                    "Identificação de espécies nativas",
                    "Avaliação de conectividade"
                ],
                "resumo": f"Análise preliminar do {tipo_ecossistema} com viabilidade {viabilidade.lower()} de restauração",
                "confianca_geral": 0.6
            }

        except Exception as e:
            self.logger.error(
                "Fallback analysis generation failed",
                request_id=str(request_id),
                error=str(e)
            )

            # Return minimal safe analysis
            return {
                "tipo_ecossistema": "Ecossistema brasileiro",
                "bioma_identificado": "Não identificado",
                "condicao_geral": "Análise não disponível",
                "biodiversidade_score": 0.5,
                "viabilidade_restauracao": "Média",
                "especies_nativas_esperadas": [],
                "ameacas_identificadas": [],
                "indicadores_ecologicos": {
                    "conectividade": 0.5,
                    "integridade_habitat": 0.5,
                    "pressao_antropica": 0.5
                },
                "recomendacoes_prioritarias": [],
                "resumo": "Análise de ecossistema indisponível",
                "confianca_geral": 0.3
            }

    async def _enhance_biodiversity_analysis(
        self,
        base_analysis: Dict[str, Any],
        rag_context: Dict[str, Any],
        coordinates: Optional[Dict[str, float]],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Enhance analysis with additional biodiversity insights

        Args:
            base_analysis: Base analysis from Gemma
            rag_context: RAG context data
            coordinates: GPS coordinates
            request_id: Request ID

        Returns:
            Enhanced analysis
        """
        try:
            enhanced = base_analysis.copy()

            # Add conservation status if available from RAG
            conservation_info = self._extract_conservation_info(rag_context)
            if conservation_info:
                enhanced["status_conservacao"] = conservation_info

            # Add connectivity assessment
            if coordinates:
                connectivity_score = self._assess_connectivity(coordinates, rag_context)
                enhanced["indicadores_ecologicos"]["conectividade"] = connectivity_score

            # Enhance species recommendations based on RAG data
            rag_species = self._extract_species_from_rag(rag_context)
            if rag_species:
                current_species = enhanced.get("especies_nativas_esperadas", [])
                enhanced_species = list(set(current_species + rag_species))[:10]  # Limit to 10
                enhanced["especies_nativas_esperadas"] = enhanced_species

            # Add ecosystem services assessment
            enhanced["servicos_ecossistemicos"] = self._assess_ecosystem_services(
                enhanced.get("tipo_ecossistema", ""),
                enhanced.get("biodiversidade_score", 0.5)
            )

            self.logger.debug(
                "Biodiversity analysis enhanced",
                request_id=str(request_id),
                conservation_status=enhanced.get("status_conservacao"),
                species_count=len(enhanced.get("especies_nativas_esperadas", []))
            )

            return enhanced

        except Exception as e:
            self.logger.warning(
                "Biodiversity enhancement failed",
                request_id=str(request_id),
                error=str(e)
            )

            # Return base analysis if enhancement fails
            return base_analysis

    def _calculate_analysis_depth(self, analysis: Dict[str, Any]) -> float:
        """
        Calculate analysis depth score based on completeness

        Args:
            analysis: Analysis results

        Returns:
            Depth score (0.0 to 1.0)
        """
        try:
            depth_score = 0.0

            # Check presence of key fields
            key_fields = [
                "tipo_ecossistema", "bioma_identificado", "condicao_geral",
                "especies_nativas_esperadas", "ameacas_identificadas", "resumo"
            ]

            for field in key_fields:
                if field in analysis and analysis[field]:
                    if isinstance(analysis[field], list):
                        depth_score += 0.1 if len(analysis[field]) > 0 else 0
                    else:
                        depth_score += 0.1

            # Bonus for detailed fields
            if "indicadores_ecologicos" in analysis:
                depth_score += 0.2

            if "recomendacoes_prioritarias" in analysis:
                recs = analysis["recomendacoes_prioritarias"]
                if isinstance(recs, list) and len(recs) >= 3:
                    depth_score += 0.2

            return min(1.0, depth_score)

        except Exception:
            return 0.5

    def _extract_conservation_info(self, rag_context: Dict[str, Any]) -> Optional[str]:
        """Extract conservation status from RAG context"""
        try:
            docs = rag_context.get("documents", [])
            for doc in docs:
                content = doc.get("content", "").lower()
                if any(word in content for word in ["ameaçado", "vulnerável", "crítico", "iucn"]):
                    return "Área com espécies em risco de extinção"
            return None
        except Exception:
            return None

    def _assess_connectivity(self, coordinates: Dict[str, float], rag_context: Dict[str, Any]) -> float:
        """Assess habitat connectivity based on location and context"""
        try:
            # Simplified connectivity assessment
            # In production, this would use geospatial analysis
            base_score = 0.5

            # Adjust based on RAG context mentioning fragmentation
            docs = rag_context.get("documents", [])
            for doc in docs:
                content = doc.get("content", "").lower()
                if "fragmentação" in content or "fragmentado" in content:
                    base_score -= 0.2
                elif "corredor" in content or "conectividade" in content:
                    base_score += 0.2

            return max(0.0, min(1.0, base_score))
        except Exception:
            return 0.5

    def _extract_species_from_rag(self, rag_context: Dict[str, Any]) -> List[str]:
        """Extract species names from RAG context"""
        try:
            species = []
            docs = rag_context.get("documents", [])

            # Common Brazilian species patterns
            species_patterns = [
                "pau-brasil", "jequitibá", "ipê", "sabiá", "bem-te-vi",
                "mico-leão", "onça", "anta", "tatu", "preguiça"
            ]

            for doc in docs:
                content = doc.get("content", "").lower()
                for pattern in species_patterns:
                    if pattern in content and pattern.title() not in species:
                        species.append(pattern.title())

            return species[:5]  # Limit to 5 species
        except Exception:
            return []

    def _assess_ecosystem_services(self, ecosystem_type: str, biodiversity_score: float) -> Dict[str, float]:
        """Assess ecosystem services provision"""
        try:
            base_services = {
                "regulacao_clima": 0.5,
                "purificacao_agua": 0.5,
                "controle_erosao": 0.5,
                "polinizacao": 0.5,
                "sequestro_carbono": 0.5
            }

            # Adjust based on ecosystem type and biodiversity
            multiplier = biodiversity_score

            if "mata atlântica" in ecosystem_type.lower():
                base_services["sequestro_carbono"] *= 1.3
                base_services["purificacao_agua"] *= 1.2
            elif "cerrado" in ecosystem_type.lower():
                base_services["regulacao_clima"] *= 1.2
                base_services["controle_erosao"] *= 1.1
            elif "amazônia" in ecosystem_type.lower():
                base_services["regulacao_clima"] *= 1.4
                base_services["sequestro_carbono"] *= 1.5

            # Apply biodiversity multiplier
            for service in base_services:
                base_services[service] = min(1.0, base_services[service] * multiplier)

            return base_services
        except Exception:
            return {
                "regulacao_clima": 0.5,
                "purificacao_agua": 0.5,
                "controle_erosao": 0.5,
                "polinizacao": 0.5,
                "sequestro_carbono": 0.5
            }
