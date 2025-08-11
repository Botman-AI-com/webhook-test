#!/usr/bin/env python3
"""
Webhook simple para GitHub - Solo lo esencial
Captura: commit ID, archivos cambiados, contenido de archivos
"""

import os
import hmac
import hashlib
import json
import base64
from typing import Dict, List, Any
from fastapi import FastAPI, Request, HTTPException
from github import Github
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

app = FastAPI(title="GitHub Webhook Simple")

# Configuración desde .env
GITHUB_TOKEN = os.getenv('GITHUB_TOKEN')
GITHUB_SECRET = os.getenv('GITHUB_SECRET')
OWNER = os.getenv('OWNER')
REPO = os.getenv('REPO')

def verify_github_signature(request: Request, body: bytes) -> None:
    """Verificar que el webhook viene realmente de GitHub"""
    signature = request.headers.get("X-Hub-Signature-256")
    if signature is None:
        raise HTTPException(400, "Missing signature header")
    
    sha_name, signature = signature.split('=', 1)
    mac = hmac.new(GITHUB_SECRET.encode(), msg=body, digestmod=hashlib.sha256)
    
    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(403, "Invalid signature")

def get_changed_files(payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """Extraer archivos que cambiaron del payload"""
    files = {"added": [], "modified": [], "removed": []}
    
    for commit in payload.get("commits", []):
        files["added"].extend(commit.get("added", []))
        files["modified"].extend(commit.get("modified", []))
        files["removed"].extend(commit.get("removed", []))
    
    # Quitar duplicados
    for key in files:
        files[key] = list(set(files[key]))
    
    return files

def is_code_file(file_path: str) -> bool:
    """Verificar si es un archivo de código que nos interesa"""
    code_extensions = {'.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.php', '.rb'}
    return any(file_path.lower().endswith(ext) for ext in code_extensions)

def download_file_content(file_path: str, commit_sha: str) -> Dict[str, Any]:
    """Descargar contenido de un archivo específico"""
    github_client = Github(GITHUB_TOKEN)
    repo = github_client.get_repo(f"{OWNER}/{REPO}")
    
    try:
        file_content = repo.get_contents(file_path, ref=commit_sha)
        
        if hasattr(file_content, 'content') and file_content.content:
            content = base64.b64decode(file_content.content).decode('utf-8')
            
            return {
                "path": file_path,
                "content": content,
                "size": len(content),
                "sha": file_content.sha
            }
    except Exception as e:
        print(f"Error descargando {file_path}: {str(e)}")
        return {"path": file_path, "content": None, "error": str(e)}

@app.post("/webhook")
async def github_webhook(request: Request):
    """Endpoint principal del webhook"""
    body = await request.body()
    
    # Verificar que viene de GitHub
    verify_github_signature(request, body)
    payload = json.loads(body)
    
    # Solo procesar push events
    if "commits" not in payload or not payload.get("commits"):
        return {"status": "ignored", "reason": "not a push event"}
    
    # Extraer información básica
    commit_sha = payload["after"]
    commit_info = payload["commits"][-1]  # Último commit
    
    print(f"📦 Procesando commit: {commit_sha[:8]} - {commit_info.get('message', '')}")
    
    # Obtener archivos que cambiaron
    changed_files = get_changed_files(payload)
    
    print(f"📊 Archivos cambiados:")
    print(f"   ➕ Añadidos: {len(changed_files['added'])}")
    print(f"   ✏️  Modificados: {len(changed_files['modified'])}")
    print(f"   🗑️  Eliminados: {len(changed_files['removed'])}")
    
    # Descargar contenido de archivos nuevos y modificados
    file_contents = []
    all_changed = changed_files["added"] + changed_files["modified"]
    
    for file_path in all_changed:
        if is_code_file(file_path):
            print(f"📁 Descargando: {file_path}")
            content_data = download_file_content(file_path, commit_sha)
            if content_data:
                file_contents.append(content_data)
    
    print(f"✅ Descargados: {len(file_contents)} archivos")
    
    # Crear respuesta JSON simple
    result = {
        "commit_id": commit_sha,
        "commit_message": commit_info.get("message", ""),
        "author": commit_info.get("author", {}).get("name", ""),
        "timestamp": commit_info.get("timestamp", ""),
        "changed_files": {
            "added": changed_files["added"],
            "modified": changed_files["modified"],
            "removed": changed_files["removed"]
        },
        "file_contents": file_contents,
        "summary": {
            "total_files_changed": len(all_changed),
            "code_files_downloaded": len(file_contents),
            "files_removed": len(changed_files["removed"])
        }
    }
    
    return result

@app.get("/health")
async def health_check():
    """Verificar que el servidor está funcionando"""
    return {
        "status": "ok",
        "service": "webhook-simple",
        "configured_repo": f"{OWNER}/{REPO}" if OWNER and REPO else "not configured"
    }

if __name__ == "__main__":
    print("🚀 Iniciando Webhook Simple para GitHub")
    print(f"📡 Configurado para: {OWNER}/{REPO}")
    print("🔗 Endpoints:")
    print("   POST /webhook - Recibir webhooks de GitHub")
    print("   GET /health - Verificar estado")
    
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 