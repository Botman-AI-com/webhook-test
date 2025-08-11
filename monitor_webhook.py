#!/usr/bin/env python3
"""
Monitor webhook en tiempo real - ver logs y actividad
"""

import subprocess
import time
import requests
import json
from datetime import datetime

def test_webhook_health():
    """Verificar que el webhook está funcionando"""
    try:
        response = requests.get("http://localhost:8001/health", timeout=5)
        if response.status_code == 200:
            print("✅ Webhook funcionando")
            return True
        else:
            print(f"❌ Webhook error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Webhook no disponible: {e}")
        return False

def monitor_webhook_process():
    """Monitorear el proceso del webhook"""
    try:
        # Buscar el proceso del webhook
        result = subprocess.run(['pgrep', '-f', 'webhook_simple.py'], capture_output=True, text=True)
        
        if result.returncode == 0:
            pid = result.stdout.strip().split('\n')[0]
            print(f"🔍 Monitoreando proceso webhook PID: {pid}")
            return pid
        else:
            print("❌ No se encontró proceso webhook")
            return None
            
    except Exception as e:
        print(f"❌ Error buscando proceso: {e}")
        return None

def make_test_push():
    """Hacer push de prueba para activar webhook"""
    try:
        print("\n🧪 Haciendo push de prueba...")
        
        # Crear archivo de prueba
        timestamp = datetime.now().strftime("%H:%M:%S")
        test_content = f"""#!/usr/bin/env python3
# Archivo de prueba webhook
# Creado: {timestamp}
print("Webhook test funcionando!")
"""
        
        with open(f'test_webhook_{timestamp.replace(":", "")}.py', 'w') as f:
            f.write(test_content)
        
        # Git commands
        subprocess.run(['git', 'add', '.'], check=True)
        subprocess.run(['git', 'commit', '-m', f'🚀 Test webhook monitor {timestamp}'], check=True)
        result = subprocess.run(['git', 'push'], check=True, capture_output=True, text=True)
        
        print(f"✅ Push exitoso - {timestamp}")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Error en push: {e}")
        return False

def check_recent_logs():
    """Verificar logs recientes del sistema"""
    try:
        print("\n📋 Verificando logs recientes...")
        
        # Obtener commits recientes
        result = subprocess.run(['git', 'log', '--oneline', '-5'], capture_output=True, text=True)
        print("🗂️  Commits recientes:")
        for line in result.stdout.strip().split('\n'):
            print(f"   {line}")
            
        return True
        
    except Exception as e:
        print(f"❌ Error obteniendo logs: {e}")
        return False

def main():
    """Función principal de monitoreo"""
    print("🔍 MONITOR WEBHOOK TIEMPO REAL")
    print("=" * 40)
    
    # 1. Verificar salud del webhook
    if not test_webhook_health():
        print("❌ Webhook no está funcionando")
        return False
    
    # 2. Encontrar proceso
    pid = monitor_webhook_process()
    if not pid:
        return False
    
    # 3. Mostrar logs recientes
    check_recent_logs()
    
    # 4. Hacer push de prueba
    if make_test_push():
        print("\n⏱️  Esperando respuesta del webhook (10 segundos)...")
        time.sleep(10)
        
        print("\n📊 RESUMEN:")
        print("- ✅ Push realizado")
        print("- 📡 Webhook debería haber recibido datos")
        print("- 🔍 Revisar logs del proceso para confirmar")
        
        # Test adicional de salud
        if test_webhook_health():
            print("- ✅ Webhook sigue funcionando")
        else:
            print("- ❌ Webhook tiene problemas")
    
    print(f"\n💡 Para ver logs en tiempo real del proceso {pid}:")
    print(f"   lsof -p {pid}")
    print("\n🔄 Para hacer más tests:")
    print("   python monitor_webhook.py")
    
    return True

if __name__ == "__main__":
    if main():
        print("\n👀 ¡Monitoreo completado!")
    else:
        print("\n❌ Error en monitoreo") 