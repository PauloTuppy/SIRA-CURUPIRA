"""
Image Analysis Agent - Specialized in Gemini Vision for Aedes aegypti and invasive species detection
"""

import asyncio
import base64
import json
from typing import Any, Dict, List, Optional
from uuid import UUID
from io import BytesIO
from PIL import Image

import structlog
from google.generativeai import GenerativeModel
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from .base import BaseAgent
from ..config import settings
from ..utils.exceptions import AnalysisError, ValidationError


class ImageAnalysisAgent(BaseAgent):
    """
    Image Analysis Agent using Gemini Vision
    Specialized in detecting Aedes aegypti and invasive species
    """

    def __init__(self):
        super().__init__(
            name="image_analysis",
            version="1.0.0",
            timeout_seconds=120.0,  # 2 minutes for image analysis
            max_retries=3
        )

        # Initialize Gemini Vision
        genai.configure(api_key=settings.gemini_api_key)
        self.model = GenerativeModel(
            settings.image_analysis_model,
            safety_settings={
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }
        )

        self.logger = structlog.get_logger("agent.image_analysis")

        # Supported image formats
        self.supported_formats = {
            "image/jpeg", "image/jpg", "image/png", "image/webp", "image/gif"
        }

        # Maximum image size (10MB)
        self.max_image_size = 10 * 1024 * 1024
    
    async def _process_request(
        self,
        request_data: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Process image analysis request

        Args:
            request_data: Request data with image information
            request_id: Request ID

        Returns:
            Image analysis results
        """
        self.logger.info(
            "Starting image analysis",
            request_id=str(request_id),
            filename=request_data.get("filename")
        )

        try:
            # Extract and validate image data
            image_data = request_data.get("image_data")
            image_type = request_data.get("image_type", "image/jpeg")
            filename = request_data.get("filename", "unknown")
            coordinates = request_data.get("coordinates")
            focus_areas = request_data.get("focus_areas", [])

            if not image_data:
                raise ValidationError(
                    message="No image data provided",
                    field="image_data"
                )

            # Validate image format and size
            await self._validate_image(image_data, image_type, request_id)

            # Analyze image with Gemini Vision
            analysis_result = await self._analyze_with_gemini_vision(
                image_data, image_type, filename, coordinates, focus_areas, request_id
            )
        
            self.logger.info(
                "Image analysis completed",
                request_id=str(request_id),
                risco_dengue=analysis_result["risco_dengue"],
                especies_invasoras_count=len(analysis_result["especies_invasoras"]),
                cobertura_vegetal=analysis_result["cobertura_vegetal"]
            )

            return {
                "data": analysis_result,
                "metadata": {
                    "model_used": settings.image_analysis_model,
                    "image_type": image_type,
                    "filename": filename,
                    "analysis_type": "gemini_vision",
                    "coordinates": coordinates,
                    "focus_areas": focus_areas
                },
                "confidence_score": analysis_result["confianca_geral"],
                "quality_metrics": {
                    "image_quality": await self._assess_image_quality(image_data, image_type),
                    "detection_confidence": analysis_result["confianca_geral"],
                    "species_identification": self._calculate_species_confidence(analysis_result["especies_invasoras"])
                }
            }

        except (ValidationError, AnalysisError):
            raise
        except Exception as e:
            self.logger.error(
                "Image analysis failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )
            raise AnalysisError(
                message=f"Image analysis failed: {str(e)}",
                analysis_id=str(request_id),
                agent_name=self.name
            )

    async def _validate_image(
        self,
        image_data: str,
        image_type: str,
        request_id: UUID
    ) -> None:
        """
        Validate image data and format

        Args:
            image_data: Base64 encoded image data
            image_type: Image MIME type
            request_id: Request ID

        Raises:
            ValidationError: If image is invalid
        """
        try:
            # Check supported format
            if image_type not in self.supported_formats:
                raise ValidationError(
                    message=f"Unsupported image format: {image_type}",
                    field="image_type"
                )

            # Decode base64 data
            try:
                # Remove data URL prefix if present
                if "," in image_data:
                    image_data = image_data.split(",", 1)[1]

                decoded_data = base64.b64decode(image_data)
            except Exception as e:
                raise ValidationError(
                    message=f"Invalid base64 image data: {str(e)}",
                    field="image_data"
                )

            # Check image size
            if len(decoded_data) > self.max_image_size:
                raise ValidationError(
                    message=f"Image too large: {len(decoded_data)} bytes (max: {self.max_image_size})",
                    field="image_data"
                )

            # Validate image with PIL
            try:
                with Image.open(BytesIO(decoded_data)) as img:
                    # Check image dimensions
                    width, height = img.size
                    if width < 100 or height < 100:
                        raise ValidationError(
                            message=f"Image too small: {width}x{height} (min: 100x100)",
                            field="image_data"
                        )

                    if width > 4096 or height > 4096:
                        raise ValidationError(
                            message=f"Image too large: {width}x{height} (max: 4096x4096)",
                            field="image_data"
                        )

                    # Verify image format matches MIME type
                    expected_format = image_type.split("/")[1].upper()
                    if expected_format == "JPEG":
                        expected_format = "JPEG"
                    elif expected_format == "JPG":
                        expected_format = "JPEG"

                    if img.format != expected_format and expected_format != "GIF":
                        self.logger.warning(
                            "Image format mismatch",
                            request_id=str(request_id),
                            expected=expected_format,
                            actual=img.format
                        )

            except Exception as e:
                raise ValidationError(
                    message=f"Invalid image file: {str(e)}",
                    field="image_data"
                )

            self.logger.debug(
                "Image validation successful",
                request_id=str(request_id),
                image_type=image_type,
                size_bytes=len(decoded_data)
            )

        except ValidationError:
            raise
        except Exception as e:
            self.logger.error(
                "Image validation failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )
            raise ValidationError(
                message=f"Image validation failed: {str(e)}",
                field="image_data"
            )

    async def _analyze_with_gemini_vision(
        self,
        image_data: str,
        image_type: str,
        filename: str,
        coordinates: Optional[Dict[str, float]],
        focus_areas: List[str],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Analyze image with Gemini Vision API

        Args:
            image_data: Base64 encoded image data
            image_type: Image MIME type
            filename: Image filename
            coordinates: Optional GPS coordinates
            focus_areas: Areas to focus analysis on
            request_id: Request ID

        Returns:
            Analysis results
        """
        try:
            # Prepare image for Gemini Vision
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]

            # Build analysis prompt
            analysis_prompt = self._build_analysis_prompt(coordinates, focus_areas)

            # Prepare image part for Gemini
            image_part = {
                "mime_type": image_type,
                "data": base64.b64decode(image_data)
            }

            self.logger.debug(
                "Sending image to Gemini Vision",
                request_id=str(request_id),
                image_type=image_type,
                prompt_length=len(analysis_prompt)
            )

            # Call Gemini Vision API
            response = await asyncio.to_thread(
                self.model.generate_content,
                [analysis_prompt, image_part]
            )

            # Parse response
            if not response.text:
                raise AnalysisError(
                    message="Empty response from Gemini Vision",
                    analysis_id=str(request_id),
                    agent_name=self.name
                )

            # Extract JSON from response
            analysis_result = self._parse_gemini_response(response.text, request_id)

            # Validate and enhance results
            analysis_result = self._validate_and_enhance_results(analysis_result, request_id)

            self.logger.debug(
                "Gemini Vision analysis successful",
                request_id=str(request_id),
                risco_dengue=analysis_result["risco_dengue"],
                especies_count=len(analysis_result["especies_invasoras"])
            )

            return analysis_result

        except AnalysisError:
            raise
        except Exception as e:
            self.logger.error(
                "Gemini Vision analysis failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return fallback analysis
            return self._get_fallback_analysis(request_id)

    def _build_analysis_prompt(
        self,
        coordinates: Optional[Dict[str, float]],
        focus_areas: List[str]
    ) -> str:
        """
        Build analysis prompt for Gemini Vision

        Args:
            coordinates: Optional GPS coordinates
            focus_areas: Areas to focus analysis on

        Returns:
            Analysis prompt
        """
        base_prompt = """
        Analise esta imagem ambiental com foco em recuperação ecológica. Seja preciso e detalhado.

        ANÁLISE OBRIGATÓRIA:

        1. AEDES AEGYPTI E DENGUE:
        - Identifique criadouros potenciais (recipientes com água parada, pneus, vasos, calhas)
        - Avalie condições favoráveis à proliferação (sombra, água limpa, temperatura)
        - Classifique o risco: Alto (múltiplos criadouros), Médio (poucos criadouros), Baixo (sem criadouros)

        2. ESPÉCIES INVASORAS:
        - Caramujo-africano (Achatina fulica): concha grande, listras escuras
        - Baronesa/Aguapé (Eichhornia crassipes): flores roxas, folhas arredondadas
        - Capim-colonião (Panicum maximum): gramínea alta, densa
        - Outras espécies invasoras visíveis
        - Para cada espécie: nome científico, risco ecológico, localização na imagem

        3. CONDIÇÕES AMBIENTAIS:
        - Cobertura vegetal (0.0 = sem vegetação, 1.0 = totalmente coberto)
        - Qualidade da vegetação (nativa vs invasora vs degradada)
        - Sinais de degradação (erosão, lixo, poluição, desmatamento)
        - Presença de água (rios, lagos, alagamentos)

        RESPONDA APENAS EM JSON VÁLIDO:
        {
            "risco_dengue": "Alto|Médio|Baixo",
            "criadouros_identificados": ["lista específica de criadouros encontrados"],
            "especies_invasoras": [
                {
                    "nome": "Nome científico (Nome comum)",
                    "risco": "Alto|Médio|Baixo",
                    "descricao": "Impacto ecológico específico",
                    "confianca": 0.0-1.0,
                    "localizacao": "Posição específica na imagem",
                    "densidade": "Baixa|Média|Alta"
                }
            ],
            "cobertura_vegetal": 0.0-1.0,
            "qualidade_vegetacao": "Nativa|Mista|Invasora|Degradada",
            "sinais_degradacao": ["lista específica de problemas observados"],
            "presenca_agua": {
                "tem_agua": true/false,
                "tipo": "Rio|Lago|Alagamento|Recipiente|Outro",
                "qualidade": "Limpa|Turva|Poluída"
            },
            "confianca_geral": 0.0-1.0
        }
        """

        # Add location context if coordinates provided
        if coordinates:
            lat = coordinates.get("latitude")
            lng = coordinates.get("longitude")
            if lat and lng:
                base_prompt += f"\n\nCONTEXTO GEOGRÁFICO: Imagem capturada em lat: {lat}, lng: {lng}"

        # Add focus areas if specified
        if focus_areas:
            focus_text = ", ".join(focus_areas)
            base_prompt += f"\n\nFOCO ESPECIAL: Priorize a análise de: {focus_text}"

        return base_prompt

    def _parse_gemini_response(self, response_text: str, request_id: UUID) -> Dict[str, Any]:
        """
        Parse Gemini Vision response

        Args:
            response_text: Raw response text
            request_id: Request ID

        Returns:
            Parsed analysis results
        """
        try:
            # Try to extract JSON from response
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

            self.logger.debug(
                "Successfully parsed Gemini response",
                request_id=str(request_id),
                keys=list(result.keys())
            )

            return result

        except Exception as e:
            self.logger.error(
                "Failed to parse Gemini response",
                request_id=str(request_id),
                error=str(e),
                response_preview=response_text[:200] if response_text else None
            )

            # Return structured fallback based on response content
            return self._extract_fallback_from_text(response_text, request_id)

    def _validate_and_enhance_results(
        self,
        results: Dict[str, Any],
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Validate and enhance analysis results

        Args:
            results: Raw analysis results
            request_id: Request ID

        Returns:
            Enhanced results
        """
        try:
            # Ensure required fields exist
            required_fields = [
                "risco_dengue", "especies_invasoras", "cobertura_vegetal",
                "sinais_degradacao", "confianca_geral"
            ]

            for field in required_fields:
                if field not in results:
                    if field == "especies_invasoras":
                        results[field] = []
                    elif field == "sinais_degradacao":
                        results[field] = []
                    elif field == "cobertura_vegetal":
                        results[field] = 0.5
                    elif field == "confianca_geral":
                        results[field] = 0.6
                    elif field == "risco_dengue":
                        results[field] = "Médio"

            # Validate and fix data types
            if not isinstance(results["especies_invasoras"], list):
                results["especies_invasoras"] = []

            if not isinstance(results["sinais_degradacao"], list):
                results["sinais_degradacao"] = []

            # Ensure cobertura_vegetal is between 0 and 1
            cobertura = results.get("cobertura_vegetal", 0.5)
            if isinstance(cobertura, (int, float)):
                results["cobertura_vegetal"] = max(0.0, min(1.0, float(cobertura)))
            else:
                results["cobertura_vegetal"] = 0.5

            # Ensure confianca_geral is between 0 and 1
            confianca = results.get("confianca_geral", 0.6)
            if isinstance(confianca, (int, float)):
                results["confianca_geral"] = max(0.0, min(1.0, float(confianca)))
            else:
                results["confianca_geral"] = 0.6

            # Validate risco_dengue values
            valid_risks = ["Alto", "Médio", "Baixo"]
            if results["risco_dengue"] not in valid_risks:
                results["risco_dengue"] = "Médio"

            # Enhance species data
            for species in results["especies_invasoras"]:
                if not isinstance(species, dict):
                    continue

                # Ensure required species fields
                if "confianca" not in species:
                    species["confianca"] = 0.7
                elif isinstance(species["confianca"], (int, float)):
                    species["confianca"] = max(0.0, min(1.0, float(species["confianca"])))

                if "risco" not in species or species["risco"] not in valid_risks:
                    species["risco"] = "Médio"

            # Add criadouros_identificados if missing (for backward compatibility)
            if "criadouros_identificados" not in results:
                results["criadouros_identificados"] = []

            # Add presenca_agua if missing
            if "presenca_agua" not in results:
                results["presenca_agua"] = {
                    "tem_agua": False,
                    "tipo": "Nenhum",
                    "qualidade": "N/A"
                }

            self.logger.debug(
                "Results validation completed",
                request_id=str(request_id),
                especies_count=len(results["especies_invasoras"]),
                risco_dengue=results["risco_dengue"]
            )

            return results

        except Exception as e:
            self.logger.error(
                "Results validation failed",
                request_id=str(request_id),
                error=str(e),
                exc_info=True
            )

            # Return safe fallback
            return self._get_fallback_analysis(request_id)

    def _get_fallback_analysis(self, request_id: UUID) -> Dict[str, Any]:
        """
        Get fallback analysis when Gemini Vision fails

        Args:
            request_id: Request ID

        Returns:
            Fallback analysis results
        """
        self.logger.warning(
            "Using fallback analysis",
            request_id=str(request_id)
        )

        return {
            "risco_dengue": "Médio",
            "criadouros_identificados": ["Análise automática indisponível"],
            "especies_invasoras": [],
            "cobertura_vegetal": 0.5,
            "qualidade_vegetacao": "Indeterminada",
            "sinais_degradacao": ["Análise visual necessária"],
            "presenca_agua": {
                "tem_agua": False,
                "tipo": "Indeterminado",
                "qualidade": "N/A"
            },
            "confianca_geral": 0.3
        }

    def _extract_fallback_from_text(
        self,
        response_text: str,
        request_id: UUID
    ) -> Dict[str, Any]:
        """
        Extract basic analysis from text response when JSON parsing fails

        Args:
            response_text: Raw response text
            request_id: Request ID

        Returns:
            Basic analysis results
        """
        try:
            text_lower = response_text.lower() if response_text else ""

            # Determine dengue risk based on keywords
            risco_dengue = "Baixo"
            if any(word in text_lower for word in ["alto risco", "muitos criadouros", "água parada"]):
                risco_dengue = "Alto"
            elif any(word in text_lower for word in ["médio", "alguns", "possível"]):
                risco_dengue = "Médio"

            # Look for invasive species mentions
            especies_invasoras = []
            if "caramujo" in text_lower or "achatina" in text_lower:
                especies_invasoras.append({
                    "nome": "Caramujo-africano (Achatina fulica)",
                    "risco": "Alto",
                    "descricao": "Espécie invasora identificada no texto",
                    "confianca": 0.6,
                    "localizacao": "Mencionado na análise",
                    "densidade": "Indeterminada"
                })

            if "baronesa" in text_lower or "eichhornia" in text_lower:
                especies_invasoras.append({
                    "nome": "Baronesa (Eichhornia crassipes)",
                    "risco": "Alto",
                    "descricao": "Planta aquática invasora identificada",
                    "confianca": 0.6,
                    "localizacao": "Mencionado na análise",
                    "densidade": "Indeterminada"
                })

            # Estimate vegetation coverage
            cobertura_vegetal = 0.5
            if any(word in text_lower for word in ["densa", "abundante", "muita vegetação"]):
                cobertura_vegetal = 0.8
            elif any(word in text_lower for word in ["pouca", "escassa", "degradada"]):
                cobertura_vegetal = 0.2

            return {
                "risco_dengue": risco_dengue,
                "criadouros_identificados": ["Análise baseada em texto"],
                "especies_invasoras": especies_invasoras,
                "cobertura_vegetal": cobertura_vegetal,
                "qualidade_vegetacao": "Indeterminada",
                "sinais_degradacao": ["Análise textual limitada"],
                "presenca_agua": {
                    "tem_agua": "água" in text_lower,
                    "tipo": "Indeterminado",
                    "qualidade": "N/A"
                },
                "confianca_geral": 0.4
            }

        except Exception as e:
            self.logger.error(
                "Fallback text extraction failed",
                request_id=str(request_id),
                error=str(e)
            )
            return self._get_fallback_analysis(request_id)

    async def _assess_image_quality(
        self,
        image_data: str,
        image_type: str
    ) -> float:
        """
        Assess image quality for analysis

        Args:
            image_data: Base64 encoded image data
            image_type: Image MIME type

        Returns:
            Quality score (0.0 to 1.0)
        """
        try:
            # Decode image
            if "," in image_data:
                image_data = image_data.split(",", 1)[1]

            decoded_data = base64.b64decode(image_data)

            with Image.open(BytesIO(decoded_data)) as img:
                width, height = img.size

                # Base quality score
                quality_score = 0.5

                # Resolution scoring
                total_pixels = width * height
                if total_pixels >= 1920 * 1080:  # Full HD or better
                    quality_score += 0.3
                elif total_pixels >= 1280 * 720:  # HD
                    quality_score += 0.2
                elif total_pixels >= 640 * 480:   # VGA
                    quality_score += 0.1

                # Aspect ratio scoring (prefer landscape for environmental analysis)
                aspect_ratio = width / height
                if 1.2 <= aspect_ratio <= 2.0:  # Good landscape ratio
                    quality_score += 0.1

                # File size scoring (indicates compression level)
                file_size = len(decoded_data)
                if file_size > 500000:  # > 500KB indicates less compression
                    quality_score += 0.1

                return min(1.0, quality_score)

        except Exception:
            return 0.5  # Default quality score

    def _calculate_species_confidence(self, especies_invasoras: List[Dict[str, Any]]) -> float:
        """
        Calculate overall species identification confidence

        Args:
            especies_invasoras: List of identified invasive species

        Returns:
            Overall confidence score
        """
        if not especies_invasoras:
            return 1.0  # High confidence in "no species found"

        confidences = []
        for species in especies_invasoras:
            if isinstance(species, dict) and "confianca" in species:
                conf = species["confianca"]
                if isinstance(conf, (int, float)):
                    confidences.append(float(conf))

        if not confidences:
            return 0.7  # Default confidence

        # Return average confidence
        return sum(confidences) / len(confidences)
