# 🎯 Webhook Simple GitHub

Webhook básico que captura **commit ID**, **archivos cambiados** y **contenido nuevo** de GitHub.

## 📋 Lo que hace

Cuando haces `git push`:
1. **GitHub envía webhook** → Tu servidor
2. **Captura información**:
   - ✅ ID del commit
   - ✅ Archivos añadidos/modificados/eliminados
   - ✅ Contenido completo de archivos de código
3. **Devuelve JSON** con toda la información

## 🚀 Uso Rápido

### 1. Instalar dependencias
```bash
pip install fastapi uvicorn PyGithub python-dotenv requests
```

### 2. Verificar tu .env
```bash
# Tu .env debe tener:
GITHUB_TOKEN=ghp_tu_token_aqui
GITHUB_SECRET=tu_webhook_secret  
OWNER=tu_usuario
REPO=tu_repositorio
```

### 3. Probar configuración
```bash
python test_github_connection.py
```

### 4. Ejecutar webhook
```bash
python webhook_simple.py
```

### 5. Probar sin GitHub real
```bash
# En otra terminal:
python test_simple.py
```

## 📡 Configurar en GitHub

1. Ve a tu repositorio → **Settings** → **Webhooks**
2. **Add webhook**:
   - URL: `http://tu-servidor:8000/webhook`
   - Content type: `application/json`
   - Secret: El valor de `GITHUB_SECRET` de tu .env
   - Events: Solo **Push events**

## 📊 Respuesta JSON

```json
{
  "commit_id": "abc123def456789...",
  "commit_message": "Add new feature",
  "author": "Tu Nombre",
  "timestamp": "2024-01-15T10:30:00Z",
  "changed_files": {
    "added": ["src/new_file.py"],
    "modified": ["src/main.py"],
    "removed": ["old_file.py"]
  },
  "file_contents": [
    {
      "path": "src/new_file.py",
      "content": "class NewClass:\n    def method(self):...",
      "size": 245,
      "sha": "def456..."
    }
  ],
  "summary": {
    "total_files_changed": 2,
    "code_files_downloaded": 1,
    "files_removed": 1
  }
}
```

## 🔍 Archivos que Procesa

- ✅ Python (`.py`)
- ✅ JavaScript (`.js`, `.ts`)  
- ✅ Java (`.java`)
- ✅ C/C++ (`.c`, `.cpp`)
- ✅ Go (`.go`)
- ✅ Rust (`.rs`)
- ✅ PHP (`.php`)
- ✅ Ruby (`.rb`)

## 🧪 Testing

### Probar con GitHub real
```bash
# 1. Ejecutar servidor
python webhook_simple.py

# 2. Hacer push a tu repo
git add .
git commit -m "Test webhook"  
git push origin main
```

### Probar sin GitHub
```bash
# Terminal 1:
python webhook_simple.py

# Terminal 2:  
python test_simple.py
```

## 🔧 Endpoints

- `POST /webhook` - Recibe webhooks de GitHub
- `GET /health` - Verificar que funciona

## 🐛 Problemas Comunes

**Error: "Missing signature header"**
```bash
# Verificar GITHUB_SECRET en .env
echo $GITHUB_SECRET
```

**Error: "Invalid signature"**
- Verificar que el secret en GitHub coincida con tu .env

**Error: conectando a GitHub**
```bash
# Probar conexión
python test_github_connection.py
```

**No encuentra archivos**
- Verificar que OWNER y REPO en .env sean correctos
- Verificar permisos del GITHUB_TOKEN

## ✨ Resultado

Cada push a GitHub te da un JSON completo con:
- **Commit ID** exacto
- **Lista de archivos** cambiados  
- **Contenido completo** de archivos nuevos
- **Información del autor** y timestamp

Perfecto para alimentar a tu parser de Neo4j o cualquier otro procesamiento! 🚀 