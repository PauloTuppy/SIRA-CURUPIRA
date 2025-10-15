#!/bin/bash

# SIRA Production Deployment Script
# Sistema Inteligente de Recuperação Ambiental

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$PROJECT_ROOT/.env.prod"
BACKUP_DIR="$PROJECT_ROOT/backups/$(date +%Y%m%d_%H%M%S)"

# Functions
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

check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check NVIDIA Docker (for GPU support)
    if ! docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi &> /dev/null; then
        log_warning "NVIDIA Docker runtime not available - GPU services may not work"
    fi
    
    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Production environment file not found: $ENV_FILE"
        log_info "Please create $ENV_FILE with production configuration"
        exit 1
    fi
    
    log_success "Prerequisites check completed"
}

backup_current_deployment() {
    log_info "Creating backup of current deployment..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup volumes
    if docker volume ls | grep -q "sira-.*-prod"; then
        log_info "Backing up Docker volumes..."
        docker run --rm -v sira-redis-data-prod:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/redis-data.tar.gz -C /data .
        docker run --rm -v sira-prometheus-data-prod:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/prometheus-data.tar.gz -C /data .
        docker run --rm -v sira-grafana-data-prod:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/grafana-data.tar.gz -C /data .
        docker run --rm -v sira-ollama-data-prod:/data -v "$BACKUP_DIR":/backup alpine tar czf /backup/ollama-data.tar.gz -C /data .
    fi
    
    # Backup configuration
    cp -r "$PROJECT_ROOT/monitoring" "$BACKUP_DIR/" 2>/dev/null || true
    cp "$ENV_FILE" "$BACKUP_DIR/" 2>/dev/null || true
    
    log_success "Backup created at $BACKUP_DIR"
}

build_images() {
    log_info "Building production images..."
    
    cd "$PROJECT_ROOT"
    
    # Build all services
    docker-compose -f docker-compose.prod.yml build --no-cache
    
    log_success "Images built successfully"
}

