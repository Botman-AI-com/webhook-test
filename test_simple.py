#!/usr/bin/env python3
"""
Test simple para el webhook - Sin GitHub real
"""

import requests
import json
import hmac
import hashlib
import os
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

def create_test_payload():
    """Crear payload básico de prueba"""
    return {
        "ref": "refs/heads/main",
        "after": "abc123def456789",
        "commits": [{
            "id": "abc123def456789",
            "message": "Test commit message",
            "timestamp": datetime.now().isoformat(),
            "author": {
                "name": "Test User",
                "email": "test@example.com"
            },
            "added": ["src/test.py", "docs/readme.md"],
            "modified": ["src/main.py"],
            "removed": ["old_file.py"]
        }]
    }

def create_signature(payload_bytes, secret):
    """Crear signature para GitHub"""
    signature = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    return f"sha256={signature}"

def test_webhook():
    """Enviar webhook de prueba"""
    url = "http://localhost:8001/webhook"
    secret = os.getenv('GITHUB_SECRET')  # Usar el secret real del .env
    
    if not secret:
        print("❌ GITHUB_SECRET no encontrado en .env")
        return
    
    payload = create_test_payload()
    payload_json = json.dumps(payload)
    payload_bytes = payload_json.encode('utf-8')
    
    headers = {
        "Content-Type": "application/json",
        "X-Hub-Signature-256": create_signature(payload_bytes, secret),
        "X-GitHub-Event": "push"
    }
    
    print("🧪 Enviando webhook de prueba...")
    print(f"📦 Commit: {payload['after']}")
    print(f"📝 Message: {payload['commits'][0]['message']}")
    
    try:
        response = requests.post(url, data=payload_bytes, headers=headers, timeout=10)
        
        print(f"\n📈 Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Webhook procesado!")
            print(f"📋 Respuesta:")
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            print(f"❌ Error: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("❌ No se pudo conectar.")
        print("   ¿Está corriendo webhook_simple.py en puerto 8001?")
    except Exception as e:
        print(f"❌ Error: {str(e)}")

def test_health():
    """Probar endpoint de salud"""
    try:
        response = requests.get("http://localhost:8001/health")
        if response.status_code == 200:
            print("✅ Health check OK:")
            print(json.dumps(response.json(), indent=2))
        else:
            print(f"❌ Health check failed: {response.status_code}")
    except:
        print("❌ No se pudo conectar al health endpoint")

if __name__ == "__main__":
    print("🔧 Test Simple del Webhook")
    print("=" * 30)
    
    print("\n1. Probando health check...")
    test_health()
    
    print("\n2. Enviando webhook de prueba...")
    test_webhook()
    
    print("\n🏁 Test completado") 