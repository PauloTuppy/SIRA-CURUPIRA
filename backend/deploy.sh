#!/bin/bash

# SIRA Backend Deployment Script
# Deploy to Google Cloud Run

set -e

# Configuration
PROJECT_ID=${GOOGLE_CLOUD_PROJECT:-"sira-project"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME="sira-backend"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

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

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if gcloud is installed
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI is not installed. Please install it first."
        exit 1
    fi
    
    # Check if docker is installed
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install it first."
        exit 1
    fi
    
    # Check if authenticated
    if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
        log_error "Not authenticated with gcloud. Run 'gcloud auth login' first."
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Set project
set_project() {
    log_info "Setting project to ${PROJECT_ID}..."
    gcloud config set project ${PROJECT_ID}
    log_success "Project set to ${PROJECT_ID}"
}

# Enable required APIs
enable_apis() {
    log_info "Enabling required APIs..."
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        containerregistry.googleapis.com \
        secretmanager.googleapis.com \
        redis.googleapis.com \
        monitoring.googleapis.com \
        logging.googleapis.com
    log_success "APIs enabled"
}

# Build and push image
build_and_push() {
    log_info "Building Docker image..."
    
    # Build image
    docker build -t ${IMAGE_NAME}:latest .
    
    # Tag with timestamp
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:${TIMESTAMP}
    
    log_info "Pushing image to Container Registry..."
    
    # Configure Docker for GCR
    gcloud auth configure-docker --quiet
    
    # Push images
    docker push ${IMAGE_NAME}:latest
    docker push ${IMAGE_NAME}:${TIMESTAMP}
    
    log_success "Image pushed: ${IMAGE_NAME}:latest"
    log_success "Image pushed: ${IMAGE_NAME}:${TIMESTAMP}"
}

# Create secrets
create_secrets() {
    log_info "Creating secrets in Secret Manager..."
    
    # Check if secrets exist, create if not
    secrets=("gemini-api-key" "jwt-secret-key" "redis-password")
    
    for secret in "${secrets[@]}"; do
        if ! gcloud secrets describe ${secret} &> /dev/null; then
            log_info "Creating secret: ${secret}"
            echo "CHANGE_ME_IN_PRODUCTION" | gcloud secrets create ${secret} --data-file=-
        else
            log_info "Secret ${secret} already exists"
        fi
    done
    
    log_success "Secrets created/verified"
}

# Create service account
create_service_account() {
    log_info "Creating service account..."
    
    SA_NAME="sira-backend-sa"
    SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
    
    # Create service account if it doesn't exist
    if ! gcloud iam service-accounts describe ${SA_EMAIL} &> /dev/null; then
        gcloud iam service-accounts create ${SA_NAME} \
            --display-name="SIRA Backend Service Account" \
            --description="Service account for SIRA Backend on Cloud Run"
    fi
    
    # Grant necessary roles
    roles=(
        "roles/secretmanager.secretAccessor"
        "roles/datastore.user"
        "roles/storage.objectViewer"
        "roles/aiplatform.user"
        "roles/monitoring.metricWriter"
        "roles/logging.logWriter"
    )
    
    for role in "${roles[@]}"; do
        gcloud projects add-iam-policy-binding ${PROJECT_ID} \
            --member="serviceAccount:${SA_EMAIL}" \
            --role="${role}" \
            --quiet
    done
    
    log_success "Service account created/configured: ${SA_EMAIL}"
}

# Deploy to Cloud Run
deploy_service() {
    log_info "Deploying to Cloud Run..."
    
    # Update cloudrun.yaml with actual project ID
    sed -i.bak "s/PROJECT_ID/${PROJECT_ID}/g" cloudrun.yaml
    
    # Deploy service
    gcloud run services replace cloudrun.yaml \
        --region=${REGION} \
        --quiet
    
    # Restore original cloudrun.yaml
    mv cloudrun.yaml.bak cloudrun.yaml
    
    # Get service URL
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
        --region=${REGION} \
        --format="value(status.url)")
    
    log_success "Service deployed successfully!"
    log_success "Service URL: ${SERVICE_URL}"
}

# Set IAM policy for public access (optional)
set_public_access() {
    if [[ "${ALLOW_PUBLIC_ACCESS:-false}" == "true" ]]; then
        log_info "Setting public access..."
        gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
            --region=${REGION} \
            --member="allUsers" \
            --role="roles/run.invoker"
        log_success "Public access enabled"
    else
        log_info "Skipping public access (set ALLOW_PUBLIC_ACCESS=true to enable)"
    fi
}

# Main deployment function
main() {
    log_info "Starting SIRA Backend deployment..."
    log_info "Project: ${PROJECT_ID}"
    log_info "Region: ${REGION}"
    log_info "Service: ${SERVICE_NAME}"
    
    check_prerequisites
    set_project
    enable_apis
    create_secrets
    create_service_account
    build_and_push
    deploy_service
    set_public_access
    
    log_success "Deployment completed successfully!"
    log_info "Next steps:"
    log_info "1. Update secrets in Secret Manager with actual values"
    log_info "2. Configure Redis instance if using Cloud Memorystore"
    log_info "3. Update CORS origins in environment variables"
    log_info "4. Test the deployment"
}

# Run main function
main "$@"
