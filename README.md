# Monitorización ligera de servidores Linux mediante SSH

Este proyecto consiste en una herramienta web ligera y segura diseñada para la monitorización remota y la gestión básica de servidores Linux.
Pensada especialmente para pequeñas empresas o entornos educativos con redes de hasta 15 servidores.

## 🔧 Funcionalidades principales

- Monitorización en tiempo real de CPU, RAM y disco
- Visualización de métricas vía interfaz web
- Gestión remota de usuarios y grupos
- Instalación/desinstalación de paquetes en servidores remotos
- Conexión mediante SSH seguro (Paramiko)
- Backend en Flask, frontend con HTML/CSS/JS

## 🧱 Tecnologías utilizadas

- Python 3.10
- Flask (microframework web)
- Paramiko (SSH en Python)
- SQLite (base de datos embebida)
- HTML5, CSS3, JavaScript
- VirtualBox (para pruebas en entorno virtualizado)

## 📦 Estructura del proyecto

/app.py          # Servidor Flask

/static/

└── script.js    # Lógica del frontend

└── style.css    # Estilos personalizados

/templates/

└── index.html    # Página principal

└── server.html   # Vista individual de servidor

## 🚀 Instalación y ejecución (modo local)

1. Clona el repositorio:
   
git clone https://github.com/tuusuario/tu-repo.git

cd tu-repo
   
4. Instala las dependencias:

pip install -r requirements.txt

6. Ejecuta la app:

python app.py

📚 Más información
Este proyecto forma parte de un Trabajo Fin de Ciclo (ASIR), enfocado en soluciones eficientes para la administración de infraestructuras pequeñas.
