#!/usr/bin/env python3
"""
SIRA - Teste Simples sem Docker
Testa a funcionalidade básica dos módulos Python
"""

import sys
import os
import asyncio
from pathlib import Path

# Adicionar o backend ao path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

def test_imports():
    """Testa se os imports básicos funcionam"""
    print("🧪 Testando imports básicos...")
    
    try:
        # Testar config
        from config import Settings
        print("✅ Config importado com sucesso")
        
        # Testar models
        from models.analysis import BiomeAnalysis, BiodiversityAnalysis
        print("✅ Models importados com sucesso")
        
        # Testar agents
        from agents.base import BaseAgent
        print("✅ Base Agent importado com sucesso")
        
        # Testar utils
        from utils.logging import setup_logging
        print("✅ Utils importados com sucesso")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no import: {e}")
        return False

def test_config():
    """Testa a configuração"""
    print("\n🔧 Testando configuração...")
    
    try:
        from config import Settings
        
        # Criar configuração de teste
        os.environ["SECRET_KEY"] = "test-secret-key"
        os.environ["ENVIRONMENT"] = "test"
        
        settings = Settings()
        
        print(f"✅ Environment: {settings.environment}")
        print(f"✅ Debug: {settings.debug}")
        print(f"✅ Secret Key configurado: {'Sim' if settings.secret_key else 'Não'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro na configuração: {e}")
        return False

def test_models():
    """Testa os modelos Pydantic"""
    print("\n📋 Testando modelos...")
    
    try:
        from models.analysis import BiomeAnalysis, BiodiversityAnalysis, RecoveryPlan
        
        # Testar BiomeAnalysis
        biome = BiomeAnalysis(
            primary_biome="Atlantic Forest",
            confidence=0.95,
            characteristics=["High biodiversity", "Fragmented"],
            threats=["Deforestation", "Urban expansion"],
            conservation_status="critically_endangered"
        )
        print(f"✅ BiomeAnalysis: {biome.primary_biome} ({biome.confidence})")
        
        # Testar BiodiversityAnalysis
        biodiversity = BiodiversityAnalysis(
            species_count=245,
            endemic_species=18,
            threatened_species=12,
            conservation_priority="high"
        )
        print(f"✅ BiodiversityAnalysis: {biodiversity.species_count} espécies")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos modelos: {e}")
        return False

def test_agents():
    """Testa os agentes"""
    print("\n🤖 Testando agentes...")
    
    try:
        from agents.base import BaseAgent
        from agents.coordinator import CoordinatorAgent
        
        # Testar BaseAgent
        base_agent = BaseAgent()
        print(f"✅ BaseAgent criado: {base_agent.__class__.__name__}")
        
        # Testar CoordinatorAgent
        coordinator = CoordinatorAgent()
        print(f"✅ CoordinatorAgent criado: {coordinator.__class__.__name__}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro nos agentes: {e}")
        return False

async def test_async_functionality():
    """Testa funcionalidade assíncrona"""
    print("\n⚡ Testando funcionalidade assíncrona...")
    
    try:
        from agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        
        # Testar método assíncrono básico
        result = await coordinator.process_analysis_request({
            "location": {
                "latitude": -23.5505,
                "longitude": -46.6333
            },
            "analysis_type": "basic"
        })
        
        print(f"✅ Análise processada: {type(result)}")
        return True
        
    except Exception as e:
        print(f"❌ Erro na funcionalidade assíncrona: {e}")
        return False

def test_logging():
    """Testa o sistema de logging"""
    print("\n📝 Testando logging...")
    
    try:
        from utils.logging import setup_logging
        import logging
        
        # Configurar logging
        setup_logging()
        logger = logging.getLogger("sira.test")
        
        logger.info("Teste de log INFO")
        logger.warning("Teste de log WARNING")
        logger.error("Teste de log ERROR")
        
        print("✅ Sistema de logging funcionando")
        return True
        
    except Exception as e:
        print(f"❌ Erro no logging: {e}")
        return False

def test_performance_module():
    """Testa o módulo de performance"""
    print("\n⚡ Testando módulo de performance...")
    
    try:
        from core.performance import PerformanceMonitor, performance_tracking
        
        # Testar PerformanceMonitor
        monitor = PerformanceMonitor()
        print(f"✅ PerformanceMonitor criado")
        
        # Testar decorator
        @performance_tracking("test_endpoint")
        async def test_function():
            await asyncio.sleep(0.1)
            return "test_result"
        
        # Executar função com tracking
        result = asyncio.run(test_function())
        print(f"✅ Performance tracking funcionando: {result}")
        
        return True
        
    except Exception as e:
        print(f"❌ Erro no módulo de performance: {e}")
        return False

async def main():
    """Função principal de teste"""
    print("🌍 SIRA - Teste Simples de Funcionalidade")
    print("=" * 50)
    
    tests = [
        ("Imports", test_imports),
        ("Configuração", test_config),
        ("Modelos", test_models),
        ("Agentes", test_agents),
        ("Logging", test_logging),
        ("Performance", test_performance_module),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ Erro no teste {test_name}: {e}")
            results.append((test_name, False))
    
    # Teste assíncrono separado
    print("\n⚡ Testando funcionalidade assíncrona...")
    try:
        async_result = await test_async_functionality()
        results.append(("Async", async_result))
    except Exception as e:
        print(f"❌ Erro no teste assíncrono: {e}")
        results.append(("Async", False))
    
    # Resumo
    print("\n📊 Resumo dos Testes")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\nResultado: {passed}/{total} testes passaram ({passed/total*100:.1f}%)")
    
    if passed == total:
        print("🎉 Todos os testes passaram! O código básico está funcionando.")
        return 0
    else:
        print("⚠️  Alguns testes falharam. Verifique os erros acima.")
        return 1

if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n⚠️  Testes interrompidos pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro geral nos testes: {e}")
        sys.exit(1)
