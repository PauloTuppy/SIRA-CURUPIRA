# SIRA API Documentation
## Sistema Inteligente de Recuperação Ambiental

### 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Autenticação](#autenticação)
3. [Endpoints](#endpoints)
4. [Modelos de Dados](#modelos-de-dados)
5. [Códigos de Erro](#códigos-de-erro)
6. [Exemplos](#exemplos)

---

## 🌐 Visão Geral

A API do SIRA oferece endpoints RESTful para análise ambiental, busca de conhecimento científico e geração de conteúdo com IA.

**Base URL**: `http://localhost:8000/api/v1`
**Formato**: JSON
**Encoding**: UTF-8

### Serviços Disponíveis

- **Backend API** (Port 8000): Coordenação e análise principal
- **RAG Service** (Port 8001): Busca e recuperação de conhecimento
- **GPU Service** (Port 8002): Inferência de IA com Gemma 2

---

## 🔐 Autenticação

### JWT Token (Futuro)
```http
Authorization: Bearer <jwt_token>
```

### API Key (Desenvolvimento)
```http
X-API-Key: <api_key>
```

---

## 📡 Endpoints

### 🏥 Health & Status

#### GET /health
Verificação básica de saúde do serviço.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime": 3600,
  "timestamp": "2024-01-15T10:00:00Z"
}
```

#### GET /health/detailed
Verificação detalhada incluindo dependências.

**Response:**
```json
{
  "status": "healthy",
  "services": {
    "database": "healthy",
    "redis": "healthy",
    "rag_service": "healthy",
    "gpu_service": "healthy"
  },
  "system": {
    "cpu_usage": 25.5,
    "memory_usage": 60.2,
    "disk_usage": 45.8
  }
}
```

### 🔬 Análise Ambiental

#### POST /analysis/analyze
Inicia uma nova análise ambiental.

**Request:**
```json
{
  "location": {
    "latitude": -23.5505,
    "longitude": -46.6333,
    "address": "São Paulo, SP, Brazil"
  },
  "analysis_type": "comprehensive",
  "include_biodiversity": true,
  "include_recovery_plan": true,
  "user_context": {
    "organization": "NGO Verde",
    "project_type": "urban_restoration",
    "budget_range": "medium"
  }
}
```

**Response:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "estimated_completion": "2024-01-15T10:30:00Z",
  "progress": {
    "current_step": "biome_identification",
    "completion_percentage": 15
  }
}
```

#### GET /analysis/{analysis_id}/status
Consulta o status de uma análise.

**Response:**
```json
{
  "analysis_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "progress": {
    "completion_percentage": 100,
    "steps": [
      {
        "name": "biome_identification",
        "status": "completed",
        "duration": 5.2
      },
      {
        "name": "biodiversity_analysis",
        "status": "completed",
        "duration": 12.8
      },
      {
        "name": "recovery_plan_generation",
        "status": "completed",
        "duration": 8.5
      }
    ]
  },
  "results": {
    "biome_analysis": {
      "primary_biome": "Atlantic Forest",
      "confidence": 0.92,
      "characteristics": ["High biodiversity", "Fragmented habitat"]
    },
    "biodiversity_analysis": {
      "species_count": 245,
      "endemic_species": 18,
      "threatened_species": 12,
      "conservation_priority": "high"
    },
    "recovery_plan": {
      "recommendations": [
        {
          "action": "Native species reforestation",
          "priority": "high",
          "timeline": "6-12 months",
          "cost_estimate": "R$ 50,000"
        }
      ]
    }
  }
}
```

#### POST /analysis/analyze/stream
Análise com streaming em tempo real via Server-Sent Events.

**Headers:**
```http
Accept: text/event-stream
Cache-Control: no-cache
```

**Response Stream:**
```
data: {"type": "progress", "step": "biome_identification", "percentage": 25}

data: {"type": "result", "component": "biome", "data": {"primary_biome": "Atlantic Forest"}}

data: {"type": "completed", "analysis_id": "uuid", "results": {...}}
```

### 🔍 Busca de Conhecimento

#### POST /knowledge/search
Busca informações científicas na base de conhecimento.

**Request:**
```json
{
  "query": "Atlantic Forest endangered species",
  "limit": 10,
  "filters": {
    "biome": "Atlantic Forest",
    "conservation_status": ["vulnerable", "endangered"],
    "data_source": ["IUCN", "GBIF"]
  },
  "include_metadata": true
}
```

**Response:**
```json
{
  "query": "Atlantic Forest endangered species",
  "total_results": 156,
  "results": [
    {
      "id": "result_1",
      "title": "Panthera onca - Jaguar Conservation Status",
      "content": "The jaguar (Panthera onca) is classified as Near Threatened...",
      "score": 0.95,
      "metadata": {
        "source": "IUCN Red List",
        "last_updated": "2023-12-01",
        "biome": "Atlantic Forest",
        "conservation_status": "near_threatened"
      }
    }
  ],
  "facets": {
    "biomes": {"Atlantic Forest": 89, "Cerrado": 45},
    "conservation_status": {"vulnerable": 67, "endangered": 34}
  }
}
```

### 🤖 Geração de IA

#### POST /ai/generate
Gera conteúdo usando IA especializada.

**Request:**
```json
{
  "prompt": "Create a recovery plan for 100 hectares of degraded Cerrado",
  "context": {
    "biome": "Cerrado",
    "area_size": "100 hectares",
    "degradation_level": "moderate",
    "budget": "R$ 500,000"
  },
  "options": {
    "max_tokens": 1000,
    "temperature": 0.7,
    "format": "structured_plan"
  }
}
```

**Response:**
```json
{
  "response": "# Cerrado Recovery Plan\n\n## Executive Summary\nThis plan outlines...",
  "tokens_used": 856,
  "processing_time": 3.2,
  "model_info": {
    "model": "gemma2:9b",
    "version": "sira-optimized"
  }
}
```

#### POST /ai/generate/stream
Geração com streaming em tempo real.

**Response Stream:**
```
data: {"type": "token", "content": "# Cerrado"}

data: {"type": "token", "content": " Recovery Plan"}

data: {"type": "completed", "total_tokens": 856}
```

### 📊 Métricas e Monitoramento

#### GET /metrics
Métricas do sistema em formato JSON.

**Response:**
```json
{
  "requests": {
    "total": 1250,
    "success_rate": 0.98,
    "average_response_time": 2.3
  },
  "analysis": {
    "completed": 45,
    "in_progress": 3,
    "failed": 2
  },
  "system": {
    "cpu_usage": 35.2,
    "memory_usage": 68.5,
    "cache_hit_rate": 0.85
  }
}
```

#### GET /metrics/prometheus
Métricas em formato Prometheus.

**Response:**
```
# HELP sira_requests_total Total number of requests
# TYPE sira_requests_total counter
sira_requests_total{method="POST",endpoint="/analysis/analyze"} 1250

# HELP sira_response_time_seconds Response time in seconds
# TYPE sira_response_time_seconds histogram
sira_response_time_seconds_bucket{le="1.0"} 800
sira_response_time_seconds_bucket{le="5.0"} 1200
```

---

## 📋 Modelos de Dados

### Location
```json
{
  "latitude": -23.5505,
  "longitude": -46.6333,
  "address": "São Paulo, SP, Brazil",
  "elevation": 760,
  "accuracy": 10
}
```

### BiomeAnalysis
```json
{
  "primary_biome": "Atlantic Forest",
  "secondary_biomes": ["Cerrado"],
  "confidence": 0.92,
  "characteristics": ["High biodiversity", "Fragmented habitat"],
  "threats": ["Deforestation", "Urban expansion"],
  "conservation_status": "critically_endangered"
}
```

### BiodiversityAnalysis
```json
{
  "species_count": 245,
  "endemic_species": 18,
  "threatened_species": 12,
  "species_by_group": {
    "mammals": 45,
    "birds": 120,
    "reptiles": 35,
    "amphibians": 25,
    "plants": 20
  },
  "conservation_priority": "high",
  "key_species": [
    {
      "name": "Panthera onca",
      "common_name": "Jaguar",
      "status": "near_threatened",
      "population_trend": "decreasing"
    }
  ]
}
```

### RecoveryPlan
```json
{
  "summary": "Comprehensive restoration plan for Atlantic Forest fragment",
  "timeline": "5 years",
  "total_cost": "R$ 2,500,000",
  "recommendations": [
    {
      "id": "rec_1",
      "action": "Native species reforestation",
      "description": "Plant 10,000 native seedlings",
      "priority": "high",
      "timeline": "6-12 months",
      "cost_estimate": "R$ 150,000",
      "success_indicators": ["Survival rate > 80%", "Canopy coverage > 60%"]
    }
  ],
  "phases": [
    {
      "phase": 1,
      "name": "Site preparation",
      "duration": "3 months",
      "activities": ["Soil analysis", "Invasive species removal"]
    }
  ]
}
```

---

## ⚠️ Códigos de Erro

### HTTP Status Codes

- **200 OK**: Requisição bem-sucedida
- **201 Created**: Recurso criado com sucesso
- **400 Bad Request**: Dados inválidos na requisição
- **401 Unauthorized**: Autenticação necessária
- **403 Forbidden**: Acesso negado
- **404 Not Found**: Recurso não encontrado
- **422 Unprocessable Entity**: Dados válidos mas não processáveis
- **429 Too Many Requests**: Limite de taxa excedido
- **500 Internal Server Error**: Erro interno do servidor
- **503 Service Unavailable**: Serviço temporariamente indisponível

### Error Response Format

```json
{
  "error": {
    "code": "INVALID_LOCATION",
    "message": "The provided coordinates are outside Brazil",
    "details": {
      "latitude": -23.5505,
      "longitude": -46.6333,
      "valid_range": "Brazil territory only"
    },
    "timestamp": "2024-01-15T10:00:00Z",
    "request_id": "req_123456"
  }
}
```

---

## 💡 Exemplos

### Análise Completa de Área

```bash
# 1. Iniciar análise
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": {
      "latitude": -15.7801,
      "longitude": -47.9292,
      "address": "Brasília, DF"
    },
    "analysis_type": "comprehensive",
    "include_biodiversity": true,
    "include_recovery_plan": true
  }'

# Response: {"analysis_id": "uuid", "status": "processing"}

# 2. Acompanhar progresso
curl http://localhost:8000/api/v1/analysis/uuid/status

# 3. Buscar conhecimento relacionado
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Cerrado restoration techniques",
    "limit": 5
  }'

# 4. Gerar relatório personalizado
curl -X POST http://localhost:8000/api/v1/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create executive summary for Cerrado restoration project",
    "context": {"area": "500 hectares", "budget": "R$ 2M"}
  }'
```

### Streaming Analysis

```javascript
// JavaScript example for streaming
const eventSource = new EventSource('/api/v1/analysis/analyze/stream', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    location: {latitude: -23.5505, longitude: -46.6333},
    analysis_type: 'comprehensive'
  })
});

eventSource.onmessage = function(event) {
  const data = JSON.parse(event.data);
  
  if (data.type === 'progress') {
    console.log(`Progress: ${data.percentage}%`);
  } else if (data.type === 'completed') {
    console.log('Analysis completed:', data.results);
    eventSource.close();
  }
};
```

---

## 📚 SDKs e Bibliotecas

### Python SDK (Futuro)
```python
from sira_sdk import SIRAClient

client = SIRAClient(api_key="your_key")
analysis = client.analyze_location(
    latitude=-23.5505,
    longitude=-46.6333,
    include_recovery_plan=True
)
```

### JavaScript SDK (Futuro)
```javascript
import { SIRAClient } from '@sira/sdk';

const client = new SIRAClient({apiKey: 'your_key'});
const analysis = await client.analyzeLocation({
  latitude: -23.5505,
  longitude: -46.6333,
  includeRecoveryPlan: true
});
```
