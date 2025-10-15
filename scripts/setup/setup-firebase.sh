#!/bin/bash

# Sistema Inteligente de Recuperação Ambiental
# Script de configuração do Firebase

set -e

# Cores para output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Função para log
log() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

echo "🔥 Configurando Firebase para SIRA..."

# Verificar se Firebase CLI está instalado
if ! command -v firebase &> /dev/null; then
    error "Firebase CLI não encontrado. Execute install-dependencies.sh primeiro."
    exit 1
fi

# Verificar se está logado no Firebase
log "Verificando autenticação Firebase..."
if ! firebase projects:list &> /dev/null; then
    log "Fazendo login no Firebase..."
    firebase login
fi

# Listar projetos disponíveis
log "Projetos Firebase disponíveis:"
firebase projects:list

# Solicitar ID do projeto
echo ""
read -p "Digite o ID do projeto Firebase (ou pressione Enter para criar novo): " PROJECT_ID

if [ -z "$PROJECT_ID" ]; then
    # Criar novo projeto
    read -p "Digite o ID para o novo projeto: " NEW_PROJECT_ID
    read -p "Digite o nome do projeto: " PROJECT_NAME
    
    log "Criando projeto Firebase: $NEW_PROJECT_ID"
    firebase projects:create "$NEW_PROJECT_ID" --display-name "$PROJECT_NAME"
    PROJECT_ID="$NEW_PROJECT_ID"
fi

# Configurar projeto
log "Configurando projeto: $PROJECT_ID"
firebase use "$PROJECT_ID"

# Inicializar Firebase no frontend
log "Configurando Firebase Hosting..."
cd frontend

if [ ! -f "firebase.json" ]; then
    log "Inicializando Firebase Hosting..."
    firebase init hosting --project "$PROJECT_ID" <<EOF
dist
y
n
n
EOF
else
    log "Firebase Hosting já configurado ✓"
fi

cd ..

# Inicializar Firebase Functions no RAG service
log "Configurando Firebase Functions..."
cd rag-service

if [ ! -f "firebase.json" ]; then
    log "Inicializando Firebase Functions..."
    firebase init functions --project "$PROJECT_ID" <<EOF
TypeScript
y
y
n
EOF
else
    log "Firebase Functions já configurado ✓"
fi

cd ..

# Configurar Firestore
log "Configurando Firestore..."
if ! firebase firestore:databases:list --project "$PROJECT_ID" | grep -q "(default)"; then
    log "Criando banco Firestore..."
    firebase firestore:databases:create --project "$PROJECT_ID" --location=us-central1
fi

# Criar regras de segurança do Firestore
log "Configurando regras de segurança do Firestore..."
cat > firestore.rules << 'EOF'
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Análises - acesso público para leitura, autenticado para escrita
    match /analyses/{analysisId} {
      allow read: if true;
      allow write: if request.auth != null;
    }
    
    // Base de conhecimento - apenas leitura
    match /knowledge_base/{docId} {
      allow read: if true;
      allow write: if false;
    }
    
    // Embeddings - apenas para serviços
    match /embeddings/{embeddingId} {
      allow read, write: if request.auth != null && 
        request.auth.token.email.matches('.*@.*\\.iam\\.gserviceaccount\\.com');
    }
    
    // Histórico de usuários
    match /users/{userId}/history/{historyId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }
  }
}
EOF

firebase deploy --only firestore:rules --project "$PROJECT_ID"

# Criar índices do Firestore
log "Configurando índices do Firestore..."
cat > firestore.indexes.json << 'EOF'
{
  "indexes": [
    {
      "collectionGroup": "knowledge_base",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "source",
          "order": "ASCENDING"
        },
        {
          "fieldPath": "timestamp",
          "order": "DESCENDING"
        }
      ]
    },
    {
      "collectionGroup": "embeddings",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "vector",
          "mode": "VECTOR"
        }
      ]
    },
    {
      "collectionGroup": "analyses",
      "queryScope": "COLLECTION",
      "fields": [
        {
          "fieldPath": "timestamp",
          "order": "DESCENDING"
        },
        {
          "fieldPath": "status",
          "order": "ASCENDING"
        }
      ]
    }
  ],
  "fieldOverrides": []
}
EOF

firebase deploy --only firestore:indexes --project "$PROJECT_ID"

# Configurar Storage
log "Configurando Firebase Storage..."
if ! gsutil ls -p "$PROJECT_ID" | grep -q "${PROJECT_ID}.appspot.com"; then
    log "Criando bucket Storage..."
    gsutil mb -p "$PROJECT_ID" gs://"${PROJECT_ID}".appspot.com
fi

