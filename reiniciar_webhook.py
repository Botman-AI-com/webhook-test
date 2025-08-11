#!/usr/bin/env python3
"""
Reiniciar webhook: nuevo ngrok + actualizar GitHub + probar
"""

import os
import subprocess
import time
import requests
import json
from github import Github
from dotenv import load_dotenv

load_dotenv()

def kill_existing_processes():
    """Matar procesos existentes de webhook y ngrok"""
    print("🛑 Deteniendo procesos existentes...")
    
    try:
        # Matar webhook_simple
        result = subprocess.run(['pkill', '-f', 'webhook_simple.py'], capture_output=True)
        if result.returncode == 0:
            print("✅ webhook_simple detenido")
        
        # Matar ngrok
        result = subprocess.run(['pkill', '-f', 'ngrok'], capture_output=True)
        if result.returncode == 0:
            print("✅ ngrok detenido")
            
        time.sleep(2)  # Esperar a que terminen
        
    except Exception as e:
        print(f"⚠️  Error deteniendo procesos: {e}")

def start_webhook():
    """Iniciar webhook en background"""
    print("🚀 Iniciando webhook...")
    
    webhook_cmd = [
        'bash', '-c', 
        f'cd {os.getcwd()} && source venv/bin/activate && python webhook_simple.py'
    ]
    
    try:
        webhook_process = subprocess.Popen(
            webhook_cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(3)
        
        # Verificar
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Webhook funcionando en puerto 8001")
            return webhook_process
        else:
            print(f"❌ Webhook error: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error iniciando webhook: {e}")
        return None

def start_ngrok():
    """Iniciar ngrok y obtener nueva URL"""
    print("🌐 Iniciando ngrok...")
    
    try:
        ngrok_process = subprocess.Popen(
            ['ngrok', 'http', '8001'],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        time.sleep(4)
        
        response = requests.get("http://localhost:4040/api/tunnels", timeout=10)
        if response.status_code == 200:
            tunnels = response.json()
            if tunnels.get('tunnels'):
                public_url = tunnels['tunnels'][0]['public_url']
                print(f"✅ Nueva URL ngrok: {public_url}")
                return ngrok_process, public_url
        
        print("❌ No se pudo obtener URL de ngrok")
        ngrok_process.terminate()
        return None, None
        
    except Exception as e:
        print(f"❌ Error con ngrok: {e}")
        return None, None

def update_github_webhook(new_url):
    """Actualizar webhook existente en GitHub con nueva URL"""
    github_token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('OWNER')
    repo_name = os.getenv('REPO')
    github_secret = os.getenv('GITHUB_SECRET')
    
    try:
        print("🔄 Actualizando webhook en GitHub...")
        github_client = Github(github_token)
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        
        # Buscar webhook existente
        hooks = list(repo.get_hooks())
        webhook_updated = False
        
        for hook in hooks:
            existing_url = hook.config.get('url', '')
            # Si es un webhook ngrok, actualizarlo
            if 'ngrok' in existing_url or 'localhost' in existing_url:
                print(f"🔄 Actualizando webhook: {existing_url} → {new_url}/webhook")
                
                # Actualizar configuración
                hook.edit(
                    name="web",
                    config={
                        "url": f"{new_url}/webhook",
                        "content_type": "json",
                        "secret": github_secret,
                        "insecure_ssl": "0"
                    },
                    events=["push"],
                    active=True
                )
                
                print(f"✅ Webhook actualizado (ID: {hook.id})")
                webhook_updated = True
                break
        
        if not webhook_updated:
            # Crear nuevo webhook si no existe
            print("🆕 Creando nuevo webhook...")
            webhook = repo.create_hook(
                name="web",
                config={
                    "url": f"{new_url}/webhook",
                    "content_type": "json",
                    "secret": github_secret,
                    "insecure_ssl": "0"
                },
                events=["push"],
                active=True
            )
            print(f"✅ Nuevo webhook creado (ID: {webhook.id})")
        
        # Test ping
        try:
            print("🧪 Enviando ping de prueba...")
            # Obtener el webhook actualizado para ping
            hooks = list(repo.get_hooks())
            for hook in hooks:
                if f"{new_url}/webhook" in hook.config.get('url', ''):
                    hook.ping()
                    print("✅ Ping exitoso")
                    break
        except Exception as e:
            print(f"⚠️  Error en ping: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error actualizando webhook: {e}")
        return False

def test_push():
    """Hacer push de prueba para verificar webhook"""
    print("\n🧪 Haciendo push de prueba...")
    
    try:
        # Agregar línea al archivo
        with open('test.py', 'a') as f:
            f.write(f"\n# WEBHOOK REINICIADO - {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Git add, commit, push
        subprocess.run(['git', 'add', 'test.py'], check=True)
        subprocess.run(['git', 'commit', '-m', '🔥 Test webhook reiniciado'], check=True)
        result = subprocess.run(['git', 'push'], check=True, capture_output=True, text=True)
        
        print("✅ Push exitoso!")
        print("📡 El webhook debería recibir los datos ahora...")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en push: {e}")
        return False

def main():
    """Función principal"""
    print("🔄 Reiniciar Sistema Webhook Completo")
    print("=" * 40)
    
    # 1. Detener procesos existentes
    kill_existing_processes()
    
    # 2. Iniciar webhook
    webhook_process = start_webhook()
    if not webhook_process:
        print("❌ No se pudo iniciar webhook")
        return False
    
    # 3. Iniciar ngrok
    ngrok_process, public_url = start_ngrok()
    if not ngrok_process or not public_url:
        print("❌ No se pudo iniciar ngrok")
        webhook_process.terminate()
        return False
    
    # 4. Actualizar webhook en GitHub
    if not update_github_webhook(public_url):
        print("❌ No se pudo actualizar webhook en GitHub")
        webhook_process.terminate()
        ngrok_process.terminate()
        return False
    
    # 5. Test push
    if test_push():
        print("\n🎉 ¡Sistema webhook completamente reiniciado y funcionando!")
        print(f"🌐 Nueva URL: {public_url}")
        print(f"📡 Webhook: {public_url}/webhook")
        print(f"📁 Repositorio: {os.getenv('OWNER')}/{os.getenv('REPO')}")
        print("\n💡 El webhook ahora recibe pushes automáticamente")
        print("🛑 Presiona Ctrl+C para detener")
        
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
        print("❌ Error en test push")
        webhook_process.terminate()
        ngrok_process.terminate()
        return False

if __name__ == "__main__":
    if main():
        print("👋 ¡Reinicio completado!")
    else:
        print("❌ Error en reinicio")
        exit(1) 