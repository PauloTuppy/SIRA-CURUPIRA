# SIRA RAG Service

Sistema Inteligente de Recuperação Ambiental - Retrieval Augmented Generation Service

## 🏗️ Arquitetura

- **Genkit**: Framework de IA para RAG
- **Firebase Functions**: Serverless deployment
- **Firestore**: Vector database com busca vetorial
- **Vertex AI**: Embeddings e modelos de IA
- **TypeScript**: Linguagem principal

## 🚀 Quick Start

### Desenvolvimento Local

1. **Instalar dependências:**
```bash
cd rag-service
npm install
```

2. **Configurar Firebase:**
```bash
firebase login
firebase use --add  # Selecionar projeto
```

3. **Configurar variáveis de ambiente:**
```bash
cp ../.env.example .env
# Editar .env com configurações do RAG service
```

4. **Iniciar emuladores:**
```bash
npm run dev
```

### Produção

1. **Build e deploy:**
```bash
npm run build
npm run deploy
```

## 📦 Estrutura

```
rag-service/
├── src/
│   ├── config/          # Configurações
│   ├── routes/          # Endpoints REST
│   ├── services/        # Lógica de negócio
│   ├── data-sources/    # Integrações GBIF, IUCN, etc
│   ├── models/          # Tipos TypeScript
│   ├── utils/           # Utilitários
│   └── index.ts         # Entry point
├── firebase.json        # Configuração Firebase
├── firestore.rules      # Regras Firestore
├── firestore.indexes.json # Índices Firestore
├── package.json         # Dependências
└── tsconfig.json        # TypeScript config
```

## 🔧 Configuração

### Variáveis de Ambiente

| Variável | Descrição |
|----------|-----------|
| `GEMINI_API_KEY` | Chave API do Gemini |
| `GOOGLE_CLOUD_PROJECT` | ID do projeto GCP |
| `VERTEX_AI_LOCATION` | Região Vertex AI |
| `EMBEDDING_MODEL` | Modelo de embeddings |
| `GBIF_API_URL` | URL da API GBIF |
| `IUCN_API_TOKEN` | Token da API IUCN |
| `EBIRD_API_KEY` | Chave da API eBird |

### Firestore Collections

- **knowledge_base**: Documentos científicos
- **embeddings**: Vetores de embeddings
- **analyses**: Resultados de análises
- **ingestion_jobs**: Jobs de ingestão

## ✅ Implementação Completa

### Fase 3.2: Ingestion Service - CONCLUÍDA

**Implementação Avançada:**

1. **Data Source Clients (4 APIs):**
   - **GBIF Client**: Biodiversidade global com 330+ linhas
   - **IUCN Client**: Lista Vermelha com 280+ linhas
   - **OBIS Client**: Biodiversidade marinha com 310+ linhas
   - **eBird Client**: Observações de aves com 290+ linhas

2. **Core Services:**
   - **Embedding Service**: Vertex AI text-embedding-004 com batch processing
   - **Firestore Service**: Vector storage com 350+ linhas
   - **Ingestion Service**: Orquestração completa com 890+ linhas

3. **Funcionalidades Implementadas:**
   - ✅ Job queue system com status tracking
   - ✅ Document chunking (1000 chars, 200 overlap)
   - ✅ Batch embedding generation (100 per batch)
   - ✅ Vector similarity search (cosine similarity)
   - ✅ Real-time progress tracking
   - ✅ Error handling e retry logic
   - ✅ Health checks para todos os serviços

## 🌐 API Endpoints

### Health Check
- `GET /health` - Status básico
- `GET /health/detailed` - Status detalhado com todos os serviços
- `GET /health/ready` - Readiness probe
- `GET /health/live` - Liveness probe

### RAG Operations
- `POST /api/v1/rag/query` - Consulta RAG com embedding + vector search
- `POST /api/v1/rag/embed` - Gerar embeddings com Vertex AI
- `POST /api/v1/rag/search` - Busca vetorial por similaridade
- `GET /api/v1/rag/stats` - Estatísticas da knowledge base

