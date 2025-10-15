# SIRA GPU Service

Sistema Inteligente de Recuperação Ambiental - GPU Inference Service

## 🎯 Overview

The SIRA GPU Service is a high-performance inference service that provides local LLM capabilities using OLLAMA and Gemma 2 9B model, specifically optimized for environmental recovery and biodiversity conservation tasks in Brazil.

## 🚀 Features

- **Local LLM Inference**: OLLAMA integration with Gemma 2 9B model
- **GPU Acceleration**: NVIDIA L4 GPU support with CUDA
- **Environmental Specialization**: Custom model fine-tuned for Brazilian environmental data
- **High Performance**: Async FastAPI with concurrent request handling
- **Caching System**: Two-tier caching (Redis + in-memory) for optimal performance
- **Streaming Support**: Server-Sent Events for real-time responses
- **Batch Processing**: Efficient batch inference capabilities
- **Comprehensive Monitoring**: Prometheus metrics, health checks, GPU monitoring
- **Production Ready**: Docker containerization with multi-stage builds

## 🏗️ Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FastAPI App   │────│  Inference      │────│     OLLAMA      │
│   (Port 8002)   │    │   Service       │    │  (Port 11434)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │              ┌─────────────────┐              │
         │──────────────│  Cache Manager  │              │
         │              │ (Redis + Memory)│              │
         │              └─────────────────┘              │
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Metrics        │    │  Model Manager  │    │  GPU Monitoring │
│  Service        │    │                 │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Requirements

### Hardware
- NVIDIA GPU (L4 recommended, minimum 8GB VRAM)
- 16GB+ RAM
- 4+ CPU cores
- 50GB+ storage

### Software
- Docker & Docker Compose
- NVIDIA Container Toolkit
- Python 3.11+ (for local development)
- CUDA 12.0+ drivers

## 🛠️ Installation

### 1. Clone Repository
```bash
git clone <repository-url>
cd gpu-service
```

### 2. Environment Setup
```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

### 3. Docker Deployment (Recommended)
```bash
# Start all services
docker-compose -f docker-compose.gpu.yml up -d

# Check logs
docker-compose -f docker-compose.gpu.yml logs -f

# Setup OLLAMA model
docker exec -it sira-ollama bash /app/ollama/setup.sh
```

### 4. Local Development
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Start OLLAMA separately
ollama serve

# Run application
python -m src.main
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_NAME` | `gemma2:9b` | OLLAMA model name |
| `OLLAMA_HOST` | `http://localhost:11434` | OLLAMA server URL |
| `GPU_DEVICE_ID` | `0` | GPU device ID |
| `ENABLE_CACHE` | `true` | Enable caching |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `LOG_LEVEL` | `INFO` | Logging level |

See `.env.example` for complete configuration options.

### Model Configuration

The service uses a custom Gemma 2 9B model optimized for environmental tasks:

```bash
# Create custom model
docker exec -it sira-ollama ollama create sira-gemma2:9b -f /app/ollama/Modelfile

# Test model
curl -X POST http://localhost:8002/api/v1/inference/test
```

## 📚 API Documentation

### Base URL
- Development: `http://localhost:8002`
- Production: `https://your-domain.com`

### Endpoints

#### Health Checks
- `GET /health` - Basic health check
- `GET /health/ready` - Readiness check
- `GET /health/gpu` - GPU status

#### Inference
- `POST /api/v1/inference/generate` - Text generation
- `POST /api/v1/inference/generate/stream` - Streaming generation
- `POST /api/v1/inference/batch` - Batch processing

#### Models
- `GET /api/v1/models` - List models
- `GET /api/v1/models/{name}` - Model status
- `POST /api/v1/models/pull` - Pull model

#### Metrics
- `GET /api/v1/metrics` - Service metrics
- `GET /api/v1/metrics/prometheus` - Prometheus format
- `GET /api/v1/metrics/gpu` - GPU metrics

### Example Usage

#### Simple Generation
```bash
curl -X POST http://localhost:8002/api/v1/inference/generate \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "What are the main threats to Atlantic Forest biodiversity?",
    "options": {
      "temperature": 0.7,
      "max_tokens": 1000
    }
  }'
```

#### Streaming Generation
```bash
curl -X POST http://localhost:8002/api/v1/inference/generate/stream \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain ecosystem restoration techniques for Cerrado biome",
    "stream": true
  }'
```

#### Batch Processing
```bash
curl -X POST http://localhost:8002/api/v1/inference/batch \
  -H "Content-Type: application/json" \
  -d '{
    "requests": [
      {"prompt": "Describe Amazon rainforest biodiversity"},
      {"prompt": "What is the conservation status of jaguar?"}
    ],
    "parallel": true
  }'
```

## 🔍 Monitoring

### Health Checks
```bash
# Basic health
curl http://localhost:8002/health

# Detailed health with system info
curl http://localhost:8002/health/detailed

# GPU status
curl http://localhost:8002/health/gpu
```

### Metrics
```bash
# Service metrics
curl http://localhost:8002/api/v1/metrics

# Prometheus metrics
curl http://localhost:8002/api/v1/metrics/prometheus

# Performance metrics
curl http://localhost:8002/api/v1/metrics/performance
```

### Grafana Dashboard
Access Grafana at `http://localhost:3001` (admin/admin123) for visual monitoring.

## 🧪 Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Test specific module
pytest tests/test_inference.py -v

# Integration tests
pytest tests/integration/ -v
```

## 🚀 Deployment

### Docker Production
```bash
# Build production image
docker build -t sira-gpu-service:latest .

# Run with GPU support
docker run --gpus all -p 8002:8002 \
  -e ENVIRONMENT=production \
  -e OLLAMA_HOST=http://ollama:11434 \
  sira-gpu-service:latest
```

### Google Cloud Run (with GPU)
```bash
# Build and push
gcloud builds submit --tag gcr.io/PROJECT_ID/sira-gpu-service

# Deploy with GPU
gcloud run deploy sira-gpu-service \
  --image gcr.io/PROJECT_ID/sira-gpu-service \
  --platform managed \
  --region us-central1 \
  --gpu 1 \
  --gpu-type nvidia-l4 \
  --memory 8Gi \
  --cpu 4
```

## 🔧 Troubleshooting

### Common Issues

1. **GPU Not Detected**
   ```bash
   # Check NVIDIA drivers
   nvidia-smi
   
   # Check Docker GPU support
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

2. **OLLAMA Connection Failed**
   ```bash
   # Check OLLAMA status
   curl http://localhost:11434/api/tags
   
   # Restart OLLAMA
   docker restart sira-ollama
   ```

3. **Model Not Found**
   ```bash
   # Pull model manually
   docker exec -it sira-ollama ollama pull gemma2:9b
   
   # Create custom model
   docker exec -it sira-ollama bash /app/ollama/setup.sh
   ```

4. **High Memory Usage**
   ```bash
   # Check GPU memory
   nvidia-smi
   
   # Adjust GPU memory fraction
   export GPU_MEMORY_FRACTION=0.6
   ```

### Logs
```bash
# Service logs
docker logs sira-gpu-service -f

# OLLAMA logs
docker logs sira-ollama -f

# All services
docker-compose -f docker-compose.gpu.yml logs -f
```

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📄 License

This project is part of the SIRA (Sistema Inteligente de Recuperação Ambiental) initiative.

## 🆘 Support

For support and questions:
- Create an issue in the repository
- Contact the SIRA development team
- Check the documentation at `/docs` endpoint

---

**SIRA GPU Service** - Powering environmental recovery with AI 🌱🤖
