#!/usr/bin/env python3
"""
Script para crear webhook automáticamente en GitHub
No necesitas ir al repositorio manualmente
"""

import os
from github import Github
from dotenv import load_dotenv

# Cargar configuración
load_dotenv()

def crear_webhook_automatico():
    """Crear webhook automáticamente usando la API de GitHub"""
    
    # Configuración desde .env
    github_token = os.getenv('GITHUB_TOKEN')
    github_secret = os.getenv('GITHUB_SECRET')
    owner = os.getenv('OWNER')
    repo_name = os.getenv('REPO')
    webhook_url = input("🔗 URL de tu webhook (ej: https://tu-servidor.com:8001/webhook): ").strip()
    
    if not webhook_url:
        webhook_url = "http://localhost:8001/webhook"  # Default para desarrollo
    
    if not all([github_token, github_secret, owner, repo_name]):
        print("❌ Faltan variables en .env:")
        print("   GITHUB_TOKEN, GITHUB_SECRET, OWNER, REPO")
        return False
    
    try:
        print(f"🔍 Conectando a GitHub como token...")
        github_client = Github(github_token)
        
        # Verificar autenticación
        user = github_client.get_user()
        print(f"✅ Autenticado como: {user.login}")
        
        # Obtener repositorio
        print(f"📁 Accediendo a repositorio: {owner}/{repo_name}")
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        print(f"✅ Repositorio encontrado: {repo.full_name}")
        
        # Verificar si ya existe un webhook
        print("🔍 Verificando webhooks existentes...")
        existing_webhooks = []
        try:
            hooks = repo.get_hooks()
            for hook in hooks:
                if hook.config.get('url') == webhook_url:
                    existing_webhooks.append(hook)
                    print(f"⚠️  Webhook ya existe: {hook.config.get('url')}")
        except Exception as e:
            print(f"⚠️  No se pudieron listar hooks existentes: {e}")
        
        if existing_webhooks:
            respuesta = input("❓ ¿Eliminar webhook existente y crear nuevo? (y/n): ")
            if respuesta.lower() == 'y':
                for hook in existing_webhooks:
                    hook.delete()
                    print(f"🗑️  Webhook eliminado: {hook.config.get('url')}")
            else:
                print("❌ Cancelado por el usuario")
                return False
        
        # Configuración del webhook
        webhook_config = {
            "url": webhook_url,
            "content_type": "json",
            "secret": github_secret,
            "insecure_ssl": "0"  # Usar SSL verificado
        }
        
        webhook_events = ["push"]  # Solo eventos de push
        
        # Crear webhook
        print("🚀 Creando webhook...")
        webhook = repo.create_hook(
            name="web",
            config=webhook_config,
            events=webhook_events,
            active=True
        )
        
        print("✅ ¡Webhook creado exitosamente!")
        print(f"🔗 URL: {webhook.config['url']}")
        print(f"📡 ID: {webhook.id}")
        print(f"📋 Eventos: {webhook.events}")
        print(f"🟢 Activo: {webhook.active}")
        
        # Probar webhook (ping)
        try:
            print("\n🧪 Enviando ping de prueba...")
            webhook.ping()
            print("✅ Ping enviado correctamente")
        except Exception as e:
            print(f"⚠️  Error en ping: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creando webhook: {str(e)}")
        
        if "Not Found" in str(e):
            print("💡 Posibles causas:")
            print("   - El repositorio no existe o no tienes acceso")
            print("   - Verifica OWNER y REPO en tu .env")
        elif "Bad credentials" in str(e):
            print("💡 Token de GitHub inválido:")
            print("   - Verifica GITHUB_TOKEN en tu .env")
            print("   - El token debe tener permisos 'repo'")
        elif "permissions" in str(e).lower():
            print("💡 Sin permisos:")
            print("   - Tu token necesita permisos de administrador del repo")
            print("   - O permisos 'admin:repo_hook'")
        
        return False

def listar_webhooks_existentes():
    """Listar webhooks existentes en el repositorio"""
    github_token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('OWNER')
    repo_name = os.getenv('REPO')
    
    try:
        github_client = Github(github_token)
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        
        print(f"📋 Webhooks en {repo.full_name}:")
        print("=" * 50)
        
        hooks = repo.get_hooks()
        count = 0
        
        for hook in hooks:
            count += 1
            print(f"🔗 Webhook #{count}:")
            print(f"   ID: {hook.id}")
            print(f"   URL: {hook.config.get('url', 'N/A')}")
            print(f"   Eventos: {hook.events}")
            print(f"   Activo: {'✅' if hook.active else '❌'}")
            print(f"   Creado: {hook.created_at}")
            print()
        
        if count == 0:
            print("📭 No hay webhooks configurados")
            
        return count
        
    except Exception as e:
        print(f"❌ Error listando webhooks: {str(e)}")
        return 0

def eliminar_webhook():
    """Eliminar un webhook específico"""
    github_token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('OWNER')
    repo_name = os.getenv('REPO')
    
    try:
        github_client = Github(github_token)
        repo = github_client.get_repo(f"{owner}/{repo_name}")
        
        # Listar webhooks
        hooks = list(repo.get_hooks())
        
        if not hooks:
            print("📭 No hay webhooks para eliminar")
            return
        
        print("📋 Webhooks disponibles:")
        for i, hook in enumerate(hooks):
            print(f"{i+1}. {hook.config.get('url', 'N/A')} (ID: {hook.id})")
        
        try:
            selection = int(input("❓ ¿Cuál webhook eliminar? (número): ")) - 1
            if 0 <= selection < len(hooks):
                hook = hooks[selection]
                hook.delete()
                print(f"✅ Webhook eliminado: {hook.config.get('url')}")
            else:
                print("❌ Selección inválida")
        except ValueError:
            print("❌ Debe ser un número")
            
    except Exception as e:
        print(f"❌ Error eliminando webhook: {str(e)}")

if __name__ == "__main__":
    print("🎯 Gestión Automática de Webhooks GitHub")
    print("=" * 40)
    
    while True:
        print("\n📋 Opciones:")
        print("1. 🚀 Crear webhook automáticamente")
        print("2. 📋 Listar webhooks existentes")
        print("3. 🗑️  Eliminar webhook")
        print("4. 🚪 Salir")
        
        opcion = input("\n❓ Elige opción (1-4): ").strip()
        
        if opcion == "1":
            print("\n🚀 Creando webhook...")
            if crear_webhook_automatico():
                print("\n🎉 ¡Webhook configurado! Tu repositorio ahora enviará")
                print("   notificaciones automáticamente a tu servidor.")
            
        elif opcion == "2":
            print("\n📋 Listando webhooks...")
            listar_webhooks_existentes()
            
        elif opcion == "3":
            print("\n🗑️ Eliminando webhook...")
            eliminar_webhook()
            
        elif opcion == "4":
            print("👋 ¡Hasta luego!")
            break
            
        else:
            print("❌ Opción inválida") 