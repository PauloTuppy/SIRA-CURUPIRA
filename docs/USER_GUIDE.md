# SIRA - Sistema Inteligente de Recuperação Ambiental
## Guia do Usuário

### 📋 Índice
1. [Visão Geral](#visão-geral)
2. [Instalação](#instalação)
3. [Configuração](#configuração)
4. [Uso da Interface](#uso-da-interface)
5. [API Reference](#api-reference)
6. [Casos de Uso](#casos-de-uso)
7. [Solução de Problemas](#solução-de-problemas)

---

## 🌍 Visão Geral

O SIRA é um sistema inteligente para análise e recuperação ambiental no Brasil, especializado em:

- **Identificação de Biomas**: Análise automática de biomas brasileiros
- **Análise de Biodiversidade**: Avaliação de espécies e conservação
- **Planos de Recuperação**: Geração de estratégias personalizadas
- **Dados Científicos**: Integração com GBIF, IUCN, OBIS, eBird
- **IA Especializada**: Modelo Gemma 2 9B otimizado para meio ambiente

### 🏗️ Arquitetura do Sistema

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Frontend      │    │   Backend       │    │   RAG Service   │
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (TypeScript)  │
│   Port: 5173    │    │   Port: 8000    │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   GPU Service   │    │     OLLAMA      │
                       │   (Python)      │◄──►│   (Gemma 2)     │
                       │   Port: 8002    │    │   Port: 11434   │
                       └─────────────────┘    └─────────────────┘
```

---

## 🚀 Instalação

### Pré-requisitos

- **Docker** 20.10+
- **Docker Compose** 2.0+
- **NVIDIA Docker** (para GPU)
- **Git**
- **Node.js** 18+ (desenvolvimento)
- **Python** 3.11+ (desenvolvimento)

### Instalação Rápida

```bash
# 1. Clone o repositório
git clone https://github.com/your-org/sira.git
cd sira

# 2. Configure as variáveis de ambiente
cp .env.example .env
# Edite .env com suas configurações

# 3. Execute o setup
./scripts/setup.sh

# 4. Inicie os serviços
docker-compose up -d
```

### Instalação de Produção

```bash
# 1. Configure ambiente de produção
cp .env.example .env.prod
# Configure .env.prod com valores de produção

# 2. Execute deploy de produção
./scripts/deploy-production.sh
```

---

## ⚙️ Configuração

### Variáveis de Ambiente Principais

```bash
# Google Cloud
GOOGLE_CLOUD_PROJECT=seu-projeto
GEMINI_API_KEY=sua-chave-gemini

# Firebase
FIREBASE_PROJECT_ID=seu-projeto-firebase
FIRESTORE_DATABASE=(default)

# Segurança
SECRET_KEY=sua-chave-secreta
JWT_SECRET_KEY=sua-chave-jwt

# Redis
REDIS_PASSWORD=sua-senha-redis

# Monitoramento
GRAFANA_USER=admin
GRAFANA_PASSWORD=sua-senha-grafana
```

### Configuração de GPU

Para usar o GPU Service com NVIDIA:

```bash
# Instalar NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

---

## 🖥️ Uso da Interface

### Página Principal

1. **Acesse**: http://localhost:5173
2. **Insira localização**: Coordenadas ou endereço
3. **Selecione tipo de análise**:
   - Básica: Identificação de bioma
   - Completa: Bioma + biodiversidade
   - Avançada: Análise completa + plano de recuperação

### Tipos de Análise

#### 🌱 Análise Básica
- Identificação do bioma
- Características principais
- Estado de conservação

#### 🦋 Análise de Biodiversidade
- Espécies encontradas na região
- Status de conservação
- Ameaças identificadas
- Recomendações básicas

#### 📋 Plano de Recuperação
- Estratégias específicas
- Cronograma de implementação
- Recursos necessários
- Indicadores de sucesso

### Interface de Monitoramento

**Grafana Dashboard**: http://localhost:3000
- Métricas de performance
- Status dos serviços
- Uso de recursos
- Logs centralizados

---

## 🔌 API Reference

### Endpoints Principais

#### Análise Ambiental

```http
POST /api/v1/analysis/analyze
Content-Type: application/json

{
  "location": {
    "latitude": -23.5505,
    "longitude": -46.6333,
    "address": "São Paulo, SP, Brazil"
  },
  "analysis_type": "comprehensive",
  "include_biodiversity": true,
  "include_recovery_plan": true
}
```

**Resposta:**
```json
{
  "analysis_id": "uuid-here",
  "status": "processing",
  "estimated_completion": "2024-01-15T10:30:00Z"
}
```

#### Status da Análise

```http
GET /api/v1/analysis/{analysis_id}/status
```

#### Busca de Conhecimento

```http
POST /api/v1/knowledge/search
Content-Type: application/json

{
  "query": "Atlantic Forest conservation",
  "limit": 10,
  "include_metadata": true
}
```

#### Geração de IA

```http
POST /api/v1/ai/generate
Content-Type: application/json

{
  "prompt": "Generate recovery plan for degraded Cerrado",
  "context": {
    "biome": "Cerrado",
    "area_size": "100 hectares"
  }
}
```

### Streaming API

Para análises em tempo real:

```http
POST /api/v1/analysis/analyze/stream
Accept: text/event-stream
```

**Eventos SSE:**
```
data: {"type": "progress", "message": "Analyzing biome..."}
data: {"type": "progress", "message": "Searching biodiversity data..."}
data: {"type": "completed", "results": {...}}
```

---

## 📚 Casos de Uso

### 1. Análise de Área Degradada

**Cenário**: Avaliar área degradada para recuperação

```bash
# 1. Submeter análise
curl -X POST http://localhost:8000/api/v1/analysis/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "location": {"latitude": -15.7801, "longitude": -47.9292},
    "analysis_type": "comprehensive",
    "include_recovery_plan": true
  }'

# 2. Acompanhar progresso
curl http://localhost:8000/api/v1/analysis/{id}/status

# 3. Obter resultados
curl http://localhost:8000/api/v1/analysis/{id}/results
```

### 2. Pesquisa Científica

**Cenário**: Buscar dados sobre espécie específica

```bash
curl -X POST http://localhost:8000/api/v1/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Jaguar Panthera onca Atlantic Forest",
    "limit": 5,
    "filters": {
      "biome": "Atlantic Forest",
      "conservation_status": "vulnerable"
    }
  }'
```

### 3. Geração de Relatório

**Cenário**: Gerar relatório personalizado

```bash
curl -X POST http://localhost:8000/api/v1/ai/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Create executive summary for Cerrado restoration project",
    "context": {
      "area": "500 hectares",
      "budget": "R$ 2,000,000",
      "timeline": "5 years"
    },
    "format": "executive_summary"
  }'
```

---

## 🔧 Solução de Problemas

### Problemas Comuns

#### Serviços não iniciam

```bash
# Verificar logs
docker-compose logs -f [service-name]

# Verificar saúde dos serviços
curl http://localhost:8000/health
curl http://localhost:8001/health
curl http://localhost:8002/health
```

#### GPU Service não funciona

```bash
# Verificar NVIDIA Docker
docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi

# Verificar OLLAMA
docker exec sira-ollama ollama list

# Reinstalar modelo
docker exec sira-ollama ollama pull gemma2:9b
```

#### Performance lenta

```bash
# Verificar recursos
docker stats

# Limpar cache
curl -X DELETE http://localhost:8000/api/v1/cache/clear

# Verificar métricas
curl http://localhost:8000/metrics
```

### Logs e Monitoramento

```bash
# Logs por serviço
docker-compose logs -f backend
docker-compose logs -f rag-service
docker-compose logs -f gpu-service

# Logs centralizados
tail -f logs/*/app.log

# Métricas Prometheus
curl http://localhost:9090/api/v1/query?query=up

# Dashboard Grafana
open http://localhost:3000
```

### Comandos de Manutenção

```bash
# Reiniciar serviços
docker-compose restart

# Atualizar imagens
docker-compose pull
docker-compose up -d

# Backup de dados
./scripts/backup.sh

# Limpeza de sistema
docker system prune -a
docker volume prune
```

---

### Configuração Avançada

#### Ajuste de Performance

```bash
# Backend
export MAX_WORKERS=4
export CACHE_TTL=7200
export MAX_CONCURRENT_REQUESTS=50

# RAG Service
export MAX_CONCURRENT_INGESTIONS=5
export BATCH_SIZE=100
export EMBEDDING_CACHE_TTL=86400

# GPU Service
export MAX_CONCURRENT_REQUESTS=10
export MODEL_TEMPERATURE=0.7
export CACHE_TTL=7200
```

#### Configuração de Rede

```yaml
# docker-compose.override.yml
version: '3.8'
services:
  backend:
    ports:
      - "8000:8000"
    environment:
      - CORS_ORIGINS=["https://yourdomain.com"]
```

---

## 📞 Suporte

- **Documentação**: `/docs`
- **API Docs**: http://localhost:8000/docs
- **Monitoramento**: http://localhost:3000
- **Issues**: GitHub Issues
- **Email**: suporte@sira.com.br

---

## 📄 Licença

Este projeto está licenciado sob a Licença MIT. Veja o arquivo `LICENSE` para detalhes.