# Criar regras de segurança do Storage
log "Configurando regras de segurança do Storage..."
cat > storage.rules << 'EOF'
rules_version = '2';
service firebase.storage {
  match /b/{bucket}/o {
    // Imagens de análise - upload autenticado, leitura pública
    match /analyses/{analysisId}/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null && 
        resource == null && 
        request.resource.size < 50 * 1024 * 1024 && // 50MB max
        request.resource.contentType.matches('image/.*|video/.*');
    }
    
    // Dados da base de conhecimento - apenas serviços
    match /knowledge_base/{allPaths=**} {
      allow read: if true;
      allow write: if request.auth != null && 
        request.auth.token.email.matches('.*@.*\\.iam\\.gserviceaccount\\.com');
    }
  }
}
EOF

firebase deploy --only storage --project "$PROJECT_ID"

# Habilitar APIs necessárias
log "Habilitando APIs do Google Cloud..."
gcloud services enable firestore.googleapis.com --project="$PROJECT_ID"
gcloud services enable storage-api.googleapis.com --project="$PROJECT_ID"
gcloud services enable cloudfunctions.googleapis.com --project="$PROJECT_ID"
gcloud services enable run.googleapis.com --project="$PROJECT_ID"
gcloud services enable aiplatform.googleapis.com --project="$PROJECT_ID"

# Criar service account para os serviços
log "Criando service accounts..."

# Service account para backend
if ! gcloud iam service-accounts describe backend-service@"$PROJECT_ID".iam.gserviceaccount.com --project="$PROJECT_ID" &> /dev/null; then
    gcloud iam service-accounts create backend-service \
        --display-name="Backend Service Account" \
        --project="$PROJECT_ID"
fi

# Service account para RAG service
if ! gcloud iam service-accounts describe rag-service@"$PROJECT_ID".iam.gserviceaccount.com --project="$PROJECT_ID" &> /dev/null; then
    gcloud iam service-accounts create rag-service \
        --display-name="RAG Service Account" \
        --project="$PROJECT_ID"
fi

# Service account para GPU service
if ! gcloud iam service-accounts describe gpu-service@"$PROJECT_ID".iam.gserviceaccount.com --project="$PROJECT_ID" &> /dev/null; then
    gcloud iam service-accounts create gpu-service \
        --display-name="GPU Service Account" \
        --project="$PROJECT_ID"
fi

# Atribuir permissões
log "Configurando permissões..."

# Permissões para backend service
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:backend-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:backend-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/storage.objectAdmin"

# Permissões para RAG service
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:rag-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/datastore.user"

gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:rag-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Permissões para GPU service
gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:gpu-service@$PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# Gerar chaves de service account
log "Gerando chaves de service account..."
mkdir -p credentials

gcloud iam service-accounts keys create credentials/backend-service-account.json \
    --iam-account=backend-service@"$PROJECT_ID".iam.gserviceaccount.com \
    --project="$PROJECT_ID"

gcloud iam service-accounts keys create credentials/rag-service-account.json \
    --iam-account=rag-service@"$PROJECT_ID".iam.gserviceaccount.com \
    --project="$PROJECT_ID"

gcloud iam service-accounts keys create credentials/gpu-service-account.json \
    --iam-account=gpu-service@"$PROJECT_ID".iam.gserviceaccount.com \
    --project="$PROJECT_ID"

# Atualizar .env com configurações do Firebase
log "Atualizando arquivo .env..."
if [ -f ".env" ]; then
    # Backup do .env atual
    cp .env .env.backup
    
    # Atualizar variáveis
    sed -i.bak "s/GOOGLE_CLOUD_PROJECT=.*/GOOGLE_CLOUD_PROJECT=$PROJECT_ID/" .env
    sed -i.bak "s/FIREBASE_PROJECT_ID=.*/FIREBASE_PROJECT_ID=$PROJECT_ID/" .env
    sed -i.bak "s/FIREBASE_STORAGE_BUCKET=.*/FIREBASE_STORAGE_BUCKET=${PROJECT_ID}.appspot.com/" .env
    
    rm .env.bak
fi

# Limpar arquivos temporários
rm -f firestore.rules storage.rules firestore.indexes.json

echo ""
log "✅ Configuração do Firebase concluída!"
echo ""
echo -e "${BLUE}Projeto configurado:${NC} $PROJECT_ID"
echo -e "${BLUE}Service accounts criados:${NC}"
echo "  - backend-service@$PROJECT_ID.iam.gserviceaccount.com"
echo "  - rag-service@$PROJECT_ID.iam.gserviceaccount.com"
echo "  - gpu-service@$PROJECT_ID.iam.gserviceaccount.com"
echo ""
echo -e "${BLUE}Próximos passos:${NC}"
echo "1. Configure as chaves de API no arquivo .env"
echo "2. Execute ./scripts/setup/setup-gcp.sh"
echo "3. Teste a configuração com: firebase serve"
