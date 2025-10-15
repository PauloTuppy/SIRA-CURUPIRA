# Estrutura do Projeto - Sistema Inteligente de Recuperação Ambiental

## Nova Estrutura Proposta

```
ecosystem-recovery-ai/
├── README.md                                    # Documentação principal
├── .gitignore                                   # Git ignore rules
├── .env.example                                 # Template de variáveis de ambiente
├── docker-compose.yml                           # Desenvolvimento local
├── 
├── docs/                                        # Documentação
│   ├── architecture.md                          # Arquitetura detalhada
│   ├── development.md                           # Guia de desenvolvimento
│   ├── deployment.md                            # Guia de deploy
│   ├── api-specs/                               # Especificações OpenAPI
│   │   ├── backend-api.yaml
│   │   ├── rag-service-api.yaml
│   │   └── gpu-service-api.yaml
│   └── data-sources.md                          # Documentação das fontes
│
├── frontend/                                    # Frontend React/Vite
│   ├── src/
│   │   ├── components/                          # Componentes React (preservados)
│   │   │   ├── FileUpload.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── Sidebar.tsx
│   │   │   ├── ResultCard.tsx
│   │   │   ├── MapPlaceholder.tsx
│   │   │   └── icons.tsx
│   │   ├── services/                            # Serviços do frontend
│   │   │   ├── apiClient.ts                     # Cliente API principal
│   │   │   ├── sseClient.ts                     # Cliente SSE
│   │   │   └── geminiService.ts                 # Mantido para fallback
│   │   ├── types/                               # Tipos TypeScript
│   │   │   ├── api.ts                           # Tipos da API
│   │   │   ├── analysis.ts                      # Tipos de análise (preservados)
│   │   │   └── index.ts                         # Exports
│   │   ├── utils/                               # Utilitários
│   │   │   ├── config.ts                        # Configurações
│   │   │   └── constants.ts                     # Constantes
│   │   ├── App.tsx                              # App principal (aprimorado)
│   │   └── main.tsx                             # Entry point
│   ├── public/                                  # Assets públicos
│   ├── package.json                             # Dependências frontend
│   ├── tsconfig.json                            # Config TypeScript
│   ├── vite.config.ts                           # Config Vite
│   ├── firebase.json                            # Config Firebase Hosting
│   └── .firebaserc                              # Firebase projects
│
├── backend/                                     # Backend Python ADK + FastAPI
│   ├── src/
│   │   ├── main.py                              # FastAPI app
│   │   ├── config.py                            # Configurações
│   │   ├── models/                              # Modelos Pydantic
│   │   │   ├── __init__.py
│   │   │   ├── analysis.py                      # Modelos de análise
│   │   │   └── requests.py                      # Modelos de request
│   │   ├── services/                            # Serviços
│   │   │   ├── __init__.py
│   │   │   ├── coordinator.py                   # Coordinator service
│   │   │   ├── rag_client.py                    # Cliente RAG
│   │   │   └── gpu_client.py                    # Cliente GPU
│   │   ├── agents/                              # Agentes ADK
│   │   │   ├── __init__.py
│   │   │   ├── coordinator_agent.py             # Agente coordenador
│   │   │   ├── image_analysis_agent.py          # Agente análise de imagem
│   │   │   ├── ecosystem_balance_agent.py       # Agente equilíbrio ecológico
│   │   │   └── recovery_plan_agent.py           # Agente plano de recuperação
│   │   ├── api/                                 # Endpoints API
│   │   │   ├── __init__.py
│   │   │   ├── v1/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── analysis.py                  # Endpoints de análise
│   │   │   │   ├── history.py                   # Endpoints de histórico
│   │   │   │   └── health.py                    # Health checks
│   │   │   └── middleware.py                    # Middlewares
│   │   └── utils/                               # Utilitários
│   │       ├── __init__.py
│   │       ├── logging.py                       # Configuração de logs
│   │       └── exceptions.py                    # Exceções customizadas
│   ├── requirements.txt                         # Dependências Python
│   ├── Dockerfile                               # Container backend
│   ├── .dockerignore                            # Docker ignore
│   └── pytest.ini                               # Config testes
│
├── rag-service/                                 # RAG Service TypeScript Genkit
│   ├── src/
│   │   ├── index.ts                             # Entry point Genkit
│   │   ├── config.ts                            # Configurações
│   │   ├── services/                            # Serviços RAG
│   │   │   ├── ingestion.ts                     # Ingestão de dados
│   │   │   ├── retriever.ts                     # Recuperação contextual
│   │   │   ├── embeddings.ts                    # Geração de embeddings
│   │   │   └── vector-search.ts                 # Busca vetorial
│   │   ├── data-sources/                        # Conectores de dados
│   │   │   ├── gbif.ts                          # Conector GBIF
│   │   │   ├── iucn.ts                          # Conector IUCN
│   │   │   ├── obis.ts                          # Conector OBIS
│   │   │   └── ebird.ts                         # Conector eBird
│   │   ├── models/                              # Modelos TypeScript
│   │   │   ├── knowledge-base.ts                # Modelos base conhecimento
│   │   │   └── rag-types.ts                     # Tipos RAG
│   │   └── utils/                               # Utilitários
│   │       ├── firestore.ts                     # Helpers Firestore
│   │       └── vertex-ai.ts                     # Helpers Vertex AI
│   ├── package.json                             # Dependências Node.js
│   ├── tsconfig.json                            # Config TypeScript
│   ├── firebase.json                            # Config Firebase Functions
│   └── .firebaserc                              # Firebase projects
│
├── gpu-service/                                 # GPU Service Gemma 3
│   ├── src/
│   │   ├── main.py                              # FastAPI app GPU
│   │   ├── config.py                            # Configurações GPU
│   │   ├── models/                              # Modelos Pydantic
│   │   │   ├── __init__.py
│   │   │   ├── inference.py                     # Modelos de inferência
│   │   │   └── responses.py                     # Modelos de resposta
│   │   ├── services/                            # Serviços GPU
│   │   │   ├── __init__.py
│   │   │   ├── gemma_inference.py               # Inferência Gemma 3
│   │   │   ├── model_manager.py                 # Gerenciamento de modelos
│   │   │   └── cache_manager.py                 # Cache de inferências
│   │   ├── api/                                 # Endpoints GPU
│   │   │   ├── __init__.py
│   │   │   ├── inference.py                     # Endpoints inferência
│   │   │   ├── health.py                        # Health checks
│   │   │   └── metrics.py                       # Métricas performance
│   │   └── utils/                               # Utilitários GPU
│   │       ├── __init__.py
│   │       ├── gpu_utils.py                     # Utilitários GPU
│   │       └── model_utils.py                   # Utilitários modelo
│   ├── requirements.txt                         # Dependências Python GPU
│   ├── Dockerfile                               # Container GPU
│   ├── docker-compose.gpu.yml                   # Compose para GPU local
│   └── ollama/                                  # Configurações OLLAMA
│       ├── Modelfile                            # Definição modelo Gemma 3
│       └── setup.sh                             # Script setup OLLAMA
│
├── scripts/                                     # Scripts de automação
│   ├── setup/                                   # Scripts de setup
│   │   ├── install-dependencies.sh              # Instalar dependências
│   │   ├── setup-firebase.sh                    # Setup Firebase
│   │   └── setup-gcp.sh                         # Setup Google Cloud
│   ├── deploy/                                  # Scripts de deploy
│   │   ├── deploy-backend.sh                    # Deploy backend
│   │   ├── deploy-rag-service.sh                # Deploy RAG service
│   │   ├── deploy-gpu-service.sh                # Deploy GPU service
│   │   ├── deploy-frontend.sh                   # Deploy frontend
│   │   └── deploy-all.sh                        # Deploy completo
│   ├── data/                                    # Scripts de dados
│   │   ├── ingest-gbif.py                       # Ingestão GBIF
│   │   ├── ingest-iucn.py                       # Ingestão IUCN
│   │   ├── ingest-obis.py                       # Ingestão OBIS
│   │   └── ingest-ebird.py                      # Ingestão eBird
│   └── monitoring/                              # Scripts monitoramento
│       ├── health-check.sh                      # Health checks
│       └── performance-test.py                  # Testes performance
│
├── tests/                                       # Testes automatizados
│   ├── backend/                                 # Testes backend
│   │   ├── unit/                                # Testes unitários
│   │   ├── integration/                         # Testes integração
│   │   └── conftest.py                          # Config pytest
│   ├── rag-service/                             # Testes RAG
│   │   ├── unit/                                # Testes unitários
│   │   └── integration/                         # Testes integração
│   ├── gpu-service/                             # Testes GPU
│   │   ├── unit/                                # Testes unitários
│   │   └── integration/                         # Testes integração
│   ├── frontend/                                # Testes frontend
│   │   ├── unit/                                # Testes unitários
│   │   └── e2e/                                 # Testes end-to-end
│   └── common/                                  # Utilitários comuns
│       ├── fixtures.py                          # Fixtures compartilhadas
│       └── helpers.py                           # Helpers de teste
│
├── infrastructure/                              # Infraestrutura como código
│   ├── terraform/                               # Terraform configs
│   │   ├── main.tf                              # Configuração principal
│   │   ├── variables.tf                         # Variáveis
│   │   ├── outputs.tf                           # Outputs
│   │   └── modules/                             # Módulos Terraform
│   ├── kubernetes/                              # Manifests K8s (futuro)
│   └── monitoring/                              # Configs monitoramento
│       ├── dashboards/                          # Dashboards Grafana
│       └── alerts/                              # Regras de alerta
│
└── .github/                                     # GitHub Actions
    └── workflows/                               # CI/CD workflows
        ├── backend-ci.yml                       # CI backend
        ├── rag-service-ci.yml                   # CI RAG service
        ├── gpu-service-ci.yml                   # CI GPU service
        ├── frontend-ci.yml                      # CI frontend
        └── deploy.yml                           # Deploy workflow
```

## Migração da Estrutura Atual

### Preservar
- `sistema-inteligente-de-recuperação-ambiental (1)/components/` → `frontend/src/components/`
- `sistema-inteligente-de-recuperação-ambiental (1)/types.ts` → `frontend/src/types/analysis.ts`
- `sistema-inteligente-de-recuperação-ambiental (1)/services/geminiService.ts` → `frontend/src/services/`

### Evoluir
- `ecosystem-agents/` → `backend/src/agents/` (implementação completa)
- `firebase-backend/functions/` → `rag-service/` (nova implementação)

### Criar Novo
- `backend/` - Backend FastAPI completo
- `gpu-service/` - Serviço GPU Gemma 3
- `scripts/` - Automação e deploy
- `tests/` - Cobertura completa de testes
- `infrastructure/` - IaC e monitoramento
