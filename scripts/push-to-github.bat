@echo off
REM SIRA - Push to GitHub Repository Script (Windows)
REM Pushes the complete SIRA project to GitHub repository

setlocal enabledelayedexpansion

REM Repository information
set "REPO_URL=https://github.com/PauloTuppy/SIRA-CURUPIRA.git"
set "REPO_NAME=SIRA-CURUPIRA"
set "BRANCH=main"

REM Colors (limited support in Windows CMD)
set "INFO=[INFO]"
set "SUCCESS=[SUCCESS]"
set "WARNING=[WARNING]"
set "ERROR=[ERROR]"

echo 🌍 SIRA - Push to GitHub Repository
echo ==================================
echo.

REM Check if git is installed
git --version >nul 2>&1
if errorlevel 1 (
    echo %ERROR% Git is not installed. Please install Git first.
    pause
    exit /b 1
)
echo %SUCCESS% Git is available

REM Check if we're in the right directory
if not exist "docker-compose.yml" (
    echo %ERROR% This script must be run from the SIRA project root directory
    pause
    exit /b 1
)
if not exist "backend" (
    echo %ERROR% Backend directory not found
    pause
    exit /b 1
)
if not exist "frontend" (
    echo %ERROR% Frontend directory not found
    pause
    exit /b 1
)
echo %SUCCESS% In correct project directory

REM Initialize git repository if needed
if not exist ".git" (
    echo %INFO% Initializing Git repository...
    git init
    echo %SUCCESS% Git repository initialized
) else (
    echo %INFO% Git repository already exists
)

REM Create .gitignore if it doesn't exist
if not exist ".gitignore" (
    echo %INFO% Creating .gitignore file...
    (
        echo # Environment variables
        echo .env
        echo .env.local
        echo .env.prod
        echo .env.*.local
        echo.
        echo # Dependencies
        echo node_modules/
        echo __pycache__/
        echo *.pyc
        echo *.pyo
        echo *.pyd
        echo .Python
        echo pip-log.txt
        echo pip-delete-this-directory.txt
        echo.
        echo # IDE
        echo .vscode/
        echo .idea/
        echo *.swp
        echo *.swo
        echo *~
        echo.
        echo # OS
        echo .DS_Store
        echo .DS_Store?
        echo ._*
        echo .Spotlight-V100
        echo .Trashes
        echo ehthumbs.db
        echo Thumbs.db
        echo.
        echo # Logs
        echo *.log
        echo logs/
        echo npm-debug.log*
        echo yarn-debug.log*
        echo yarn-error.log*
        echo.
        echo # Runtime data
        echo pids
        echo *.pid
        echo *.seed
        echo *.pid.lock
        echo.
        echo # Coverage directory used by tools like istanbul
        echo coverage/
        echo *.lcov
        echo.
        echo # Build outputs
        echo dist/
        echo build/
        echo *.egg-info/
        echo.
        echo # Docker
        echo .dockerignore
        echo.
        echo # Temporary files
        echo tmp/
        echo temp/
        echo.
        echo # Firebase
        echo .firebase/
        echo firebase-debug.log
        echo firestore-debug.log
        echo.
        echo # Google Cloud
        echo .gcloudignore
        echo service-account-key.json
        echo.
        echo # Jupyter Notebook
        echo .ipynb_checkpoints
        echo.
        echo # pytest
        echo .pytest_cache/
        echo .coverage
        echo.
        echo # mypy
        echo .mypy_cache/
        echo .dmypy.json
        echo dmypy.json
        echo.
        echo # Backup files
        echo *.bak
        echo *.backup
        echo *.old
        echo.
        echo # Data files ^(large datasets^)
        echo data/raw/
        echo data/processed/
        echo *.csv
        echo *.json.gz
        echo *.parquet
        echo.
        echo # Model files
        echo models/*.bin
        echo models/*.safetensors
        echo ollama_data/
        echo.
        echo # Redis dumps
        echo dump.rdb
        echo.
        echo # Grafana data
        echo grafana_data/
        echo.
        echo # Prometheus data
        echo prometheus_data/
    ) > .gitignore
    echo %SUCCESS% .gitignore created
) else (
    echo %INFO% .gitignore already exists
)

REM Check if remote origin already exists
git remote get-url origin >nul 2>&1
if errorlevel 1 (
    echo %INFO% Adding remote origin: %REPO_URL%
    git remote add origin "%REPO_URL%"
    echo %SUCCESS% Remote origin added
) else (
    for /f "tokens=*" %%i in ('git remote get-url origin') do set "current_url=%%i"
    if "!current_url!" neq "%REPO_URL%" (
        echo %WARNING% Remote origin exists with different URL: !current_url!
        echo %INFO% Updating remote origin to: %REPO_URL%
        git remote set-url origin "%REPO_URL%"
    ) else (
        echo %INFO% Remote origin already set correctly
    )
)

REM Stage all files
echo %INFO% Staging all files...
git add .

REM Check if there are any changes to commit
git diff --staged --quiet
if errorlevel 1 (
    echo %SUCCESS% Files staged successfully
    
    REM Commit changes
    echo %INFO% Committing changes...
    git commit -m "🌍 SIRA - Sistema Inteligente de Recuperação Ambiental

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
    
    echo %SUCCESS% Changes committed
    
    REM Push to GitHub
    echo %INFO% Pushing to GitHub repository...
    
    REM Check if we need to set upstream
    git rev-parse --abbrev-ref --symbolic-full-name @{u} >nul 2>&1
    if errorlevel 1 (
        echo %INFO% Setting upstream branch...
        git push -u origin %BRANCH%
    ) else (
        git push origin %BRANCH%
    )
    
    echo %SUCCESS% Successfully pushed to GitHub!
    
    REM Display repository information
    echo.
    echo 🎉 SIRA project successfully pushed to GitHub!
    echo.
    echo Repository: %REPO_URL%
    echo Branch: %BRANCH%
    echo.
    echo You can now:
    echo 1. View your repository: https://github.com/PauloTuppy/SIRA-CURUPIRA
    echo 2. Clone it elsewhere: git clone %REPO_URL%
    echo 3. Set up GitHub Actions for CI/CD
    echo 4. Configure branch protection rules
    echo 5. Add collaborators and manage access
    echo.
    echo Next steps:
    echo - Set up GitHub Actions for automated testing
    echo - Configure deployment to Google Cloud
    echo - Set up issue templates and PR templates
    echo - Add GitHub Pages for documentation
    echo.
    
) else (
    echo %WARNING% No changes to commit
    echo %INFO% Repository is already up to date
    echo.
    echo Repository: %REPO_URL%
    echo No changes to push.
)

echo.
echo Press any key to continue...
pause >nul
