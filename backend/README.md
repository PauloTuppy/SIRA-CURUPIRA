# SIRA Backend Service

Sistema Inteligente de Recuperação Ambiental - Backend FastAPI com ADK Multi-Agente

## 🏗️ Arquitetura

- **FastAPI**: Framework web assíncrono
- **ADK (Agent Development Kit)**: Sistema multi-agente
- **Gemini Pro/Vision**: Modelos de IA para coordenação e análise
- **Firestore**: Banco de dados NoSQL
- **Redis**: Cache e sessões
- **Prometheus**: Métricas e monitoramento

## 🚀 Quick Start

### Desenvolvimento Local

1. **Instalar dependências:**
```bash
cd backend
pip install -r requirements.txt
```

2. **Configurar variáveis de ambiente:**
```bash
cp ../.env.example .env
# Editar .env com suas configurações
```

3. **Executar o servidor:**
```bash
python -m uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```

### Docker (Recomendado)

1. **Build da imagem:**
```bash
docker build -t sira-backend .
```

2. **Executar container:**
```bash
docker run -p 8080:8080 --env-file .env sira-backend
```

### Docker Compose (Ambiente Completo)

```bash
# Na raiz do projeto
docker-compose up -d
```

## 📦 Containerização

### Dockerfile

O `Dockerfile` utiliza multi-stage build otimizado para produção:

- **Build Stage**: Instala dependências em ambiente virtual
- **Production Stage**: Imagem slim com apenas runtime necessário
- **Security**: Usuário não-root, health checks
- **Optimization**: Cache de layers, .dockerignore

### Características:

- ✅ **Python 3.11+** com otimizações
- ✅ **Multi-stage build** para imagens menores
- ✅ **Non-root user** para segurança
- ✅ **Health checks** integrados
- ✅ **Graceful shutdown** com timeouts
- ✅ **Logs estruturados** em JSON

### Variáveis de Ambiente

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `ENVIRONMENT` | `production` | Ambiente de execução |
| `DEBUG` | `false` | Modo debug |
| `PORT` | `8080` | Porta do servidor |
| `WORKERS` | `4` | Número de workers |
| `GEMINI_API_KEY` | - | Chave API do Gemini |
| `GOOGLE_CLOUD_PROJECT` | - | ID do projeto GCP |
| `REDIS_URL` | - | URL do Redis |

## ☁️ Deploy Cloud Run

### Automático (Script)

```bash
chmod +x deploy.sh
./deploy.sh
```

### Manual

1. **Build e push:**
```bash
gcloud builds submit --tag gcr.io/PROJECT_ID/sira-backend
```

2. **Deploy:**
```bash
gcloud run deploy sira-backend \
  --image gcr.io/PROJECT_ID/sira-backend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

### Configuração Cloud Run

O arquivo `cloudrun.yaml` inclui:

- ✅ **Auto-scaling**: 1-10 instâncias
- ✅ **Resources**: 2 CPU, 2Gi RAM
- ✅ **Health checks**: Startup, liveness, readiness
- ✅ **Security**: Service account, secrets
- ✅ **Monitoring**: Logs estruturados

## 🔧 Configuração

### Secrets (Produção)

Criar secrets no Secret Manager:

```bash
# Gemini API Key
echo "your-api-key" | gcloud secrets create gemini-api-key --data-file=-

# JWT Secret
echo "your-jwt-secret" | gcloud secrets create jwt-secret-key --data-file=-

# Redis Password
echo "your-redis-password" | gcloud secrets create redis-password --data-file=-
```

### Service Account

Criar service account com permissões:

```bash
gcloud iam service-accounts create sira-backend-sa \
  --display-name="SIRA Backend Service Account"

# Adicionar roles necessários
gcloud projects add-iam-policy-binding PROJECT_ID \
  --member="serviceAccount:sira-backend-sa@PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

## 📊 Monitoramento

### Métricas Prometheus

Endpoint: `http://localhost:8080/metrics`

Métricas disponíveis:
- Request count/duration
- Agent processing times
- Error rates
- Resource usage

### Health Checks

- **Health**: `GET /api/v1/health`
- **Ready**: `GET /api/v1/health/ready`
- **Live**: `GET /api/v1/health/live`

### Logs

Logs estruturados em JSON com:
- Request ID tracking
- Agent execution traces
- Error context
- Performance metrics

## 🧪 Testes

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# Coverage
pytest --cov=src tests/
```

## 🔍 Debugging

### Logs em Desenvolvimento

```bash
# Logs detalhados
LOG_LEVEL=DEBUG python -m uvicorn src.main:app --reload

# Logs específicos de agente
LOG_LEVEL=DEBUG AGENT_DEBUG=true python -m uvicorn src.main:app --reload
```

### Docker Debug

```bash
# Executar com shell
docker run -it --entrypoint /bin/bash sira-backend

# Logs do container
docker logs -f sira-backend
```

## 📁 Estrutura

```
backend/
├── src/
│   ├── agents/          # Sistema multi-agente
│   ├── api/             # Endpoints REST
│   ├── models/          # Modelos Pydantic
│   ├── services/        # Serviços de negócio
│   ├── utils/           # Utilitários
│   ├── config.py        # Configurações
│   └── main.py          # App principal
├── tests/               # Testes
├── Dockerfile           # Container de produção
├── cloudrun.yaml        # Configuração Cloud Run
├── deploy.sh            # Script de deploy
├── requirements.txt     # Dependências Python
└── README.md           # Esta documentação
```

## 🚨 Troubleshooting

### Problemas Comuns

1. **Port já em uso:**
```bash
lsof -ti:8080 | xargs kill -9
```

2. **Permissões Google Cloud:**
```bash
gcloud auth application-default login
```

3. **Redis connection:**
```bash
redis-cli ping
```

4. **Memory issues:**
```bash
# Aumentar memory limit
docker run --memory=2g sira-backend
```

### Performance

- Use Redis para cache
- Configure workers baseado em CPU
- Monitor métricas Prometheus
- Otimize queries Firestore

## 📚 Documentação API

- **OpenAPI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **Health**: `http://localhost:8080/api/v1/health`

## 🤝 Contribuição

1. Fork o projeto
2. Crie feature branch
3. Commit mudanças
4. Push para branch
5. Abra Pull Request

## 📄 Licença

MIT License - veja [LICENSE](../LICENSE) para detalhes.
