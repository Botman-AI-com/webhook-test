#!/bin/bash
# Script de deployment simple

echo "🚀 Deployment GitHub Webhook Simple"
echo "=================================="

# Verificar que estamos en el directorio correcto
if [ ! -f "webhook_simple.py" ]; then
    echo "❌ Error: webhook_simple.py no encontrado"
    echo "Ejecuta este script desde el directorio del proyecto"
    exit 1
fi

# Verificar .env
if [ ! -f ".env" ]; then
    echo "❌ Error: .env no encontrado"
    echo "Copia .env.example a .env y configura las variables"
    exit 1
fi

# Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual..."
    python3 -m venv venv
fi

# Activar entorno virtual
echo "🔧 Activando entorno virtual..."
source venv/bin/activate

# Instalar dependencias
echo "📋 Instalando dependencias..."
pip install -r requirements.txt

# Verificar configuración
echo "✅ Verificando configuración..."
python -c "
import os
from dotenv import load_dotenv
load_dotenv()

required = ['GITHUB_TOKEN', 'GITHUB_SECRET', 'OWNER', 'REPO']
missing = [var for var in required if not os.getenv(var)]

if missing:
    print(f'❌ Variables faltantes: {missing}')
    exit(1)
else:
    print('✅ Configuración completa')
"

if [ $? -ne 0 ]; then
    echo "❌ Error en configuración. Verifica tu .env"
    exit 1
fi

echo ""
echo "🎉 ¡Deployment listo!"
echo ""
echo "Para ejecutar:"
echo "  source venv/bin/activate"
echo "  python webhook_simple.py"
echo ""
echo "Para Docker:"
echo "  docker-compose up -d"
