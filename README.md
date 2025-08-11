# GitHub Webhook Simple

Webhook simple para capturar commits de GitHub y extraer contenido de archivos.

## 🚀 Características

- ✅ Captura commits automáticamente
- ✅ Extrae archivos añadidos/modificados
- ✅ Descarga contenido completo de archivos de código
- ✅ Genera JSON estructurado
- ✅ Verificación de firmas GitHub (HMAC)
- ✅ Soporte para Docker

## 📋 Requisitos

- Python 3.8+
- Token de GitHub con permisos de repositorio
- Webhook secret configurado

## ⚙️ Instalación

1. **Clonar repositorio:**
```bash
git clone <your-repo-url>
cd integration_ai
```

2. **Crear entorno virtual:**
```bash
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate
```

3. **Instalar dependencias:**
```bash
pip install -r requirements.txt
```

4. **Configurar variables de entorno:**
```bash
cp .env.example .env
# Editar .env con tus valores reales
```

5. **Ejecutar webhook:**
```bash
python webhook_simple.py
```

## 🔧 Configuración

### Variables de entorno (.env):

```env
GITHUB_TOKEN=ghp_your_github_token_here
GITHUB_SECRET=your_webhook_secret_here
OWNER=your_github_username
REPO=your_repository_name
```

### Configurar webhook en GitHub:

1. Ve a tu repositorio → Settings → Webhooks
2. Add webhook:
   - **URL**: `https://your-domain.com/webhook`
   - **Content type**: `application/json`
   - **Secret**: (el mismo que `GITHUB_SECRET`)
   - **Events**: `push`

## 🐳 Docker

```bash
# Construir imagen
docker-compose build

# Ejecutar
docker-compose up -d
```

## 📡 API

### POST /webhook
Recibe webhooks de GitHub.

### GET /health
Verificar estado del servicio.

## 📊 Respuesta JSON

```json
{
  "commit_id": "abc123...",
  "commit_message": "Fix bug",
  "author": "Developer",
  "timestamp": "2024-08-11T15:35:45Z",
  "changed_files": {
    "added": ["new_file.py"],
    "modified": ["existing_file.js"],
    "removed": []
  },
  "file_contents": [
    {
      "path": "new_file.py",
      "content": "print('Hello World')",
      "size": 20,
      "sha": "def456..."
    }
  ],
  "summary": {
    "total_files_changed": 2,
    "code_files_downloaded": 1,
    "files_removed": 0
  }
}
```

## 🔒 Seguridad

- Verificación HMAC de firmas GitHub
- Solo procesa eventos `push`
- Validación de cabeceras requeridas

## 🚀 Deployment

### Usando Docker:
```bash
docker-compose up -d
```

### Usando systemd:
```bash
# Crear servicio en /etc/systemd/system/webhook.service
sudo systemctl enable webhook
sudo systemctl start webhook
```

### Usando nginx (proxy reverso):
```nginx
location /webhook {
    proxy_pass http://localhost:8001;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

## 🛠️ Desarrollo

Para desarrollo local con ngrok:

```bash
# Terminal 1: Ejecutar webhook
python webhook_simple.py

# Terminal 2: Exponer con ngrok
ngrok http 8001

# Configurar webhook en GitHub con URL de ngrok
```

## 📝 Logs

El webhook imprime logs en tiempo real:
- Commits procesados
- Archivos descargados
- Errores de descarga

## 🔧 Troubleshooting

### Webhook no recibe eventos:
1. Verificar URL pública accesible
2. Verificar secret coincide
3. Verificar eventos `push` configurados

### Error 403 Invalid signature:
- Verificar `GITHUB_SECRET` en .env
- Verificar secret en configuración GitHub

### Error 500:
- Verificar logs del webhook
- Verificar `GITHUB_TOKEN` válido
- Verificar permisos del token

## 📄 Licencia

MIT License
