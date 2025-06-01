from flask import Flask, render_template, request, jsonify
import paramiko
import sqlite3
import logging
import re

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ---------------- SSH ---------------- #
def conectar_ssh(nombre_host, nombre_usuario, contraseña):
    logging.debug(f"Conectando a {nombre_host} como {nombre_usuario}")
    cliente = paramiko.SSHClient()
    cliente.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    cliente.connect(nombre_host, username=nombre_usuario, password=contraseña)
    return cliente

# ---------------- RUTAS ---------------- #
@app.route('/')
def indice():
    conn = sqlite3.connect('database.db')
    servidores = conn.execute("SELECT * FROM servers").fetchall()
    conn.close()
    return render_template('index.html', servidores=servidores)

@app.route('/servidor/<int:id_servidor>')
def detalle_servidor(id_servidor):
    return render_template('server.html', id_servidor=id_servidor)

# ---------------- API MÉTRICAS ---------------- #
@app.route('/api/servidor/<int:id_servidor>/metricas')
def obtener_métricas_servidor(id_servidor):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])

        comandos = {
            'ram': "free -m | awk '/Mem/{printf \"%.2f\", ($3/$2)*100}'",
            'cpu': "mpstat 1 1 | awk '/Average:/ && $2 ~ /all/ {print 100 - $NF}'",
            'disco': "df -BG / | awk 'NR==2 {gsub(\"G\", \"\", $2); total=$2; gsub(\"G\", \"\", $3); usado=$3; print usado\"/\"total\" GB\"}'"
        }

        resultado = {}
        for clave, cmd in comandos.items():
            stdin, stdout, stderr = ssh.exec_command(cmd)
            resultado[clave] = stdout.read().decode().strip()

        return jsonify(resultado)

    except Exception as e:
        logging.exception("Error obteniendo métricas")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()
            logging.info("Conexión SSH cerrada")

