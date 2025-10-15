#!/bin/bash

# SIRA - Push to GitHub Repository Script
# Pushes the complete SIRA project to GitHub repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Repository information
REPO_URL="https://github.com/PauloTuppy/SIRA-CURUPIRA.git"
REPO_NAME="SIRA-CURUPIRA"
BRANCH="main"

# Function to print colored output
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check if git is installed
check_git() {
    if ! command -v git &> /dev/null; then
        log_error "Git is not installed. Please install Git first."
        exit 1
    fi
    log_success "Git is available"
}

# Function to check if we're in the right directory
check_directory() {
    if [[ ! -f "docker-compose.yml" ]] || [[ ! -d "backend" ]] || [[ ! -d "frontend" ]]; then
        log_error "This script must be run from the SIRA project root directory"
        exit 1
    fi
    log_success "In correct project directory"
}

# Function to initialize git repository if needed
init_git_repo() {
    if [[ ! -d ".git" ]]; then
        log_info "Initializing Git repository..."
        git init
        log_success "Git repository initialized"
    else
        log_info "Git repository already exists"
    fi
}

# Function to create .gitignore if it doesn't exist
create_gitignore() {
    if [[ ! -f ".gitignore" ]]; then
        log_info "Creating .gitignore file..."
        cat > .gitignore << 'EOF'
# Environment variables
.env
.env.local
.env.prod
.env.*.local

# Dependencies
node_modules/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
pip-log.txt
pip-delete-this-directory.txt

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log
logs/
npm-debug.log*
yarn-debug.log*
yarn-error.log*

# Runtime data
pids
*.pid
*.seed
*.pid.lock

# Coverage directory used by tools like istanbul
coverage/
*.lcov

# Build outputs
dist/
build/
*.egg-info/

# Docker
.dockerignore

# Temporary files
tmp/
temp/

# Firebase
.firebase/
firebase-debug.log
firestore-debug.log

# Google Cloud
.gcloudignore
service-account-key.json

# Jupyter Notebook
.ipynb_checkpoints

# pytest
.pytest_cache/
.coverage

# mypy
.mypy_cache/
.dmypy.json
dmypy.json

# Backup files
*.bak
*.backup
*.old

# Data files (large datasets)
data/raw/
data/processed/
*.csv
*.json.gz
*.parquet

# Model files
models/*.bin
models/*.safetensors
ollama_data/

# Redis dumps
dump.rdb

# Grafana data
grafana_data/

# Prometheus data
prometheus_data/
EOF
        log_success ".gitignore created"
    else
        log_info ".gitignore already exists"
    fi
}

# Function to add remote origin
add_remote_origin() {
    # Check if remote origin already exists
    if git remote get-url origin &> /dev/null; then
        current_url=$(git remote get-url origin)
        if [[ "$current_url" != "$REPO_URL" ]]; then
            log_warning "Remote origin exists with different URL: $current_url"
            log_info "Updating remote origin to: $REPO_URL"
            git remote set-url origin "$REPO_URL"
        else
            log_info "Remote origin already set correctly"
        fi
    else
        log_info "Adding remote origin: $REPO_URL"
        git remote add origin "$REPO_URL"
        log_success "Remote origin added"
    fi
}

# Function to stage all files
stage_files() {
    log_info "Staging all files..."
    
    # Add all files
    git add .
    
    # Check if there are any changes to commit
    if git diff --staged --quiet; then
        log_warning "No changes to commit"
        return 1
    else
        log_success "Files staged successfully"
        return 0
    fi
}

# Function to commit changes
commit_changes() {
    log_info "Committing changes..."
    
    # Create comprehensive commit message
    commit_message="🌍 SIRA - Sistema Inteligente de Recuperação Ambiental

Complete implementation of SIRA (Intelligent Environmental Recovery System):

✅ Backend Service (FastAPI + ADK)
- Multi-agent architecture with CoordinatorAgent
- Biome identification and biodiversity analysis
- Recovery plan generation
- Integration with Google Gemini Vision API
- RESTful APIs with SSE streaming support

✅ RAG Service (TypeScript + Genkit)
- Integration with 4 scientific APIs (GBIF, IUCN, OBIS, eBird)
- Firestore Vector Search with Vertex AI embeddings
- Document processing and chunking
- Job management with progress tracking

✅ GPU Service (Python + OLLAMA)
- Gemma 2 9B model specialized for environmental data
- NVIDIA GPU acceleration support
- Advanced caching system (Redis + in-memory)
- Performance monitoring and metrics

✅ Frontend (React + Vite)
- Modern responsive interface
- Interactive analysis workflow
- Real-time streaming updates
- Environmental data visualization

✅ Infrastructure & DevOps
- Docker Compose for development and production
- Prometheus + Grafana monitoring stack
- Automated deployment scripts
- Comprehensive integration tests

✅ Documentation
- Complete user guide and API documentation
- Development setup instructions
- Production deployment guide
- Performance optimization guidelines

Features:
- Brazilian biome identification with high accuracy
- Biodiversity analysis using real scientific data
- AI-generated recovery plans for degraded areas
- Real-time streaming analysis with SSE
- Comprehensive monitoring and observability
- Production-ready containerized deployment

Technologies: Python, TypeScript, React, FastAPI, Genkit, OLLAMA, Docker, Firebase, Google Cloud, Prometheus, Grafana"

    git commit -m "$commit_message"
    log_success "Changes committed"
}

# Function to push to GitHub
push_to_github() {
    log_info "Pushing to GitHub repository..."
    
    # Check if we need to set upstream
    if ! git rev-parse --abbrev-ref --symbolic-full-name @{u} &> /dev/null; then
        log_info "Setting upstream branch..."
        git push -u origin "$BRANCH"
    else
        git push origin "$BRANCH"
    fi
    
    log_success "Successfully pushed to GitHub!"
}

# Function to display repository information
display_repo_info() {
    echo ""
    echo "🎉 SIRA project successfully pushed to GitHub!"
    echo ""
    echo "Repository: $REPO_URL"
    echo "Branch: $BRANCH"
    echo ""
    echo "You can now:"
    echo "1. View your repository: https://github.com/PauloTuppy/SIRA-CURUPIRA"
    echo "2. Clone it elsewhere: git clone $REPO_URL"
    echo "3. Set up GitHub Actions for CI/CD"
    echo "4. Configure branch protection rules"
    echo "5. Add collaborators and manage access"
    echo ""
    echo "Next steps:"
    echo "- Set up GitHub Actions for automated testing"
    echo "- Configure deployment to Google Cloud"
    echo "- Set up issue templates and PR templates"
    echo "- Add GitHub Pages for documentation"
    echo ""
}

# Main execution
main() {
    echo "🌍 SIRA - Push to GitHub Repository"
    echo "=================================="
    echo ""
    
    # Run all checks and operations
    check_git
    check_directory
    init_git_repo
    create_gitignore
    add_remote_origin
    
    # Stage files and check if there are changes
    if stage_files; then
        commit_changes
        push_to_github
        display_repo_info
    else
        log_info "Repository is already up to date"
        echo ""
        echo "Repository: $REPO_URL"
        echo "No changes to push."
    fi
}

# Run main function
main "$@"
