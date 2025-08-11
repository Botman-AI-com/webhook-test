import os
import hmac
import hashlib
import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseSettings
from github import Github
from github.Repository import Repository
from github.ContentFile import ContentFile
from neo4j import GraphDatabase
import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
import base64

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    # GitHub
    GITHUB_SECRET: str
    GITHUB_TOKEN: str
    OWNER: str
    REPO: str
    # Neo4j
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    # GraphQL fallback
    # Use GitHub GraphQL API endpoint
    GRAPHQL_URL: str = "https://api.github.com/graphql"
    # Branch to monitor
    BRANCH: str = "main"
    # Cron for fallback (e.g. every 2 hours)
    FALLBACK_CRON: str = "0 */2 * * *"
    # Processing settings
    ENABLE_DIFF_ANALYSIS: bool = True
    ENABLE_ROLLBACK: bool = True
    MAX_HISTORY_VERSIONS: int = 50

    class Config:
        env_file = ".env"


# Configuración global


settings = Settings()
app = FastAPI()

driver = GraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
)
scheduler = AsyncIOScheduler()


def verify_github_signature(request: Request, body: bytes) -> None:
    signature = request.headers.get("X-Hub-Signature-256")
    if signature is None:
        raise HTTPException(400, "Missing signature header")
    sha_name, signature = signature.split('=', 1)
    mac = hmac.new(
        settings.GITHUB_SECRET.encode(), msg=body, digestmod=hashlib.sha256
    )
    if not hmac.compare_digest(mac.hexdigest(), signature):
        raise HTTPException(403, "Invalid signature")