# ---------------- Añadir servidor ---------------- #
@app.route('/api/servidor', methods=['POST'])
def añadir_servidor():
    datos = request.json
    nombre = datos.get('nombre')
    host = datos.get('host')
    usuario = datos.get('usuario')
    contraseña = datos.get('contraseña')

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO servers (name, host, user, password) VALUES (?, ?, ?, ?)", (nombre, host, usuario, contraseña))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ---------------- Eliminar Servidor ---------------- #
@app.route('/api/servidor/<int:id_servidor>', methods=['DELETE'])
def eliminar_servidor(id_servidor):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DELETE FROM servers WHERE id = ?", (id_servidor,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# ---------------- Obtener Usuarios y Grupos ---------------- #
@app.route('/api/servidor/<int:id_servidor>/usuarios_grupos')
def obtener_usuarios_y_grupos(id_servidor):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])

        # Lista de usuarios
        stdin, stdout, stderr = ssh.exec_command("getent passwd | cut -d: -f1")
        usuarios = stdout.read().decode().strip().splitlines()

        # Grupos con usuarios
        stdin, stdout, stderr = ssh.exec_command("getent group | awk -F: '{print $1\":\"$4}'")
        lineas_grupos = stdout.read().decode().strip().splitlines()

        grupos = {}
        for linea in lineas_grupos:
            if ':' in linea:
                nombre, miembros = linea.split(':')
                grupos[nombre] = miembros.split(',') if miembros else []

        return jsonify({
            "usuarios": usuarios,
            "grupos": grupos
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ---------------- Crear Usuario ---------------- #
@app.route('/api/servidor/<int:id_servidor>/usuario', methods=['POST'])
def gestionar_usuario(id_servidor):
    datos = request.json
    nombre_usuario = datos.get('nombre_usuario')
    contraseña = datos.get('contraseña')

    if not re.match("^[a-zA-Z0-9_-]+$", nombre_usuario):
        return jsonify({"success": False, "error": "Nombre inválido"}), 400
    if len(contraseña) < 8:
        return jsonify({"success": False, "error": "Contraseña muy corta"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])
        escapado = nombre_usuario.replace("'", "'\\''")
        comando = f"sudo /usr/sbin/useradd '{escapado}' && echo '{escapado}:{contraseña}' | sudo /usr/sbin/chpasswd"
        stdin, stdout, stderr = ssh.exec_command(comando)
        error = stderr.read().decode()

        if error:
            return jsonify({"success": False, "error": error}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ---------------- Crear Grupo ---------------- #
@app.route('/api/servidor/<int:id_servidor>/grupo', methods=['POST'])
def gestionar_grupo(id_servidor):
    datos = request.json
    nombre_grupo = datos.get('nombre_grupo')

    if not re.match("^[a-zA-Z0-9_-]+$", nombre_grupo):
        return jsonify({"success": False, "error": "Nombre inválido"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])
        escapado = nombre_grupo.replace("'", "'\\''")
        comando = f"sudo /usr/sbin/groupadd '{escapado}'"
        stdin, stdout, stderr = ssh.exec_command(comando)
        error = stderr.read().decode()

        if error:
            return jsonify({"success": False, "error": error}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ---------------- Agregar Usuario a Grupo ---------------- #
@app.route('/api/servidor/<int:id_servidor>/usuario/grupo', methods=['POST'])
def agregar_usuario_a_grupo(id_servidor):
    datos = request.json
    nombre_usuario = datos.get('nombre_usuario')
    nombre_grupo = datos.get('nombre_grupo')

    if not re.match("^[a-zA-Z0-9_-]+$", nombre_usuario) or not re.match("^[a-zA-Z0-9_-]+$", nombre_grupo):
        return jsonify({"success": False, "error": "Nombre inválido"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])
        escapado_usuario = nombre_usuario.replace("'", "'\\''")
        escapado_grupo = nombre_grupo.replace("'", "'\\''")
        comando = f"sudo /usr/sbin/usermod -aG '{escapado_grupo}' '{escapado_usuario}'"
        stdin, stdout, stderr = ssh.exec_command(comando)
        error = stderr.read().decode()

        if error:
            return jsonify({"success": False, "error": error}), 400
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ---------------- Ver Procesos ---------------- #
@app.route('/api/servidor/<int:id_servidor>/procesos/<string:tipo>')
def obtener_procesos_top(id_servidor, tipo):
    try:
        if tipo not in ['ram', 'cpu']:
            return jsonify({"error": "Tipo inválido"}), 400

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])

        comando = {
            'ram': "ps -eo pid,comm,%mem --sort=-%mem | head -n 11",
            'cpu': "ps -eo pid,comm,%cpu --sort=-%cpu | head -n 11"
        }[tipo]

        stdin, stdout, stderr = ssh.exec_command(comando)
        salida = stdout.read().decode().strip().split('\n')[1:]  # Saltar encabezado
        procesos = []

        for linea in salida:
            partes = linea.strip().split(None, 2)
            if len(partes) == 3:
                pid, nombre, uso = partes
                procesos.append({
                    "pid": pid,
                    "nombre": nombre,
                    "uso": uso
                })

        return jsonify({"procesos": procesos})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ------------------------- Acciones Server -----------------------------#
@app.route('/api/servidor/<int:id_servidor>/accion', methods=['POST'])
def accion_servidor(id_servidor):
    datos = request.json
    accion = datos.get('accion')

    acciones = {
        'apagar': "sudo shutdown now",
        'reiniciar': "sudo reboot",
        'actualizar': "sudo apt update -y",
        'mejorar': "sudo apt upgrade -y"
    }

    if accion not in acciones:
        return jsonify({"success": False, "error": "accion inválida"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])

        comando = acciones[accion]
        ssh.exec_command(comando)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()


# ---------------- Programas ---------------- #
programas_info = {
    "apache2": {
        "nombre": "Apache",
        "descripcion": "Servidor web",
        "imagen": "/static/img/apache.png" 
    },
    "ufw": {
        "nombre": "UFW",
        "descripcion": "Firewall sencillo",
        "imagen": "/static/img/ufw.png"  
    },
    "fail2ban": {
        "nombre": "Fail2Ban",
        "descripcion": "Protección contra ataques",
        "imagen": "/static/img/fail2ban.png"
    },
    "htop": {
        "nombre": "htop",
        "descripcion": "Monitor de procesos",
        "imagen": "/static/img/htop.png"
    },
    "curl": {
        "nombre": "curl",
        "descripcion": "Cliente HTTP",
        "imagen": "/static/img/curl.png"
    },
    "vim": {
        "nombre": "Vim",
        "descripcion": "Editor de texto",
        "imagen": "/static/img/vim.png"
    },
    "git": {
        "nombre": "Git",
        "descripcion": "Control de versiones",
        "imagen": "/static/img/git.png"
    },
    "unattended-upgrades": {
        "nombre": "Actualizaciones Automáticas",
        "descripcion": "Actualizaciones automáticas",
        "imagen": "/static/img/unattended.png"
    },
    "net-tools": {
        "nombre": "Net-Tools",
        "descripcion": "Herramientas de red",
        "imagen": "/static/img/nettools.png"
    },
    "lsof": {
        "nombre": "lsof",
        "descripcion": "Lista archivos abiertos",
        "imagen": "/static/img/lsof.png"
    },
    "rsync": {
        "nombre": "rsync",
        "descripcion": "Sincronizar archivos",
        "imagen": "/static/img/rsync.png"
    },
    "tmux": {
        "nombre": "tmux",
        "descripcion": "Multiplexor de terminal",
        "imagen": "/static/img/tmux.png"
    },
    "sudo": {
        "nombre": "sudo",
        "descripcion": "Permisos de administrador",
        "imagen": "/static/img/sudo.png"
    },
    "logrotate": {
        "nombre": "logrotate",
        "descripcion": "Rotación de logs",
        "imagen": "/static/img/logrotate.png"
    }
}

# ------------------------------- Programas Servidor ----------------------------------- #
@app.route('/api/servidor/<int:id_servidor>/programas', methods=['GET', 'POST', 'DELETE'])
def programas_servidor(id_servidor):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (id_servidor,))
        servidor = c.fetchone()
        conn.close()

        if not servidor:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = conectar_ssh(servidor[2], servidor[3], servidor[4])

        if request.method == 'GET':
            resultado = []
            for paquete, info in programas_info.items():
                stdin, stdout, stderr = ssh.exec_command(f"dpkg -s {paquete} 2>/dev/null | grep Status")
                estado = stdout.read().decode()

                instalado = "install ok installed" in estado
                activo = None
                if instalado and paquete in ["apache2", "ufw", "fail2ban", "ssh", "unattended-upgrades"]:
                    stdin, stdout, stderr = ssh.exec_command(f"systemctl is-active {paquete}")
                    activo = stdout.read().decode().strip() == "active"

                resultado.append({
                    "paquete": paquete,
                    "nombre": info["nombre"],
                    "descripcion": info["descripcion"],
                    "imagen": info["imagen"],
                    "instalado": instalado,
                    "activo": activo
                })

            return jsonify(resultado)

        elif request.method == 'POST':
            datos = request.json
            programa = datos.get('programa')
            if not programa or programa not in programas_info:
                return jsonify({"success": False, "error": "Programa inválido"})

            stdin, stdout, stderr = ssh.exec_command(f"sudo apt update -y && sudo apt install {programa} -y")
            stdout.channel.recv_exit_status()
            return jsonify({"success": True})
        
        elif request.method == 'DELETE':
            datos = request.json
            programa = datos.get('programa')
            if not programa or programa not in programas_info:
                return jsonify({"success": False, "error": "Programa inválido"})

            stdin, stdout, stderr = ssh.exec_command(f"sudo apt remove --purge {programa} -y")
            print("STDOUT:", stdout.read().decode())
            print("STDERR:", stderr.read().decode())
            stdout.channel.recv_exit_status()
            return jsonify({"success": True})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ---------------- MAIN ---------------- #
if __name__ == '__main__':
    app.run(debug=True)