### Ingestion Operations
- `POST /api/v1/ingestion/start` - Iniciar job de ingestão
- `GET /api/v1/ingestion/job/:jobId` - Status detalhado do job
- `GET /api/v1/ingestion/jobs` - Listar jobs com filtros
- `DELETE /api/v1/ingestion/job/:jobId` - Cancelar job em execução
- `GET /api/v1/ingestion/stats` - Estatísticas completas de ingestão

### Exemplo de Uso - Ingestão GBIF

```bash
# Iniciar ingestão de espécies brasileiras
curl -X POST http://localhost:5001/api/v1/ingestion/start \
  -H "Content-Type: application/json" \
  -d '{
    "source": "gbif",
    "parameters": {
      "species": "Aedes aegypti",
      "location": { "country": "BR" },
      "limit": 100
    }
  }'

# Verificar status do job
curl http://localhost:5001/api/v1/ingestion/job/gbif_1234567890_abc123

# Consultar dados ingeridos
curl -X POST http://localhost:5001/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Aedes aegypti distribution in Brazil",
    "maxResults": 5,
    "threshold": 0.7
  }'
```

## 🔍 Fontes de Dados

### GBIF (Global Biodiversity Information Facility)
- **URL**: https://api.gbif.org/v1
- **Dados**: Ocorrências de espécies, taxonomia
- **Rate Limit**: Sem limite oficial

### IUCN Red List
- **URL**: https://apiv3.iucnredlist.org/api/v3
- **Dados**: Status de conservação
- **Auth**: API Token necessário

### OBIS (Ocean Biodiversity Information System)
- **URL**: https://api.obis.org
- **Dados**: Biodiversidade marinha
- **Rate Limit**: Sem limite oficial

### eBird
- **URL**: https://api.ebird.org/v2
- **Dados**: Observações de aves
- **Auth**: API Key necessário

## 🧪 Testes

```bash
# Unit tests
npm test

# Watch mode
npm run test:watch

# Coverage
npm test -- --coverage
```

## 📊 Monitoramento

### Métricas
- Request count/duration
- RAG query performance
- Ingestion job status
- Vector search latency

### Logs
- Structured JSON logging
- Request/response tracking
- Error context
- Performance metrics

## 🚀 Deploy

### Firebase Functions

```bash
# Deploy todas as functions
npm run deploy

# Deploy específica
firebase deploy --only functions:ragService
```

### Configuração Cloud Run (Alternativa)

```yaml
# cloudrun.yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: sira-rag-service
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/memory: "2Gi"
    spec:
      containers:
      - image: gcr.io/PROJECT_ID/sira-rag-service
        ports:
        - containerPort: 8001
```

## 🔧 Desenvolvimento

### Scripts Disponíveis

- `npm run build` - Compilar TypeScript
- `npm run dev` - Desenvolvimento com hot reload
- `npm run serve` - Servir localmente
- `npm run lint` - Linting
- `npm run format` - Formatação

### Genkit Development

```bash
# Iniciar Genkit UI
npm run genkit:start

# Desenvolvimento com Genkit
npm run genkit:dev
```

## 📚 Próximas Implementações

### Fase 3.2: Ingestion Service
- Implementar ingestão GBIF, IUCN, OBIS, eBird
- Processamento de documentos
- Chunking e embeddings
- Job queue e status

### Fase 3.3: Retriever Service
- Busca vetorial Firestore
- Similarity search
- Context retrieval
- Result ranking

### Fase 3.4: Vector Search
- Configurar índices vetoriais
- Otimizar queries
- Batch operations
- Performance tuning

### Fase 3.5: API Endpoints
- Implementar endpoints completos
- Validação de entrada
- Rate limiting
- Caching

## 🤝 Contribuição

1. Fork o projeto
2. Crie feature branch
3. Commit mudanças
4. Push para branch
5. Abra Pull Request

## 📄 Licença

MIT License - veja [LICENSE](../LICENSE) para detalhes.
