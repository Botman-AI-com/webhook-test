#!/usr/bin/env python3
"""
Crear repositorio de prueba para testear webhook
"""

import os
import subprocess
import time
from github import Github
from dotenv import load_dotenv

load_dotenv()

def crear_repo_github():
    """Crear repositorio en GitHub usando la API"""
    github_token = os.getenv('GITHUB_TOKEN')
    owner = os.getenv('OWNER')
    
    repo_name = "webhook-test"
    
    try:
        print("🔍 Conectando a GitHub...")
        github_client = Github(github_token)
        
        # Obtener organización
        try:
            org = github_client.get_organization(owner)
            print(f"✅ Organización encontrada: {owner}")
            
            # Verificar si el repo ya existe
            try:
                existing_repo = org.get_repo(repo_name)
                print(f"⚠️  Repositorio ya existe: {existing_repo.html_url}")
                
                respuesta = input("❓ ¿Usar repo existente? (y/n): ")
                if respuesta.lower() != 'y':
                    print("❌ Cancelado")
                    return None
                return existing_repo
                
            except:
                # Repo no existe, crearlo
                print(f"🚀 Creando repositorio: {owner}/{repo_name}")
                repo = org.create_repo(
                    name=repo_name,
                    description="Repositorio de prueba para webhook GitHub → Neo4j",
                    private=False,
                    auto_init=False
                )
                print(f"✅ Repositorio creado: {repo.html_url}")
                return repo
                
        except:
            # Si no es una organización, usar cuenta personal
            user = github_client.get_user()
            print(f"✅ Usuario: {user.login}")
            
            try:
                existing_repo = user.get_repo(repo_name)
                print(f"⚠️  Repositorio ya existe: {existing_repo.html_url}")
                return existing_repo
            except:
                print(f"🚀 Creando repositorio personal: {repo_name}")
                repo = user.create_repo(
                    name=repo_name,
                    description="Repositorio de prueba para webhook GitHub → Neo4j",
                    private=False,
                    auto_init=False
                )
                print(f"✅ Repositorio creado: {repo.html_url}")
                return repo
                
    except Exception as e:
        print(f"❌ Error creando repositorio: {e}")
        return None

def inicializar_git_local(repo):
    """Inicializar git local y conectar con repo remoto"""
    try:
        print("\n📁 Inicializando git local...")
        
        # Inicializar git
        subprocess.run(['git', 'init'], check=True)
        print("✅ Git inicializado")
        
        # Configurar usuario (si no está configurado)
        try:
            subprocess.run(['git', 'config', 'user.name', 'Webhook Test'], check=True)
            subprocess.run(['git', 'config', 'user.email', 'webhook@test.com'], check=True)
            print("✅ Usuario git configurado")
        except:
            print("⚠️  Usuario git ya configurado")
        
        # Agregar remote
        subprocess.run(['git', 'remote', 'add', 'origin', repo.clone_url], check=True)
        print(f"✅ Remote agregado: {repo.clone_url}")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error configurando git: {e}")
        return False

def crear_archivos_test():
    """Crear archivos de prueba para el webhook"""
    archivos = {
        "README.md": """# 🎯 Webhook Test Repository

Este repositorio es para probar el webhook GitHub → Neo4j.

## ¿Qué hace?

Cada push envía automáticamente:
- ✅ Commit ID
- ✅ Archivos cambiados  
- ✅ Contenido completo de archivos
- ✅ Metadata del autor

## Webhook activo ✅

URL: https://tu-ngrok-url.ngrok-free.app/webhook
""",
        
        "test.py": """#!/usr/bin/env python3
'''
Archivo de prueba para webhook
'''

class WebhookTester:
    def __init__(self):
        self.name = "Webhook Test"
        self.version = "1.0"
    
    def test_commit(self):
        '''Simula cambios para activar webhook'''
        print(f"Testing webhook: {self.name} v{self.version}")
        return True

if __name__ == "__main__":
    tester = WebhookTester()
    tester.test_commit()
""",
        
        "example.js": """// Archivo JavaScript de prueba
class WebhookTest {
    constructor() {
        this.timestamp = new Date().toISOString();
    }
    
    triggerWebhook() {
        console.log(`Webhook triggered at: ${this.timestamp}`);
        return {
            status: 'success',
            message: 'Webhook test executed'
        };
    }
}

const test = new WebhookTest();
test.triggerWebhook();
""",
        
        "webhook_test.js": f"""console.log('Webhook test - {time.strftime("%Y-%m-%d %H:%M:%S")}');"""
    }
    
    print("📝 Creando archivos de prueba...")
    for filename, content in archivos.items():
        with open(filename, 'w') as f:
            f.write(content)
        print(f"✅ {filename}")
    
    return list(archivos.keys())

def hacer_commit_y_push(archivos):
    """Hacer commit y push de los archivos"""
    try:
        print("\n📤 Haciendo commit y push...")
        
        # Agregar archivos
        for archivo in archivos:
            subprocess.run(['git', 'add', archivo], check=True)
        
        # Commit
        subprocess.run([
            'git', 'commit', '-m', 
            '🚀 Initial commit - Testing webhook integration'
        ], check=True)
        print("✅ Commit creado")
        
        # Push
        print("📡 Pushing to GitHub... (esto activará el webhook)")
        subprocess.run(['git', 'push', '-u', 'origin', 'main'], check=True)
        print("✅ Push completado!")
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en commit/push: {e}")
        return False

def main():
    """Función principal"""
    print("🎯 Crear Repositorio de Prueba para Webhook")
    print("=" * 45)
    
    # 1. Crear repo en GitHub
    repo = crear_repo_github()
    if not repo:
        return False
    
    # 2. Inicializar git local
    if not inicializar_git_local(repo):
        return False
    
    # 3. Crear archivos de prueba
    archivos = crear_archivos_test()
    
    # 4. Commit y push (esto activará el webhook!)
    if hacer_commit_y_push(archivos):
        print("\n🎉 ¡Repositorio creado y push realizado!")
        print(f"🔗 Repositorio: {repo.html_url}")
        print("📡 El webhook debería haber recibido los datos automáticamente")
        print("\n💡 Para más pruebas, edita cualquier archivo y haz push:")
        print("   echo '// Nuevo cambio' >> test.py")
        print("   git add test.py")
        print("   git commit -m 'Test webhook again'")
        print("   git push")
        return True
    else:
        return False

if __name__ == "__main__":
    if main():
        print("\n✅ Setup completado exitosamente!")
    else:
        print("\n❌ Error en el setup") 