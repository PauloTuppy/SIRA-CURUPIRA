#!/bin/bash

# Sistema Inteligente de Recuperação Ambiental
# Script de instalação de dependências

set -e

echo "🚀 Instalando dependências do SIRA..."

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

# Verificar se está no diretório raiz do projeto
if [ ! -f "package.json" ] && [ ! -f "frontend/package.json" ]; then
    error "Execute este script no diretório raiz do projeto"
    exit 1
fi

# Verificar Node.js
log "Verificando Node.js..."
if ! command -v node &> /dev/null; then
    error "Node.js não encontrado. Instale Node.js 18+ primeiro."
    exit 1
fi

NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    error "Node.js versão 18+ é necessária. Versão atual: $(node -v)"
    exit 1
fi
log "Node.js $(node -v) ✓"

# Verificar Python
log "Verificando Python..."
if ! command -v python3 &> /dev/null; then
    error "Python 3 não encontrado. Instale Python 3.11+ primeiro."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
if ! python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)'; then
    error "Python 3.11+ é necessário. Versão atual: $PYTHON_VERSION"
    exit 1
fi
log "Python $PYTHON_VERSION ✓"

# Verificar pip
if ! command -v pip3 &> /dev/null; then
    error "pip3 não encontrado. Instale pip primeiro."
    exit 1
fi

# Instalar Firebase CLI
log "Verificando Firebase CLI..."
if ! command -v firebase &> /dev/null; then
    log "Instalando Firebase CLI..."
    npm install -g firebase-tools
else
    log "Firebase CLI $(firebase --version) ✓"
fi

# Verificar Google Cloud CLI
log "Verificando Google Cloud CLI..."
if ! command -v gcloud &> /dev/null; then
    warn "Google Cloud CLI não encontrado. Instale manualmente:"
    warn "https://cloud.google.com/sdk/docs/install"
else
    log "Google Cloud CLI $(gcloud version --format='value(Google Cloud SDK)') ✓"
fi

# Instalar dependências do Frontend
log "Instalando dependências do Frontend..."
cd frontend
if [ -f "package.json" ]; then
    npm install
    log "Frontend dependencies ✓"
else
    warn "package.json não encontrado em frontend/"
fi
cd ..

# Instalar dependências do Backend
log "Instalando dependências do Backend..."
cd backend
if [ -f "requirements.txt" ]; then
    # Criar virtual environment se não existir
    if [ ! -d "venv" ]; then
        log "Criando virtual environment..."
        python3 -m venv venv
    fi
    
    # Ativar virtual environment
    source venv/bin/activate
    
    # Atualizar pip
    pip install --upgrade pip
    
    # Instalar dependências
    pip install -r requirements.txt
    
    log "Backend dependencies ✓"
    deactivate
else
    warn "requirements.txt não encontrado em backend/"
fi
cd ..

# Instalar dependências do RAG Service
log "Instalando dependências do RAG Service..."
cd rag-service
if [ -f "package.json" ]; then
    npm install
    log "RAG Service dependencies ✓"
else
    warn "package.json não encontrado em rag-service/"
fi
cd ..

# Instalar dependências do GPU Service
log "Instalando dependências do GPU Service..."
cd gpu-service
if [ -f "requirements.txt" ]; then
    # Criar virtual environment se não existir
    if [ ! -d "venv" ]; then
        log "Criando virtual environment..."
        python3 -m venv venv
    fi
    
    # Ativar virtual environment
    source venv/bin/activate
    
    # Atualizar pip
    pip install --upgrade pip
    
    # Instalar dependências
    pip install -r requirements.txt
    
    log "GPU Service dependencies ✓"
    deactivate
else
    warn "requirements.txt não encontrado em gpu-service/"
fi
cd ..

# Verificar Docker (opcional)
log "Verificando Docker..."
if command -v docker &> /dev/null; then
    log "Docker $(docker --version) ✓"
    
    # Verificar Docker Compose
    if command -v docker-compose &> /dev/null; then
        log "Docker Compose $(docker-compose --version) ✓"
    else
        warn "Docker Compose não encontrado. Instale para desenvolvimento local completo."
    fi
else
    warn "Docker não encontrado. Instale para desenvolvimento local completo."
fi

# Criar diretórios necessários
log "Criando diretórios necessários..."
mkdir -p logs
mkdir -p credentials
mkdir -p data

# Copiar arquivo de exemplo de environment
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        cp .env.example .env
        log "Arquivo .env criado a partir de .env.example"
        warn "Configure as variáveis de ambiente em .env antes de continuar"
    fi
fi

# Verificar OLLAMA (para GPU service)
log "Verificando OLLAMA..."
if command -v ollama &> /dev/null; then
    log "OLLAMA $(ollama --version) ✓"
else
    warn "OLLAMA não encontrado. Instale para o GPU Service:"
    warn "curl -fsSL https://ollama.ai/install.sh | sh"
fi

echo ""
log "✅ Instalação de dependências concluída!"
echo ""
echo -e "${BLUE}Próximos passos:${NC}"
echo "1. Configure as variáveis de ambiente em .env"
echo "2. Execute ./scripts/setup/setup-firebase.sh"
echo "3. Execute ./scripts/setup/setup-gcp.sh"
echo "4. Para desenvolvimento local: docker-compose up"
echo ""
echo -e "${BLUE}Documentação:${NC}"
echo "- README.md - Guia geral"
echo "- docs/development.md - Guia de desenvolvimento"
echo "- docs/architecture.md - Arquitetura detalhada"