setup_monitoring() {
    log_info "Setting up monitoring configuration..."
    
    # Create monitoring directories
    mkdir -p "$PROJECT_ROOT/monitoring/prometheus"
    mkdir -p "$PROJECT_ROOT/monitoring/grafana/provisioning/datasources"
    mkdir -p "$PROJECT_ROOT/monitoring/grafana/provisioning/dashboards"
    
    # Create Prometheus production config
    cat > "$PROJECT_ROOT/monitoring/prometheus.prod.yml" << EOF
global:
  scrape_interval: 15s
  evaluation_interval: 15s

rule_files:
  # - "first_rules.yml"
  # - "second_rules.yml"

scrape_configs:
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  - job_name: 'sira-backend'
    static_configs:
      - targets: ['backend:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'sira-rag-service'
    static_configs:
      - targets: ['rag-service:8001']
    metrics_path: '/metrics'
    scrape_interval: 30s

  - job_name: 'sira-gpu-service'
    static_configs:
      - targets: ['gpu-service:8002']
    metrics_path: '/api/v1/metrics/prometheus'
    scrape_interval: 30s

  - job_name: 'redis'
    static_configs:
      - targets: ['redis:6379']
    scrape_interval: 30s
EOF

    # Create Grafana datasource config
    cat > "$PROJECT_ROOT/monitoring/grafana/provisioning/datasources/prometheus.yml" << EOF
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
EOF

    # Create Redis production config
    cat > "$PROJECT_ROOT/redis.prod.conf" << EOF
# Redis Production Configuration
bind 0.0.0.0
port 6379
requirepass ${REDIS_PASSWORD:-changeme}

# Memory management
maxmemory 512mb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Logging
loglevel notice
logfile /var/log/redis/redis-server.log

# Security
protected-mode yes
EOF

    log_success "Monitoring configuration created"
}

deploy_services() {
    log_info "Deploying SIRA services..."
    
    cd "$PROJECT_ROOT"
    
    # Load environment variables
    export $(cat "$ENV_FILE" | xargs)
    
    # Stop existing services
    docker-compose -f docker-compose.prod.yml down
    
    # Start services in order
    log_info "Starting infrastructure services..."
    docker-compose -f docker-compose.prod.yml up -d redis prometheus grafana
    
    log_info "Starting OLLAMA service..."
    docker-compose -f docker-compose.prod.yml up -d ollama
    
    # Wait for OLLAMA to be ready
    log_info "Waiting for OLLAMA to be ready..."
    timeout=300
    while [ $timeout -gt 0 ]; do
        if curl -f http://localhost:11434/api/tags &> /dev/null; then
            break
        fi
        sleep 5
        timeout=$((timeout - 5))
    done
    
    if [ $timeout -le 0 ]; then
        log_error "OLLAMA failed to start within timeout"
        exit 1
    fi
    
    log_info "Starting application services..."
    docker-compose -f docker-compose.prod.yml up -d rag-service gpu-service backend frontend
    
    log_success "All services deployed"
}

setup_ollama_models() {
    log_info "Setting up OLLAMA models..."
    
    # Pull required models
    docker exec sira-ollama-prod ollama pull gemma2:9b
    
    # Create custom SIRA model
    docker exec sira-ollama-prod sh -c "cd /app/ollama && ./setup.sh"
    
    log_success "OLLAMA models configured"
}

run_health_checks() {
    log_info "Running health checks..."
    
    services=("backend:8000" "rag-service:8001" "gpu-service:8002" "prometheus:9090" "grafana:3000")
    
    for service in "${services[@]}"; do
        service_name=$(echo $service | cut -d: -f1)
        port=$(echo $service | cut -d: -f2)
        
        log_info "Checking $service_name..."
        
        timeout=60
        while [ $timeout -gt 0 ]; do
            if curl -f "http://localhost:$port/health" &> /dev/null; then
                log_success "$service_name is healthy"
                break
            fi
            sleep 2
            timeout=$((timeout - 2))
        done
        
        if [ $timeout -le 0 ]; then
            log_error "$service_name health check failed"
            exit 1
        fi
    done
    
    log_success "All health checks passed"
}

setup_ssl() {
    log_info "Setting up SSL certificates..."
    
    # Create SSL directory
    mkdir -p "$PROJECT_ROOT/ssl"
    
    if [ ! -f "$PROJECT_ROOT/ssl/cert.pem" ] || [ ! -f "$PROJECT_ROOT/ssl/key.pem" ]; then
        log_warning "SSL certificates not found"
        log_info "Generating self-signed certificates for development..."
        
        openssl req -x509 -newkey rsa:4096 -keyout "$PROJECT_ROOT/ssl/key.pem" -out "$PROJECT_ROOT/ssl/cert.pem" -days 365 -nodes -subj "/C=BR/ST=SP/L=SaoPaulo/O=SIRA/CN=localhost"
        
        log_warning "Self-signed certificates generated. Replace with proper certificates for production."
    fi
    
    log_success "SSL setup completed"
}

show_deployment_info() {
    log_success "SIRA Production Deployment Completed!"
    echo
    echo "🌐 Service URLs:"
    echo "  Frontend:     http://localhost (HTTPS: https://localhost)"
    echo "  Backend API:  http://localhost:8000"
    echo "  RAG Service:  http://localhost:8001"
    echo "  GPU Service:  http://localhost:8002"
    echo "  Monitoring:   http://localhost:3000 (Grafana)"
    echo "  Metrics:      http://localhost:9090 (Prometheus)"
    echo
    echo "📊 Default Credentials:"
    echo "  Grafana: admin / ${GRAFANA_PASSWORD:-admin}"
    echo
    echo "📁 Important Directories:"
    echo "  Logs:    $PROJECT_ROOT/logs/"
    echo "  Backup:  $BACKUP_DIR"
    echo "  SSL:     $PROJECT_ROOT/ssl/"
    echo
    echo "🔧 Management Commands:"
    echo "  View logs:     docker-compose -f docker-compose.prod.yml logs -f [service]"
    echo "  Restart:       docker-compose -f docker-compose.prod.yml restart [service]"
    echo "  Stop all:      docker-compose -f docker-compose.prod.yml down"
    echo "  Update:        $0"
    echo
}

# Main deployment flow
main() {
    log_info "Starting SIRA Production Deployment"
    echo "======================================"
    
    check_prerequisites
    backup_current_deployment
    setup_monitoring
    setup_ssl
    build_images
    deploy_services
    setup_ollama_models
    run_health_checks
    show_deployment_info
    
    log_success "Deployment completed successfully!"
}

# Run main function
main "$@"
