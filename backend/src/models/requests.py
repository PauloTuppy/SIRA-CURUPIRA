"""
Request models for the SIRA Backend Service
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID


class ImageUploadRequest(BaseModel):
    """Image upload request model"""
    file_data: str = Field(..., description="Dados do arquivo em base64")
    file_type: str = Field(..., description="Tipo MIME do arquivo")
    filename: str = Field(..., description="Nome do arquivo")
    file_size: int = Field(..., description="Tamanho do arquivo em bytes")
    
    @validator('file_type')
    def validate_file_type(cls, v):
        allowed_types = [
            'image/jpeg', 'image/png', 'image/webp',
            'video/mp4', 'video/webm'
        ]
        if v not in allowed_types:
            raise ValueError(f'Tipo de arquivo não suportado: {v}')
        return v
    
    @validator('file_size')
    def validate_file_size(cls, v):
        max_size = 50 * 1024 * 1024  # 50MB
        if v > max_size:
            raise ValueError(f'Arquivo muito grande. Máximo: {max_size} bytes')
        return v


class CoordinatesRequest(BaseModel):
    """Geographic coordinates request model"""
    latitude: float = Field(..., ge=-90, le=90, description="Latitude (-90 a 90)")
    longitude: float = Field(..., ge=-180, le=180, description="Longitude (-180 a 180)")
    accuracy: Optional[float] = Field(None, description="Precisão em metros")
    altitude: Optional[float] = Field(None, description="Altitude em metros")
    heading: Optional[float] = Field(None, ge=0, le=360, description="Direção (0-360 graus)")


class AnalysisConfigRequest(BaseModel):
    """Analysis configuration request model"""
    focus_areas: Optional[List[str]] = Field(
        None,
        description="Áreas de foco específicas",
        example=["dengue", "especies_invasoras", "biodiversidade"]
    )
    detail_level: Optional[str] = Field(
        "standard",
        description="Nível de detalhamento da análise",
        pattern="^(basic|standard|detailed)$"
    )
    include_recommendations: bool = Field(
        True,
        description="Incluir recomendações de recuperação"
    )
    include_confidence_scores: bool = Field(
        False,
        description="Incluir scores de confiança"
    )
    language: str = Field(
        "pt-BR",
        description="Idioma da resposta",
        pattern="^(pt-BR|en-US|es-ES)$"
    )


class HistoryRequest(BaseModel):
    """History request model"""
    user_id: Optional[str] = Field(None, description="ID do usuário")
    start_date: Optional[datetime] = Field(None, description="Data inicial")
    end_date: Optional[datetime] = Field(None, description="Data final")
    status_filter: Optional[List[str]] = Field(
        None,
        description="Filtrar por status",
        example=["completed", "failed"]
    )
    limit: int = Field(
        20,
        ge=1,
        le=100,
        description="Número máximo de resultados"
    )
    offset: int = Field(
        0,
        ge=0,
        description="Offset para paginação"
    )
    sort_by: str = Field(
        "created_at",
        description="Campo para ordenação",
        regex="^(created_at|updated_at|filename)$"
    )
    sort_order: str = Field(
        "desc",
        description="Ordem de classificação",
        regex="^(asc|desc)$"
    )


class SearchRequest(BaseModel):
    """Search request model"""
    query: str = Field(..., min_length=1, max_length=500, description="Termo de busca")
    search_type: str = Field(
        "general",
        description="Tipo de busca",
        regex="^(general|species|ecosystem|location)$"
    )
    filters: Optional[Dict[str, Any]] = Field(
        None,
        description="Filtros adicionais"
    )
    coordinates: Optional[CoordinatesRequest] = Field(
        None,
        description="Coordenadas para busca geográfica"
    )
    radius_km: Optional[float] = Field(
        None,
        ge=0.1,
        le=1000,
        description="Raio de busca em quilômetros"
    )
    limit: int = Field(
        10,
        ge=1,
        le=50,
        description="Número máximo de resultados"
    )


class FeedbackRequest(BaseModel):
    """Feedback request model"""
    analysis_id: UUID = Field(..., description="ID da análise")
    rating: int = Field(..., ge=1, le=5, description="Avaliação (1-5)")
    feedback_type: str = Field(
        "general",
        description="Tipo de feedback",
        regex="^(general|accuracy|speed|usability)$"
    )
    comments: Optional[str] = Field(
        None,
        max_length=1000,
        description="Comentários adicionais"
    )
    user_id: Optional[str] = Field(None, description="ID do usuário")
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadados adicionais"
    )


class BatchAnalysisRequest(BaseModel):
    """Batch analysis request model"""
    analyses: List[Dict[str, Any]] = Field(
        ...,
        min_items=1,
        max_items=10,
        description="Lista de análises para processamento em lote"
    )
    priority: str = Field(
        "normal",
        description="Prioridade do lote",
        regex="^(low|normal|high)$"
    )
    callback_url: Optional[str] = Field(
        None,
        description="URL para callback quando o lote for concluído"
    )
    user_id: Optional[str] = Field(None, description="ID do usuário")


class WebhookRequest(BaseModel):
    """Webhook request model"""
    event_type: str = Field(..., description="Tipo do evento")
    analysis_id: UUID = Field(..., description="ID da análise")
    status: str = Field(..., description="Status da análise")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Timestamp do evento")
    data: Optional[Dict[str, Any]] = Field(None, description="Dados adicionais do evento")


class HealthCheckRequest(BaseModel):
    """Health check request model"""
    check_dependencies: bool = Field(
        True,
        description="Verificar dependências externas"
    )
    include_metrics: bool = Field(
        False,
        description="Incluir métricas de performance"
    )


class ConfigUpdateRequest(BaseModel):
    """Configuration update request model"""
    config_key: str = Field(..., description="Chave da configuração")
    config_value: Any = Field(..., description="Valor da configuração")
    user_id: Optional[str] = Field(None, description="ID do usuário que fez a alteração")
    reason: Optional[str] = Field(None, description="Motivo da alteração")


class ExportRequest(BaseModel):
    """Export request model"""
    analysis_ids: List[UUID] = Field(
        ...,
        min_items=1,
        max_items=100,
        description="IDs das análises para exportar"
    )
    export_format: str = Field(
        "json",
        description="Formato de exportação",
        regex="^(json|csv|pdf)$"
    )
    include_images: bool = Field(
        False,
        description="Incluir imagens no export"
    )
    user_id: Optional[str] = Field(None, description="ID do usuário")


class NotificationRequest(BaseModel):
    """Notification request model"""
    user_id: str = Field(..., description="ID do usuário")
    notification_type: str = Field(
        ...,
        description="Tipo de notificação",
        regex="^(analysis_complete|analysis_failed|system_alert)$"
    )
    title: str = Field(..., max_length=100, description="Título da notificação")
    message: str = Field(..., max_length=500, description="Mensagem da notificação")
    priority: str = Field(
        "normal",
        description="Prioridade da notificação",
        regex="^(low|normal|high|urgent)$"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        None,
        description="Metadados adicionais"
    )
