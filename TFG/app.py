from flask import Flask, render_template, request, jsonify
import paramiko
import sqlite3
import logging
import re

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# ---------------- SSH ---------------- #
def ssh_connect(hostname, username, password):
    logging.debug(f"Conectando a {hostname} como {username}")
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname, username=username, password=password)
    return client

# ---------------- RUTAS ---------------- #
@app.route('/')
def index():
    conn = sqlite3.connect('database.db')
    servers = conn.execute("SELECT * FROM servers").fetchall()
    conn.close()
    return render_template('index.html', servers=servers)

@app.route('/server/<int:server_id>')
def server_detail(server_id):
    return render_template('server.html', server_id=server_id)

# ---------------- API MÉTRICAS ---------------- #
@app.route('/api/server/<int:server_id>/metrics')
def get_server_metrics(server_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])

        commands = {
            'ram': "free -m | awk '/Mem/{printf \"%.2f\", ($3/$2)*100}'",
            'cpu': "mpstat 1 1 | awk '/Average:/ && $2 ~ /all/ {print 100 - $NF}'",
            'disk': "df -BG / | awk 'NR==2 {gsub(\"G\", \"\", $2); total=$2; gsub(\"G\", \"\", $3); used=$3; print used\"/\"total\" GB\"}'"

        }

        result = {}
        for key, cmd in commands.items():
            stdin, stdout, stderr = ssh.exec_command(cmd)
            result[key] = stdout.read().decode().strip()

        return jsonify(result)

    except Exception as e:
        logging.exception("Error obteniendo métricas")
        return jsonify({"error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()
            logging.info("Conexión SSH cerrada")

# ---------------- Añadir servidor ---------------- #
@app.route('/api/server', methods=['POST'])
def add_server():
    data = request.json
    name = data.get('name')
    host = data.get('host')
    user = data.get('user')
    password = data.get('password')

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("INSERT INTO servers (name, host, user, password) VALUES (?, ?, ?, ?)", (name, host, user, password))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})
    
# ---------------- Eliminar Servidor ---------------- #
@app.route('/api/server/<int:server_id>', methods=['DELETE'])
def delete_server(server_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("DELETE FROM servers WHERE id = ?", (server_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})


# ---------------- Obtener Usuarios y Grupos ---------------- #
@app.route('/api/server/<int:server_id>/users_groups')
def get_users_and_groups(server_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])

        # Lista de usuarios
        stdin, stdout, stderr = ssh.exec_command("getent passwd | cut -d: -f1")
        users = stdout.read().decode().strip().splitlines()

        # Grupos con usuarios
        stdin, stdout, stderr = ssh.exec_command("getent group | awk -F: '{print $1\":\"$4}'")
        group_lines = stdout.read().decode().strip().splitlines()

        groups = {}
        for line in group_lines:
            if ':' in line:
                name, members = line.split(':')
                groups[name] = members.split(',') if members else []

        return jsonify({
            "users": users,
            "groups": groups
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

# ---------------- Crear Usuario ---------------- #
@app.route('/api/server/<int:server_id>/user', methods=['POST'])
def manage_user(server_id):
    data = request.json
    username = data.get('username')
    password = data.get('password')

    if not re.match("^[a-zA-Z0-9_-]+$", username):
        return jsonify({"success": False, "error": "Nombre inválido"}), 400
    if len(password) < 8:
        return jsonify({"success": False, "error": "Contraseña muy corta"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])
        escaped = username.replace("'", "'\\''")
        command = f"sudo /usr/sbin/useradd '{escaped}' && echo '{escaped}:{password}' | sudo /usr/sbin/chpasswd"
        stdin, stdout, stderr = ssh.exec_command(command)
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
@app.route('/api/server/<int:server_id>/group', methods=['POST'])
def manage_group(server_id):
    data = request.json
    groupname = data.get('groupname')

    if not re.match("^[a-zA-Z0-9_-]+$", groupname):
        return jsonify({"success": False, "error": "Nombre inválido"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])
        escaped = groupname.replace("'", "'\\''")
        command = f"sudo /usr/sbin/groupadd '{escaped}'"
        stdin, stdout, stderr = ssh.exec_command(command)
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
@app.route('/api/server/<int:server_id>/user/group', methods=['POST'])
def add_user_to_group(server_id):
    data = request.json
    username = data.get('username')
    groupname = data.get('groupname')

    if not re.match("^[a-zA-Z0-9_-]+$", username) or not re.match("^[a-zA-Z0-9_-]+$", groupname):
        return jsonify({"success": False, "error": "Nombre inválido"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])
        escaped_user = username.replace("'", "'\\''")
        escaped_group = groupname.replace("'", "'\\''")
        command = f"sudo /usr/sbin/usermod -aG '{escaped_group}' '{escaped_user}'"
        stdin, stdout, stderr = ssh.exec_command(command)
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
@app.route('/api/server/<int:server_id>/top/<string:tipo>')
def get_top_processes(server_id, tipo):
    try:
        if tipo not in ['ram', 'cpu']:
            return jsonify({"error": "Tipo inválido"}), 400

        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])

        comando = {
            'ram': "ps -eo pid,comm,%mem --sort=-%mem | head -n 11",
            'cpu': "ps -eo pid,comm,%cpu --sort=-%cpu | head -n 11"
        }[tipo]

        stdin, stdout, stderr = ssh.exec_command(comando)
        output = stdout.read().decode().strip().split('\n')[1:]  # Saltar encabezado
        procesos = []

        for linea in output:
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
    
@app.route('/api/server/<int:server_id>/action', methods=['POST'])
def server_action(server_id):
    data = request.json
    accion = data.get('accion')

    acciones = {
        'apagar': "sudo shutdown now",
        'reiniciar': "sudo reboot",
        'update': "sudo apt update -y",
        'upgrade': "sudo apt upgrade -y"
    }

    if accion not in acciones:
        return jsonify({"success": False, "error": "Acción inválida"}), 400

    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"success": False, "error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])

        command = acciones[accion]
        ssh.exec_command(command)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if 'ssh' in locals():
            ssh.close()

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
        "nombre": "Auto-Updates",
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

@app.route('/api/server/<int:server_id>/programas', methods=['GET', 'POST', 'DELETE'])
def programas_server(server_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM servers WHERE id = ?", (server_id,))
        server = c.fetchone()
        conn.close()

        if not server:
            return jsonify({"error": "Servidor no encontrado"}), 404

        ssh = ssh_connect(server[2], server[3], server[4])

        if request.method == 'GET':
            resultado = []
            for paquete, info in programas_info.items():
                stdin, stdout, stderr = ssh.exec_command(f"dpkg -s {paquete} 2>/dev/null | grep Status")
                status = stdout.read().decode()

                instalado = "install ok installed" in status
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
            data = request.json
            programa = data.get('programa')
            if not programa or programa not in programas_info:
                return jsonify({"success": False, "error": "Programa inválido"})

            stdin, stdout, stderr = ssh.exec_command(f"sudo apt update -y && sudo apt install {programa} -y")
            stdout.channel.recv_exit_status()
            return jsonify({"success": True})
        
        elif request.method == 'DELETE':
            data = request.json
            programa = data.get('programa')
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