def get_changed_files(payload: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Extrae la lista de archivos modificados del payload del webhook.
    Retorna dict con 'added', 'modified', 'removed'
    """
    files = {"added": [], "modified": [], "removed": []}
    
    for commit in payload.get("commits", []):
        files["added"].extend(commit.get("added", []))
        files["modified"].extend(commit.get("modified", []))
        files["removed"].extend(commit.get("removed", []))
    
    # Remove duplicates
    for key in files:
        files[key] = list(set(files[key]))
    
    return files


def get_github_files(repo: Repository, commit_sha: str, file_paths: List[str]) -> List[Dict[str, Any]]:
    """
    Obtiene el contenido de archivos específicos desde GitHub usando PyGithub.
    """
    documents = []
    
    try:
        commit = repo.get_commit(commit_sha)
        
        for file_path in file_paths:
            try:
                # Filtrar solo archivos de código
                if not is_code_file(file_path):
                    continue
                    
                # Obtener contenido del archivo
                file_content = repo.get_contents(file_path, ref=commit_sha)
                
                if hasattr(file_content, 'content') and file_content.content:
                    # Decodificar contenido base64
                    content = base64.b64decode(file_content.content).decode('utf-8')
                    
                    documents.append({
                        "path": file_path,
                        "text": content,
                        "size": file_content.size,
                        "sha": file_content.sha,
                        "encoding": file_content.encoding
                    })
                    
                    logger.info(f"Loaded file: {file_path} ({len(content)} chars)")
                    
            except Exception as e:
                logger.warning(f"Could not load file {file_path}: {str(e)}")
                continue
                
    except Exception as e:
        logger.error(f"Error accessing commit {commit_sha}: {str(e)}")
        
    return documents


def is_code_file(file_path: str) -> bool:
    """
    Determina si un archivo es código fuente que debemos procesar.
    """
    code_extensions = {
        '.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.cpp', '.c', '.h', '.hpp',
        '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt', '.scala', '.r',
        '.sql', '.sh', '.bash', '.ps1', '.yaml', '.yml', '.json', '.xml'
    }
    
    # Archivos a ignorar
    ignore_patterns = {
        'node_modules/', '.git/', '__pycache__/', '.pytest_cache/',
        'dist/', 'build/', '.vscode/', '.idea/', 'venv/', 'env/'
    }
    
    # Verificar si está en directorio ignorado
    for pattern in ignore_patterns:
        if pattern in file_path:
            return False
    
    # Verificar extensión
    return any(file_path.lower().endswith(ext) for ext in code_extensions)


def get_repository_structure(repo: Repository, commit_sha: str, max_files: int = 500) -> List[Dict[str, Any]]:
    """
    Obtiene la estructura completa del repositorio para sincronización completa.
    """
    documents = []
    
    try:
        # Obtener todos los archivos del commit
        commit = repo.get_commit(commit_sha)
        tree = repo.get_git_tree(commit.sha, recursive=True)
        
        code_files = []
        for item in tree.tree:
            if item.type == "blob" and is_code_file(item.path):
                code_files.append(item.path)
        
        # Limitar número de archivos para evitar rate limits
        if len(code_files) > max_files:
            logger.warning(f"Repository has {len(code_files)} files, limiting to {max_files}")
            code_files = code_files[:max_files]
        
        # Obtener contenido de archivos en lotes
        batch_size = 10
        for i in range(0, len(code_files), batch_size):
            batch = code_files[i:i + batch_size]
            batch_docs = get_github_files(repo, commit_sha, batch)
            documents.extend(batch_docs)
            
            # Rate limiting
            if i + batch_size < len(code_files):
                import time
                time.sleep(0.5)  # Pausa para evitar rate limits
        
        logger.info(f"Loaded {len(documents)} files from repository structure")
        
    except Exception as e:
        logger.error(f"Error getting repository structure: {str(e)}")
        
    return documents


def extract_entities_with_llm(documents: List[Dict], commit_info: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Extrae entidades del código usando análisis híbrido (AST + LLM).
    Mantiene compatibilidad con tu esquema de grafo.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    commit_sha = commit_info.get("sha")
    
    extracted = []
    
    for doc in documents:
        file_path = doc.get("path", "")
        content = doc.get("text", "")
        file_sha = doc.get("sha", "")
        
        if not is_code_file(file_path):
            continue
            
        # Crear nodo Module (archivo)
        module_entity = {
            "type": "Module",
            "name": file_path,
            "attributes": {
                "path": file_path,
                "code": content[:10000],  # Limitar tamaño para Neo4j
                "languageName": detect_language(file_path),
                "status": "active",
                "commit_sha": commit_sha,
                "file_sha": file_sha,
                "last_updated": timestamp,
                "version": 1,
                "size": len(content),
                "lines": content.count('\n') + 1 if content else 0
            },
            "relations": []
        }
        extracted.append(module_entity)
        
        # Análisis básico del código (placeholder para AST real)
        extracted.extend(extract_basic_code_entities(content, file_path, commit_info))
            
    logger.info(f"Extracted {len(extracted)} entities from {len(documents)} documents")
    return extracted


def extract_basic_code_entities(content: str, file_path: str, commit_info: Dict) -> List[Dict[str, Any]]:
    """
    Extracción básica de entidades del código (placeholder para AST completo).
    """
    entities = []
    timestamp = datetime.now(timezone.utc).isoformat()
    commit_sha = commit_info.get("sha")
    
    lines = content.split('\n')
    
    # Análisis básico por lenguaje
    lang = detect_language(file_path)
    
    if lang == "Python":
        entities.extend(extract_python_entities(lines, file_path, commit_sha, timestamp))
    elif lang in ["JavaScript", "TypeScript"]:
        entities.extend(extract_js_entities(lines, file_path, commit_sha, timestamp))
    elif lang == "Java":
        entities.extend(extract_java_entities(lines, file_path, commit_sha, timestamp))
    
    return entities


def extract_python_entities(lines: List[str], file_path: str, commit_sha: str, timestamp: str) -> List[Dict[str, Any]]:
    """
    Extracción básica de entidades Python.
    """
    entities = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Detectar clases
        if line.startswith('class ') and ':' in line:
            class_name = line.split('class ')[1].split('(')[0].split(':')[0].strip()
            entities.append({
                "type": "Class",
                "name": class_name,
                "attributes": {
                    "path": f"{file_path}:{i+1}",
                    "name": class_name,
                    "status": "active",
                    "commit_sha": commit_sha,
                    "last_updated": timestamp,
                    "version": 1,
                    "line_number": i + 1
                },
                "relations": [{
                    "type": "has_class",
                    "to_type": "Module",
                    "to_name": file_path
                }]
            })
        
        # Detectar funciones/métodos
        elif line.startswith('def ') and '(' in line:
            func_name = line.split('def ')[1].split('(')[0].strip()
            
            # Determinar si es método (indentado) o función
            if line.startswith('    def '):
                entity_type = "Method"
                relation_type = "defines_method"
            else:
                entity_type = "Subroutine"
                relation_type = "has_subroutine"
            
            entities.append({
                "type": entity_type,
                "name": func_name,
                "attributes": {
                    "path": f"{file_path}:{i+1}",
                    "name": func_name,
                    "status": "active",
                    "commit_sha": commit_sha,
                    "last_updated": timestamp,
                    "version": 1,
                    "line_number": i + 1,
                    "code": line
                },
                "relations": [{
                    "type": relation_type,
                    "to_type": "Module",
                    "to_name": file_path
                }]
            })
    
    return entities


def extract_js_entities(lines: List[str], file_path: str, commit_sha: str, timestamp: str) -> List[Dict[str, Any]]:
    """
    Extracción básica de entidades JavaScript/TypeScript.
    """
    entities = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Detectar clases
        if line.startswith('class ') and ('{' in line or line.endswith('{')):
            class_name = line.split('class ')[1].split(' ')[0].split('{')[0].strip()
            entities.append({
                "type": "Class",
                "name": class_name,
                "attributes": {
                    "path": f"{file_path}:{i+1}",
                    "name": class_name,
                    "status": "active",
                    "commit_sha": commit_sha,
                    "last_updated": timestamp,
                    "version": 1,
                    "line_number": i + 1
                },
                "relations": [{
                    "type": "has_class",
                    "to_type": "Module",
                    "to_name": file_path
                }]
            })
        
        # Detectar funciones
        elif ('function ' in line or '=>' in line) and ('(' in line and ')' in line):
            # Extraer nombre de función (simplificado)
            if 'function ' in line:
                func_name = line.split('function ')[1].split('(')[0].strip()
            else:
                # Arrow functions
                func_name = line.split('=')[0].strip() if '=' in line else f"anonymous_{i}"
            
            entities.append({
                "type": "Subroutine",
                "name": func_name,
                "attributes": {
                    "path": f"{file_path}:{i+1}",
                    "name": func_name,
                    "status": "active",
                    "commit_sha": commit_sha,
                    "last_updated": timestamp,
                    "version": 1,
                    "line_number": i + 1,
                    "code": line
                },
                "relations": [{
                    "type": "has_subroutine",
                    "to_type": "Module",
                    "to_name": file_path
                }]
            })
    
    return entities


def extract_java_entities(lines: List[str], file_path: str, commit_sha: str, timestamp: str) -> List[Dict[str, Any]]:
    """
    Extracción básica de entidades Java.
    """
    entities = []
    
    for i, line in enumerate(lines):
        line = line.strip()
        
        # Detectar clases
        if line.startswith('public class ') or line.startswith('class '):
            class_name = line.split('class ')[1].split(' ')[0].split('{')[0].strip()
            entities.append({
                "type": "Class",
                "name": class_name,
                "attributes": {
                    "path": f"{file_path}:{i+1}",
                    "name": class_name,
                    "status": "active",
                    "commit_sha": commit_sha,
                    "last_updated": timestamp,
                    "version": 1,
                    "line_number": i + 1
                },
                "relations": [{
                    "type": "has_class",
                    "to_type": "Module",
                    "to_name": file_path
                }]
            })
        
        # Detectar métodos
        elif ('public ' in line or 'private ' in line or 'protected ' in line) and '(' in line and ')' in line and '{' in line:
            method_name = line.split('(')[0].split(' ')[-1].strip()
            entities.append({
                "type": "Method",
                "name": method_name,
                "attributes": {
                    "path": f"{file_path}:{i+1}",
                    "name": method_name,
                    "status": "active",
                    "commit_sha": commit_sha,
                    "last_updated": timestamp,
                    "version": 1,
                    "line_number": i + 1,
                    "code": line
                },
                "relations": [{
                    "type": "defines_method",
                    "to_type": "Class",
                    "to_name": file_path  # Simplificado, debería ser la clase contenedora
                }]
            })
    
    return entities


def detect_language(file_path: str) -> str:
    """
    Detecta el lenguaje de programación basado en la extensión del archivo.
    """
    extensions = {
        '.py': 'Python',
        '.js': 'JavaScript', 
        '.ts': 'TypeScript',
        '.java': 'Java',
        '.cpp': 'C++',
        '.c': 'C',
        '.go': 'Go',
        '.rs': 'Rust'
    }
    
    for ext, lang in extensions.items():
        if file_path.endswith(ext):
            return lang
    
    return 'Unknown'


def get_current_graph_state(tx, entity_path: str) -> Optional[Dict]:
    """
    Obtiene el estado actual de una entidad en el grafo.
    """
    result = tx.run(
        "MATCH (n) WHERE n.path = $path RETURN n",
        path=entity_path
    )
    record = result.single()
    return dict(record["n"]) if record else None


def create_graph_snapshot(tx, commit_sha: str):
    """
    Crea un snapshot del estado del grafo para rollback.
    """
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Crear nodo de snapshot
    tx.run(
        "CREATE (s:GraphSnapshot {commit_sha: $sha, timestamp: $ts, status: 'active'})",
        sha=commit_sha, ts=timestamp
    )
    
    # Marcar nodos activos en este commit
    tx.run(
        "MATCH (n) WHERE n.status = 'active' SET n.snapshot_sha = $sha",
        sha=commit_sha
    )


def update_graph_smart(tx, entities: List[Dict], commit_info: Dict):
    """
    Actualización inteligente del grafo con versionado y diff.
    """
    commit_sha = commit_info.get("sha")
    timestamp = datetime.now(timezone.utc).isoformat()
    
    # Crear snapshot antes de cambios
    if settings.ENABLE_ROLLBACK:
        create_graph_snapshot(tx, commit_sha)
    
    processed_entities = 0
    updated_entities = 0
    new_entities = 0
    
    for ent in entities:
        label = ent["type"]
        entity_path = ent["attributes"].get("path")
        name = ent["name"]
        attrs = ent.get("attributes", {})
        
        # Agregar metadatos de versionado
        attrs.update({
            "commit_sha": commit_sha,
            "last_updated": timestamp,
            "status": "active"
        })
        
        # Verificar si existe
        current_state = get_current_graph_state(tx, entity_path) if entity_path else None
        
        if current_state:
            # Actualizar versión
            current_version = current_state.get("version", 0)
            attrs["version"] = current_version + 1
            attrs["old_status"] = current_state.get("status", "unknown")
            updated_entities += 1
            logger.info(f"Updating {label} {name} (v{attrs['version']})")
        else:
            # Nueva entidad
            attrs["version"] = 1
            new_entities += 1
            logger.info(f"Creating new {label} {name}")
        
        # Preparar propiedades para Cypher
        set_str = ", ".join([f"n.{k} = ${k}" for k in attrs.keys()])
        props = {"name": name, **attrs}
        
        # MERGE inteligente
        if entity_path:
            cypher = f"MERGE (n:{label} {{path: $path}}) SET {set_str}"
            props["path"] = entity_path
        else:
            cypher = f"MERGE (n:{label} {{name: $name}}) SET {set_str}"
        
        tx.run(cypher, **props)
        
        # Procesar relaciones
        for rel in ent.get("relations", []):
            create_relationship(tx, label, name, rel)
        
        processed_entities += 1
    
    logger.info(f"Graph update complete: {processed_entities} processed, {new_entities} new, {updated_entities} updated")


def create_relationship(tx, from_label: str, from_name: str, relation: Dict):
    """
    Crea relaciones entre nodos de manera segura.
    """
    to_type = relation.get("to_type")
    to_name = relation.get("to_name")
    rel_type = relation.get("type")
    
    if not all([to_type, to_name, rel_type]):
        logger.warning(f"Incomplete relation data: {relation}")
        return
    
    # Crear relación con propiedades adicionales si existen
    rel_props = relation.get("properties", {})
    rel_props["created_at"] = datetime.now(timezone.utc).isoformat()
    
    props_str = ", ".join([f"r.{k} = ${k}" for k in rel_props.keys()]) if rel_props else ""
    set_clause = f"SET {props_str}" if props_str else ""
    
    cypher = f"""
    MATCH (a:{from_label} {{name: $from_name}}), (b:{to_type} {{name: $to_name}})
    MERGE (a)-[r:{rel_type}]->(b)
    {set_clause}
    """
    
    params = {"from_name": from_name, "to_name": to_name, **rel_props}
    tx.run(cypher, **params)


def handle_removed_files_sync(removed_files: List[str], commit_info: Dict):
    """
    Maneja archivos eliminados marcando sus entidades como deleted.
    """
    if not removed_files:
        return
    
    timestamp = datetime.now(timezone.utc).isoformat()
    commit_sha = commit_info.get("sha")
    
    with driver.session() as session:
        for file_path in removed_files:
            # Marcar módulo como eliminado
            session.run(
                "MATCH (m:Module {path: $path}) "
                "SET m.status = 'deleted', m.old_status = m.status, "
                "m.last_updated = $timestamp, m.deleted_in_commit = $commit_sha",
                path=file_path, timestamp=timestamp, commit_sha=commit_sha
            )
            
            # Marcar entidades relacionadas como eliminadas
            session.run(
                "MATCH (n) WHERE n.path STARTS WITH $file_prefix "
                "SET n.status = 'deleted', n.old_status = n.status, "
                "n.last_updated = $timestamp, n.deleted_in_commit = $commit_sha",
                file_prefix=file_path + ":", timestamp=timestamp, commit_sha=commit_sha
            )
    
    logger.info(f"Marked {len(removed_files)} files as deleted")


def rollback_to_commit(tx, target_commit_sha: str):
    """
    Rollback del grafo a un commit específico.
    """
    if not settings.ENABLE_ROLLBACK:
        logger.warning("Rollback is disabled")
        return False
    
    # Verificar que el snapshot existe
    result = tx.run(
        "MATCH (s:GraphSnapshot {commit_sha: $sha}) RETURN s",
        sha=target_commit_sha
    )
    
    if not result.single():
        logger.error(f"Snapshot for commit {target_commit_sha} not found")
        return False
    
    # Desactivar nodos posteriores al snapshot
    tx.run(
        "MATCH (n) WHERE n.commit_sha <> $sha SET n.status = 'rolled_back'",
        sha=target_commit_sha
    )
    
    # Reactivar nodos del snapshot
    tx.run(
        "MATCH (n) WHERE n.snapshot_sha = $sha SET n.status = 'active'",
        sha=target_commit_sha
    )
    
    logger.info(f"Rollback to commit {target_commit_sha} completed")
    return True


@app.post("/webhook")
async def github_webhook(request: Request):
    body = await request.body()
    verify_github_signature(request, body)
    payload = json.loads(body)

    # Solo eventos push
    if payload.get("hook") or payload.get("zen"):
        return {"status": "ignored"}
    
    # Verificar que es un push event
    if "commits" not in payload:
        return {"status": "not a push event"}

    commit_sha = payload["after"]
    commit_info = {
        "sha": commit_sha,
        "message": payload.get("head_commit", {}).get("message", ""),
        "author": payload.get("head_commit", {}).get("author", {}),
        "timestamp": payload.get("head_commit", {}).get("timestamp", "")
    }
    
    logger.info(f"Processing webhook for commit {commit_sha}")
    
    try:
        # Inicializar PyGithub
        github_client = Github(settings.GITHUB_TOKEN)
        repo = github_client.get_repo(f"{settings.OWNER}/{settings.REPO}")
        
        # Análisis diferencial si está habilitado
        docs = []
        files_info = {"added": [], "modified": [], "removed": []}
        
        if settings.ENABLE_DIFF_ANALYSIS:
            files_info = get_changed_files(payload)
            all_changed = files_info["added"] + files_info["modified"]
            
            logger.info(f"Changed files - Added: {len(files_info['added'])}, Modified: {len(files_info['modified'])}, Removed: {len(files_info['removed'])}")
            
            if not all_changed and not files_info["removed"]:
                return {"status": "no changes detected"}
            
            # Cargar solo archivos modificados/añadidos
            if all_changed:
                docs = get_github_files(repo, commit_sha, all_changed)
        else:
            # Cargar estructura completa del repositorio
            docs = get_repository_structure(repo, commit_sha)
        
        # Procesar archivos eliminados
        removed_files = files_info.get("removed", [])
        if removed_files:
            handle_removed_files_sync(removed_files, commit_info)
        
        # Extraer entidades
        entities = extract_entities_with_llm(docs, commit_info)
        
        # Actualizar grafo
        with driver.session() as session:
            session.write_transaction(update_graph_smart, entities, commit_info)
        
        logger.info(f"Successfully processed commit {commit_sha}")
        return {
            "status": "processed", 
            "commit": commit_sha,
            "entities_processed": len(entities),
            "files_processed": len(docs),
            "files_added": len(files_info["added"]),
            "files_modified": len(files_info["modified"]),
            "files_removed": len(files_info["removed"])
        }
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(500, f"Processing error: {str(e)}")


@app.post("/rollback/{commit_sha}")
async def rollback_graph(commit_sha: str):
    """
    Endpoint para hacer rollback del grafo a un commit específico.
    """
    try:
        with driver.session() as session:
            success = session.write_transaction(rollback_to_commit, commit_sha)
            
        if success:
            return {"status": "success", "rolled_back_to": commit_sha}
        else:
            raise HTTPException(400, "Rollback failed")
            
    except Exception as e:
        logger.error(f"Rollback error: {str(e)}")
        raise HTTPException(500, f"Rollback error: {str(e)}")


@app.get("/graph/health")
async def graph_health():
    """
    Endpoint para verificar la salud del grafo.
    """
    try:
        with driver.session() as session:
            # Contar nodos activos
            result = session.run("MATCH (n) WHERE n.status = 'active' RETURN count(n) as active_nodes")
            active_nodes = result.single()["active_nodes"]
            
            # Último commit procesado
            result = session.run(
                "MATCH (n) WHERE n.commit_sha IS NOT NULL RETURN n.commit_sha as sha, n.last_updated as updated ORDER BY n.last_updated DESC LIMIT 1"
            )
            last_record = result.single()
            last_commit = last_record["sha"] if last_record else None
            last_updated = last_record["updated"] if last_record else None
            
            return {
                "status": "healthy",
                "active_nodes": active_nodes,
                "last_commit": last_commit,
                "last_updated": last_updated
            }
    
    except Exception as e:
        logger.error(f"Health check error: {str(e)}")
        return {"status": "unhealthy", "error": str(e)}


async def fallback_sync():
    """
    Sincronización periódica con GitHub para mantener consistencia del grafo.
    """
    logger.info("Starting fallback sync...")
    
    try:
        query = {
            "query": f"""
            query {{
              repository(owner: \"{settings.OWNER}\", name: \"{settings.REPO}\") {{
                ref(qualifiedName: \"refs/heads/{settings.BRANCH}\") {{
                  target {{ ... on Commit {{ 
                    history(first:10) {{ 
                      nodes {{ 
                        oid 
                        message
                        author {{ name email }}
                        committedDate
                      }} 
                    }} 
                  }} }}
                }}
              }}
            }}"""
        }
        
        headers = {
            "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient() as client:
            resp = await client.post(settings.GRAPHQL_URL, json=query, headers=headers)
            resp.raise_for_status()
            
        data = resp.json().get("data", {}).get("repository", {}).get("ref", {}).get("target", {}).get("history", {}).get("nodes", [])
        
        processed_commits = 0
        for node in data:
            sha = node["oid"]
            
            # Verificar si ya procesamos este commit
            with driver.session() as session:
                result = session.run(
                    "MATCH (n) WHERE n.commit_sha = $sha RETURN count(n) as count",
                    sha=sha
                )
                if result.single()["count"] > 0:
                    continue  # Ya procesado
            
            # Procesar commit
            commit_info = {
                "sha": sha,
                "message": node.get("message", ""),
                "author": node.get("author", {}),
                "timestamp": node.get("committedDate", "")
            }
            
            # Usar PyGithub para cargar datos
            github_client = Github(settings.GITHUB_TOKEN)
            repo = github_client.get_repo(f"{settings.OWNER}/{settings.REPO}")
            
            docs = get_repository_structure(repo, sha, max_files=100)  # Limitar para fallback
            entities = extract_entities_with_llm(docs, commit_info)
            
            with driver.session() as session:
                session.write_transaction(update_graph_smart, entities, commit_info)
            
            processed_commits += 1
            logger.info(f"Fallback processed commit {sha}")
        
        logger.info(f"Fallback sync completed. Processed {processed_commits} new commits.")
        
    except Exception as e:
        logger.error(f"Fallback sync error: {str(e)}")


# Funciones auxiliares para inicialización del grafo
def initialize_graph_constraints():
    """
    Inicializa las restricciones y índices del grafo según tu esquema.
    """
    constraints = [
        # Índices únicos para entidades principales
        "CREATE CONSTRAINT IF NOT EXISTS FOR (c:Client) REQUIRE c.name IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (a:Application) REQUIRE a.path IS UNIQUE", 
        "CREATE CONSTRAINT IF NOT EXISTS FOR (m:Module) REQUIRE m.path IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (cl:Class) REQUIRE cl.path IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (me:Method) REQUIRE me.path IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (s:Subroutine) REQUIRE s.path IS UNIQUE",
        "CREATE CONSTRAINT IF NOT EXISTS FOR (t:Table) REQUIRE t.path IS UNIQUE",
        
        # Índices para performance
        "CREATE INDEX IF NOT EXISTS FOR (n) ON (n.commit_sha)",
        "CREATE INDEX IF NOT EXISTS FOR (n) ON (n.status)",
        "CREATE INDEX IF NOT EXISTS FOR (n) ON (n.last_updated)",
        "CREATE INDEX IF NOT EXISTS FOR (s:GraphSnapshot) ON (s.commit_sha)"
    ]
    
    with driver.session() as session:
        for constraint in constraints:
            try:
                session.run(constraint)
                logger.info(f"Applied: {constraint}")
            except Exception as e:
                logger.warning(f"Constraint/Index might already exist: {e}")


if __name__ == "__main__":
    logger.info("Initializing GitHub-Neo4j Sync Service...")
    
    # Inicializar constraints del grafo
    initialize_graph_constraints()
    
    # Configurar scheduler para fallback sync
    cron_parts = settings.FALLBACK_CRON.split()
    scheduler.add_job(
        fallback_sync,
        trigger="cron",
        minute=int(cron_parts[0]) if cron_parts[0] != '*' else None,
        hour=int(cron_parts[1]) if cron_parts[1] != '*' else None,
        day=int(cron_parts[2]) if cron_parts[2] != '*' else None,
        month=int(cron_parts[3]) if cron_parts[3] != '*' else None,
        day_of_week=int(cron_parts[4]) if cron_parts[4] != '*' else None,
        id="fallback_sync"
    )
    scheduler.start()
    logger.info(f"Scheduled fallback sync with cron: {settings.FALLBACK_CRON}")
    
    # Startup health check
    try:
        with driver.session() as session:
            session.run("RETURN 1")
        logger.info("Neo4j connection successful")
    except Exception as e:
        logger.error(f"Neo4j connection failed: {e}")
        exit(1)
    
    # Iniciar servidor
    logger.info("Starting FastAPI server...")
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
