#!/usr/bin/env python3
"""
Iniciador del webhook que se asegura de usar el ambiente correcto
"""

import os
import sys
import subprocess

def check_virtual_env():
    """Verificar si estamos en un ambiente virtual"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def start_webhook():
    """Iniciar el webhook"""
    print("🚀 Iniciando webhook GitHub...")
    
    # Verificar ambiente virtual
    if not check_virtual_env():
        print("⚠️  No estás en un ambiente virtual")
        print("💡 Ejecuta: source venv/bin/activate")
        return False
    
    # Verificar dependencias
    try:
        from github import Github
        from fastapi import FastAPI
        from dotenv import load_dotenv
        print("✅ Dependencias encontradas")
    except ImportError as e:
        print(f"❌ Falta dependencia: {e}")
        print("💡 Ejecuta: pip install fastapi uvicorn PyGithub python-dotenv requests")
        return False
    
    # Verificar .env
    load_dotenv()
    required_vars = ['GITHUB_TOKEN', 'GITHUB_SECRET', 'OWNER', 'REPO']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Faltan variables en .env: {missing_vars}")
        return False
    
    print(f"✅ Configuración válida para: {os.getenv('OWNER')}/{os.getenv('REPO')}")
    
    # Importar y ejecutar webhook
    try:
        print("🔗 Iniciando servidor webhook en puerto 8001...")
        print("📡 Endpoints disponibles:")
        print("   POST http://localhost:8001/webhook")
        print("   GET  http://localhost:8001/health")
        print("\n💡 Presiona Ctrl+C para detener")
        
        # Ejecutar el webhook
        exec(open('webhook_simple.py').read())
        
    except FileNotFoundError:
        print("❌ No se encontró webhook_simple.py")
        return False
    except KeyboardInterrupt:
        print("\n👋 Webhook detenido por el usuario")
        return True
    except Exception as e:
        print(f"❌ Error ejecutando webhook: {e}")
        return False

if __name__ == "__main__":
    if start_webhook():
        print("✅ Webhook finalizado correctamente")
    else:
        print("❌ Error al iniciar webhook")
        sys.exit(1) 