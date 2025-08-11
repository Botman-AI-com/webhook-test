#!/usr/bin/env python3
"""
Setup completo con ngrok: levanta webhook, obtiene URL pública, 
y configura automáticamente en GitHub
"""

import os
import sys
import subprocess
import time
import requests
import json
from dotenv import load_dotenv

def check_virtual_env():
    """Verificar si estamos en ambiente virtual"""
    return hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

def check_ngrok():
    """Verificar si ngrok está instalado"""
    try:
        result = subprocess.run(['ngrok', 'version'], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ ngrok encontrado: {result.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    
    print("❌ ngrok no encontrado")
    print("💡 Instala ngrok:")
    print("   - macOS: brew install ngrok")
    print("   - O descarga de: https://ngrok.com/download")
    return False

def start_webhook_background():
    """Iniciar webhook en background"""
    print("🚀 Iniciando webhook en background...")
    
    # Activar venv y ejecutar webhook
    webhook_cmd = [
        'bash', '-c', 
        f'cd {os.getcwd()} && source venv/bin/activate && python webhook_simple.py'
    ]
    
    try:
        # Iniciar webhook en background
        webhook_process = subprocess.Popen(
            webhook_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar a que inicie
        print("⏳ Esperando que el webhook inicie...")
        time.sleep(3)
        
        # Verificar que está funcionando
        try:
            response = requests.get("http://localhost:8001/health", timeout=5)
            if response.status_code == 200:
                print("✅ Webhook funcionando en puerto 8001")
                return webhook_process
            else:
                print(f"❌ Webhook responde pero con error: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ No se pudo conectar al webhook")
            webhook_process.terminate()
            return None
        except Exception as e:
            print(f"❌ Error verificando webhook: {e}")
            webhook_process.terminate()
            return None
            
    except Exception as e:
        print(f"❌ Error iniciando webhook: {e}")
        return None

def start_ngrok():
    """Iniciar ngrok y obtener URL pública"""
    print("🌐 Iniciando ngrok...")
    
    try:
        # Iniciar ngrok en background
        ngrok_process = subprocess.Popen(
            ['ngrok', 'http', '8001'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Esperar a que ngrok inicie
        print("⏳ Esperando que ngrok inicie...")
        time.sleep(4)
        
        # Obtener URL pública de ngrok
        try:
            response = requests.get("http://localhost:4040/api/tunnels", timeout=10)
            if response.status_code == 200:
                tunnels = response.json()
                if tunnels.get('tunnels'):
                    public_url = tunnels['tunnels'][0]['public_url']
                    print(f"✅ ngrok activo: {public_url}")
                    return ngrok_process, public_url
                else:
                    print("❌ No se encontraron túneles de ngrok")
            else:
                print(f"❌ Error obteniendo túneles: {response.status_code}")
        except requests.exceptions.ConnectionError:
            print("❌ ngrok API no disponible")
        except Exception as e:
            print(f"❌ Error obteniendo URL de ngrok: {e}")
        
        ngrok_process.terminate()
        return None, None
        
    except Exception as e:
        print(f"❌ Error iniciando ngrok: {e}")
        return None, None

def create_github_webhook(webhook_url):
    """Crear webhook en GitHub usando la API"""
    load_dotenv()
    
    github_token = os.getenv('GITHUB_TOKEN')
    github_secret = os.getenv('GITHUB_SECRET') 
    owner = os.getenv('OWNER')
    repo_name = os.getenv('REPO')
    
    if not all([github_token, github_secret, owner, repo_name]):
        print("❌ Faltan variables en .env: GITHUB_TOKEN, GITHUB_SECRET, OWNER, REPO")
        return False
    
    try:
        from github import Github
        
        print(f"🔍 Conectando a GitHub...")
        github_client = Github(github_token)
        
        # Verificar autenticación
        user = github_client.get_user()
        print(f"✅ Autenticado como: {user.login}")
        
        # Obtener repositorio
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        print(f"✅ Repositorio: {repo.full_name}")
        
        # Eliminar webhooks existentes con misma URL base
        print("🔍 Verificando webhooks existentes...")
        try:
            hooks = repo.get_hooks()
            for hook in hooks:
                existing_url = hook.config.get('url', '')
                # Si ya existe un webhook de ngrok, eliminarlo
                if 'ngrok.io' in existing_url or 'ngrok-free.app' in existing_url:
                    print(f"🗑️  Eliminando webhook ngrok anterior: {existing_url}")
                    hook.delete()
        except Exception as e:
            print(f"⚠️  Error listando hooks: {e}")
        
        # Crear nuevo webhook
        webhook_config = {
            "url": f"{webhook_url}/webhook",
            "content_type": "json",
            "secret": github_secret,
            "insecure_ssl": "0"
        }
        
        print(f"🚀 Creando webhook: {webhook_config['url']}")
        webhook = repo.create_hook(
            name="web",
            config=webhook_config,
            events=["push"],
            active=True
        )
        
        print("✅ ¡Webhook creado exitosamente!")
        print(f"🔗 URL: {webhook.config['url']}")
        print(f"📡 ID: {webhook.id}")
        
        # Probar webhook
        try:
            print("🧪 Enviando ping de prueba...")
            webhook.ping()
            print("✅ Ping enviado correctamente")
        except Exception as e:
            print(f"⚠️  Error en ping: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando webhook: {e}")
        return False

def main():
    """Función principal"""
    print("🎯 Setup Automático: Webhook + ngrok + GitHub")
    print("=" * 50)
    
    # Verificar requisitos
    if not check_virtual_env():
        print("❌ Debes estar en el ambiente virtual")
        print("💡 Ejecuta: source venv/bin/activate")
        return False
    
    if not check_ngrok():
        return False
    
    load_dotenv()
    if not all([os.getenv(var) for var in ['GITHUB_TOKEN', 'GITHUB_SECRET', 'OWNER', 'REPO']]):
        print("❌ Faltan variables en .env")
        return False
    
    print(f"✅ Configuración para: {os.getenv('OWNER')}/{os.getenv('REPO')}")
    
    # 1. Iniciar webhook
    webhook_process = start_webhook_background()
    if not webhook_process:
        print("❌ No se pudo iniciar el webhook")
        return False
    
    # 2. Iniciar ngrok
    ngrok_process, public_url = start_ngrok()
    if not ngrok_process or not public_url:
        print("❌ No se pudo iniciar ngrok")
        webhook_process.terminate()
        return False
    
    # 3. Crear webhook en GitHub
    if create_github_webhook(public_url):
        print("\n🎉 ¡Setup completado exitosamente!")
        print(f"🌐 URL pública: {public_url}")
        print(f"📡 Webhook: {public_url}/webhook")
        print("\n📋 Servicios activos:")
        print("   - Webhook local: http://localhost:8001")
        print("   - ngrok público: " + public_url)
        print("   - GitHub webhook configurado ✅")
        print("\n💡 Ahora cualquier push al repo enviará datos a tu webhook")
        print("🛑 Presiona Ctrl+C para detener todo")
        
        try:
            # Mantener servicios corriendo
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\n🛑 Deteniendo servicios...")
            webhook_process.terminate()
            ngrok_process.terminate()
            print("✅ Todo detenido")
            return True
    else:
        print("❌ Error configurando webhook en GitHub")
        webhook_process.terminate()
        ngrok_process.terminate()
        return False

if __name__ == "__main__":
    if main():
        print("👋 ¡Setup finalizado!")
    else:
        print("❌ Setup falló")
        sys.exit(1) 