#!/bin/bash

# OLLAMA Setup Script for SIRA GPU Service
# This script sets up OLLAMA with Gemma 2 9B model for environmental recovery tasks

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
MODEL_NAME="${MODEL_NAME:-gemma2:9b}"
CUSTOM_MODEL_NAME="${CUSTOM_MODEL_NAME:-sira-gemma2:9b}"
MODELFILE_PATH="./ollama/Modelfile"

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Check if OLLAMA is running
check_ollama() {
    log "Checking OLLAMA connection at $OLLAMA_HOST..."
    
    if curl -s -f "$OLLAMA_HOST/api/tags" > /dev/null 2>&1; then
        success "OLLAMA is running and accessible"
        return 0
    else
        error "OLLAMA is not accessible at $OLLAMA_HOST"
        return 1
    fi
}

# Wait for OLLAMA to be ready
wait_for_ollama() {
    log "Waiting for OLLAMA to be ready..."
    
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if check_ollama; then
            return 0
        fi
        
        log "Attempt $attempt/$max_attempts - waiting 10 seconds..."
        sleep 10
        attempt=$((attempt + 1))
    done
    
    error "OLLAMA did not become ready after $max_attempts attempts"
    return 1
}

# List available models
list_models() {
    log "Listing available models..."
    
    if ! curl -s "$OLLAMA_HOST/api/tags" | jq -r '.models[].name' 2>/dev/null; then
        warning "Could not list models or jq not available"
        curl -s "$OLLAMA_HOST/api/tags" || error "Failed to connect to OLLAMA"
    fi
}

# Pull base model
pull_model() {
    local model=$1
    log "Pulling model: $model"
    
    # Use curl to pull model
    curl -X POST "$OLLAMA_HOST/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$model\"}" \
        --no-buffer | while IFS= read -r line; do
        if echo "$line" | jq -e '.status' > /dev/null 2>&1; then
            status=$(echo "$line" | jq -r '.status')
            if echo "$line" | jq -e '.completed' > /dev/null 2>&1; then
                completed=$(echo "$line" | jq -r '.completed')
                total=$(echo "$line" | jq -r '.total')
                percentage=$(echo "scale=1; $completed * 100 / $total" | bc 2>/dev/null || echo "0")
                log "Status: $status - ${percentage}%"
            else
                log "Status: $status"
            fi
        fi
    done
    
    success "Model $model pulled successfully"
}

# Create custom model from Modelfile
create_custom_model() {
    log "Creating custom model: $CUSTOM_MODEL_NAME"
    
    if [ ! -f "$MODELFILE_PATH" ]; then
        error "Modelfile not found at $MODELFILE_PATH"
        return 1
    fi
    
    # Read Modelfile content
    modelfile_content=$(cat "$MODELFILE_PATH")
    
    # Create model using API
    curl -X POST "$OLLAMA_HOST/api/create" \
        -H "Content-Type: application/json" \
        -d "{
            \"name\": \"$CUSTOM_MODEL_NAME\",
            \"modelfile\": $(echo "$modelfile_content" | jq -Rs .)
        }" \
        --no-buffer | while IFS= read -r line; do
        if echo "$line" | jq -e '.status' > /dev/null 2>&1; then
            status=$(echo "$line" | jq -r '.status')
            log "Status: $status"
        fi
    done
    
    success "Custom model $CUSTOM_MODEL_NAME created successfully"
}

# Test model
test_model() {
    local model=$1
    log "Testing model: $model"
    
    local test_prompt="What is biodiversity and why is it important for environmental recovery?"
    
    log "Sending test prompt: $test_prompt"
    
    response=$(curl -s -X POST "$OLLAMA_HOST/api/generate" \
        -H "Content-Type: application/json" \
        -d "{
            \"model\": \"$model\",
            \"prompt\": \"$test_prompt\",
            \"stream\": false
        }")
    
    if echo "$response" | jq -e '.response' > /dev/null 2>&1; then
        response_text=$(echo "$response" | jq -r '.response')
        log "Model response (first 200 chars): ${response_text:0:200}..."
        success "Model $model is working correctly"
        return 0
    else
        error "Model test failed"
        echo "Response: $response"
        return 1
    fi
}

# Get model info
get_model_info() {
    local model=$1
    log "Getting model information: $model"
    
    curl -s -X POST "$OLLAMA_HOST/api/show" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"$model\"}" | jq '.' 2>/dev/null || {
        warning "Could not get model info or jq not available"
        curl -s -X POST "$OLLAMA_HOST/api/show" \
            -H "Content-Type: application/json" \
            -d "{\"name\": \"$model\"}"
    }
}

# Main setup function
main() {
    log "Starting OLLAMA setup for SIRA GPU Service"
    log "OLLAMA Host: $OLLAMA_HOST"
    log "Base Model: $MODEL_NAME"
    log "Custom Model: $CUSTOM_MODEL_NAME"
    
    # Wait for OLLAMA
    if ! wait_for_ollama; then
        error "OLLAMA setup failed - service not available"
        exit 1
    fi
    
    # List current models
    log "Current models:"
    list_models
    
    # Check if base model exists
    if ! curl -s "$OLLAMA_HOST/api/tags" | grep -q "$MODEL_NAME"; then
        log "Base model $MODEL_NAME not found, pulling..."
        pull_model "$MODEL_NAME"
    else
        success "Base model $MODEL_NAME already available"
    fi
    
    # Create custom model
    log "Creating custom SIRA model..."
    create_custom_model
    
    # Test custom model
    log "Testing custom model..."
    test_model "$CUSTOM_MODEL_NAME"
    
    # Get model info
    log "Model information:"
    get_model_info "$CUSTOM_MODEL_NAME"
    
    # Final model list
    log "Final model list:"
    list_models
    
    success "OLLAMA setup completed successfully!"
    log "Custom model '$CUSTOM_MODEL_NAME' is ready for use"
    log "You can now start the GPU service with MODEL_NAME=$CUSTOM_MODEL_NAME"
}

# Handle script arguments
case "${1:-setup}" in
    "setup")
        main
        ;;
    "pull")
        wait_for_ollama && pull_model "${2:-$MODEL_NAME}"
        ;;
    "test")
        wait_for_ollama && test_model "${2:-$CUSTOM_MODEL_NAME}"
        ;;
    "list")
        wait_for_ollama && list_models
        ;;
    "info")
        wait_for_ollama && get_model_info "${2:-$CUSTOM_MODEL_NAME}"
        ;;
    "create")
        wait_for_ollama && create_custom_model
        ;;
    *)
        echo "Usage: $0 [setup|pull|test|list|info|create] [model_name]"
        echo "  setup  - Full setup (default)"
        echo "  pull   - Pull base model"
        echo "  test   - Test model"
        echo "  list   - List models"
        echo "  info   - Get model info"
        echo "  create - Create custom model"
        exit 1
        ;;
esac
