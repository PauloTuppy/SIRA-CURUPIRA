"""
Analysis-related Pydantic models
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from uuid import UUID, uuid4


class RiskLevel(str, Enum):
    """Risk level enumeration"""
    ALTO = "Alto"
    MEDIO = "Médio"
    BAIXO = "Baixo"
    NA = "N/A"


class ViabilityLevel(str, Enum):
    """Viability level enumeration"""
    ALTA = "Alta"
    MEDIA = "Média"
    BAIXA = "Baixa"


class AnalysisStatus(str, Enum):
    """Analysis status enumeration"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InvasiveSpecies(BaseModel):
    """Invasive species model"""
    nome: str = Field(..., description="Nome da espécie invasora")
    risco: RiskLevel = Field(..., description="Nível de risco da espécie")
    descricao: str = Field(..., description="Descrição do impacto da espécie")
    confianca: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Nível de confiança da detecção (0-1)"
    )
    localizacao: Optional[str] = Field(
        None, 
        description="Localização específica na imagem onde foi detectada"
    )


class EcosystemAnalysis(BaseModel):
    """Ecosystem analysis details"""
    tipo_ecossistema: str = Field(..., description="Tipo de ecossistema identificado")
    condicao_geral: str = Field(..., description="Condição geral do ecossistema")
    biodiversidade_score: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Score de biodiversidade (0-1)"
    )
    cobertura_vegetal: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Percentual de cobertura vegetal"
    )
    qualidade_agua: Optional[RiskLevel] = Field(
        None, 
        description="Qualidade da água se aplicável"
    )
    sinais_degradacao: List[str] = Field(
        default_factory=list, 
        description="Lista de sinais de degradação identificados"
    )


class RecoveryPlan(BaseModel):
    """Recovery plan model"""
    acoes: List[str] = Field(..., description="Lista de ações de recuperação")
    prioridade: List[str] = Field(
        default_factory=list, 
        description="Ações ordenadas por prioridade"
    )
    cronograma: Optional[Dict[str, str]] = Field(
        None, 
        description="Cronograma estimado para as ações"
    )
    recursos_necessarios: Optional[List[str]] = Field(
        None, 
        description="Recursos necessários para implementação"
    )
    custo_estimado: Optional[str] = Field(
        None, 
        description="Estimativa de custo do plano"
    )
    metricas_sucesso: Optional[List[str]] = Field(
        None, 
        description="Métricas para avaliar sucesso do plano"
    )


class AnalysisResult(BaseModel):
    """Complete analysis result model - compatible with frontend"""
    riscoDengue: RiskLevel = Field(..., description="Risco de proliferação do Aedes aegypti")
    especiesInvasoras: List[InvasiveSpecies] = Field(
        default_factory=list, 
        description="Lista de espécies invasoras detectadas"
    )
    viabilidadeRestauracao: ViabilityLevel = Field(
        ..., 
        description="Viabilidade de restauração da área"
    )
    planoRecuperacao: List[str] = Field(
        ..., 
        description="Lista de ações para recuperação"
    )
    resumoEcossistema: str = Field(..., description="Resumo do ecossistema analisado")
    
    # Extended analysis data
    analise_detalhada: Optional[EcosystemAnalysis] = Field(
        None, 
        description="Análise detalhada do ecossistema"
    )
    plano_detalhado: Optional[RecoveryPlan] = Field(
        None, 
        description="Plano de recuperação detalhado"
    )
    confianca_geral: Optional[float] = Field(
        None, 
        ge=0.0, 
        le=1.0, 
        description="Confiança geral da análise"
    )
    tempo_processamento: Optional[float] = Field(
        None, 
        description="Tempo de processamento em segundos"
    )


class AnalysisProgress(BaseModel):
    """Analysis progress model for real-time updates"""
    analysis_id: UUID = Field(..., description="ID da análise")
    status: AnalysisStatus = Field(..., description="Status atual da análise")
    progress_percentage: float = Field(
        ..., 
        ge=0.0, 
        le=100.0, 
        description="Percentual de progresso"
    )
    current_step: str = Field(..., description="Etapa atual do processamento")
    message: Optional[str] = Field(None, description="Mensagem de status")
    estimated_completion: Optional[datetime] = Field(
        None, 
        description="Estimativa de conclusão"
    )
    error_message: Optional[str] = Field(None, description="Mensagem de erro se aplicável")


class AnalysisRequest(BaseModel):
    """Analysis request model"""
    image_data: str = Field(..., description="Dados da imagem em base64")
    image_type: str = Field(..., description="Tipo MIME da imagem")
    filename: str = Field(..., description="Nome do arquivo")
    coordinates: Optional[Dict[str, float]] = Field(
        None, 
        description="Coordenadas geográficas (lat, lng)"
    )
    focus_areas: Optional[List[str]] = Field(
        None, 
        description="Áreas de foco específicas para análise"
    )
    user_id: Optional[str] = Field(None, description="ID do usuário (se autenticado)")
    metadata: Optional[Dict[str, Any]] = Field(
        None, 
        description="Metadados adicionais"
    )
    
    @validator('image_type')
    def validate_image_type(cls, v):
        allowed_types = [
            'image/jpeg', 'image/png', 'image/webp',
            'video/mp4', 'video/webm'
        ]
        if v not in allowed_types:
            raise ValueError(f'Tipo de arquivo não suportado: {v}')
        return v


class AnalysisResponse(BaseModel):
    """Analysis response model"""
    analysis_id: UUID = Field(default_factory=uuid4, description="ID único da análise")
    status: AnalysisStatus = Field(default=AnalysisStatus.PENDING, description="Status da análise")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Data de criação")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Data de atualização")
    
    # Request data
    filename: str = Field(..., description="Nome do arquivo analisado")
    image_url: Optional[str] = Field(None, description="URL da imagem armazenada")
    coordinates: Optional[Dict[str, float]] = Field(None, description="Coordenadas geográficas")
    
    # Results (populated when completed)
    result: Optional[AnalysisResult] = Field(None, description="Resultado da análise")
    
    # Progress tracking
    progress: Optional[AnalysisProgress] = Field(None, description="Progresso da análise")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Mensagem de erro")
    retry_count: int = Field(default=0, description="Número de tentativas")
    
    # Metadata
    processing_time: Optional[float] = Field(None, description="Tempo total de processamento")
    agent_responses: Optional[Dict[str, Any]] = Field(
        None, 
        description="Respostas individuais dos agentes"
    )
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            UUID: lambda v: str(v)
        }
