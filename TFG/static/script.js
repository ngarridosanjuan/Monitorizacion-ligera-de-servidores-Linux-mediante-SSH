console.log("script.js cargado");

document.addEventListener("DOMContentLoaded", () => {
    // ---------------- Si estamos en la página del servidor ----------------
    if (typeof serverId !== 'undefined') {
        recargaGrupos();
        metricasServer();
        setInterval(metricasServer, 10000);
        cargarProgramas();

        // Crear usuario
        document.getElementById("createUserForm").addEventListener("submit", function (e) {
            e.preventDefault();
            const user = document.getElementById("username").value;
            const password = document.getElementById("password").value;

            fetch(`/api/server/${serverId}/user`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username: user, password })
            })
            .then(res => res.json())
            .then(data => {
                showMessage("managementMessage", data.success ? "Usuario creado!" : data.error, data.success);
                if (data.success) {
                    recargaGrupos();
                    e.target.reset();
                }
            });
        });
        // Crear grupo
        document.getElementById("createGroupForm").addEventListener("submit", function (e) {
            e.preventDefault();
            const groupname = document.getElementById("groupname").value;

            fetch(`/api/server/${serverId}/group`, {
              method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ groupname })
            })
            .then(res => res.json())
            .then(data => {
                showMessage("managementMessageGroups", data.success ? "Grupo creado!" : data.error, data.success);
                if (data.success) {
                    recargaGrupos();
                    e.target.reset();
                }
            });
        });
        // Añadir usuario a grupo 
        document.getElementById("addUserToGroupForm").addEventListener("submit", function (e) {
            e.preventDefault();
            const username = document.getElementById("usernameToGroup").value;
            const groupname = document.getElementById("groupToAdd").value;

            fetch(`/api/server/${serverId}/user/group`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ username, groupname })
            })
            .then(res => res.json())
            .then(data => {
                showMessage("userToGroupMessage", data.success ? "Usuario añadido al grupo!" : data.error, data.success);
                if (data.success) {
                    recargaGrupos();
                    e.target.reset();
                }
            });
        });
    }

    // ---------------- Si estamos en la página index.html ----------------
    const form = document.getElementById("addServerForm");
    if (form) {
        form.addEventListener("submit", function (e) {
            e.preventDefault();

            const name = document.getElementById("name").value;
            const host = document.getElementById("host").value;
            const user = document.getElementById("user").value;
            const password = document.getElementById("password").value;

            fetch("/api/server", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ name, host, user, password })
            })
            .then(res => res.json())
            .then(data => {
                const msg = document.getElementById("serverMessage");
                msg.textContent = data.success ? "Servidor añadido correctamente" : "Error: " + data.error;
                msg.className = "message " + (data.success ? "success" : "error");

                if (data.success) {
                    setTimeout(() => location.reload(), 1000);
                }
            });
        });
    }
});
// Obtener métricas del servidor (RAM, CPU, Disco)
function metricasServer() {
    fetch(`/api/server/${serverId}/metrics`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                console.error("Error al obtener métricas:", data.error);
                document.getElementById('ram-usage').textContent = "Error";
                document.getElementById('cpu-usage').textContent = "Error";
                document.getElementById('disk-usage').textContent = "Error";
            } else {
                document.getElementById('ram-usage').textContent = data.ram + "%";
                document.getElementById('cpu-usage').textContent = data.cpu + "%";
                document.getElementById('disk-usage').textContent = data.disk;
            }
        })
        .catch(error => {
            console.error("Error de red:", error);
        });
}

// Obtener lista de usuarios y grupos
function recargaGrupos() {
    fetch(`/api/server/${serverId}/users_groups`)
        .then(response => response.json())
        .then(data => {
            if (data.error) return;

            // Usuarios
            const userList = document.getElementById('users-list');
            userList.innerHTML = "";
            data.users.forEach(user => {
                const li = document.createElement('li');
                li.textContent = user;
                userList.appendChild(li);
            });

            // Grupos con usuarios
            const groupList = document.getElementById('groups-list');
            groupList.innerHTML = "";
            for (const group in data.groups) {
                const groupItem = document.createElement('li');
                const innerList = document.createElement('ul');
                innerList.style.marginLeft = "10px";

                data.groups[group].forEach(username => {
                    const userLi = document.createElement('li');
                    userLi.textContent = username;
                    innerList.appendChild(userLi);
                });

                groupItem.innerHTML = `<strong>${group}</strong>`;
                groupItem.appendChild(innerList);
                groupList.appendChild(groupItem);
            }
        });
}

// Mostrar mensajes temporales
function showMessage(divId, message, success = true, duration = 4000) {
    const div = document.getElementById(divId);
    div.textContent = message;
    div.style.color = success ? 'green' : 'red';
    setTimeout(() => { div.textContent = ""; }, duration);
}

// Alternar listas desplegables
function toggleList(id, btn) {
    const list = document.getElementById(id);
    const visible = list.style.display !== 'none';
    list.style.display = visible ? 'none' : 'block';
    btn.innerHTML = (id === 'users-list' ? '👤 Usuarios ' : '👥 Grupos ') + (visible ? '▶' : '▼');
}

// Eliminar servidor
function deleteServer(serverId) {
    if (!confirm("¿Estás seguro de que quieres eliminar este servidor?")) return;

    fetch(`/api/server/${serverId}`, {
        method: 'DELETE'
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById(`server-${serverId}`).remove();
        } else {
            alert("Error al eliminar servidor: " + data.error);
        }
    })
    .catch(error => {
        console.error("Error de red:", error);
        alert("Error de red al eliminar servidor.");
    });
}

// Ver Procesos
function mostrarTopProcesos(tipo) {
    fetch(`/api/server/${serverId}/top/${tipo}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) return alert("Error: " + data.error);
            const lista = document.getElementById("topProcesoLista");
            lista.innerHTML = "";

            data.procesos.forEach(proc => {
                const fila = document.createElement("tr");
                fila.innerHTML = `
                    <td>${proc.pid}</td>
                    <td>${proc.nombre}</td>
                    <td>${proc.uso}</td>
                `;
                lista.appendChild(fila);
            });

            document.getElementById("topProcesoTitulo").textContent =
                tipo === "ram" ? "Procesos por uso de RAM" : "Procesos por uso de CPU";
            document.getElementById("topProcesoModal").style.display = "block";
        });
}

function cerrarModalTop() {
    document.getElementById("topProcesoModal").style.display = "none";
}

function realizarAccion(accion) {
    if (!confirm(`¿Seguro que quieres realizar "${accion}" en el servidor?`)) return;

    fetch(`/api/server/${serverId}/action`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion })
    })
    .then(res => res.json())
    .then(data => {
        showMessage("accionMensaje", data.success ? "Acción realizada!" : data.error, data.success);
    })
    .catch(error => {
        console.error("Error de red:", error);
        showMessage("accionMensaje", "Error de red", false);
    });
}

function cargarProgramas() {
    fetch(`/api/server/${serverId}/programas`)
        .then(res => res.json())
        .then(programas => {
            const contenedor = document.getElementById('programas-section');
            contenedor.innerHTML = "";

            programas.forEach(p => {
                const card = document.createElement('div');
                card.style.background = "white";
                card.style.padding = "15px";
                card.style.borderRadius = "10px";
                card.style.boxShadow = "0 2px 5px rgba(0,0,0,0.1)";
                card.style.textAlign = "center";

                card.innerHTML = `
                    <img src="${p.imagen}" alt="${p.nombre}" style="width:50px;height:50px;margin-bottom:10px;">
                    <h4>${p.nombre}</h4>
                    <p style="font-size: 0.9em; color: gray;">${p.descripcion}</p>
                    <p><b>${p.instalado ? "Instalado" : "No instalado"}</b></p>
                    <p>Status: ${p.activo === null ? "-" : (p.activo ? "Activo" : "No activo")}</p>
                    <button class="btn ${p.instalado ? 'danger' : 'success'}" onclick="${p.instalado ? `desinstalarPrograma('${p.paquete}')` : `instalarPrograma('${p.paquete}')`}">
                        ${p.instalado ? 'Desinstalar' : 'Instalar'}
                    </button>
                `;

                contenedor.appendChild(card);
            });
        });
}

// Nueva versión de instalarPrograma y desinstalarPrograma
function instalarPrograma(programa) {
    const boton = document.querySelector(`[onclick="instalarPrograma('${programa}')"]`);
    const textoOriginal = boton.innerHTML;
    boton.disabled = true;
    boton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Instalando...';

    fetch(`/api/server/${serverId}/programas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ programa })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) alert("Error: " + data.error);
        cargarProgramas();
    })
    .finally(() => {
        boton.disabled = false;
        boton.innerHTML = textoOriginal;
    });
}

function desinstalarPrograma(programa) {
    const boton = document.querySelector(`[onclick="desinstalarPrograma('${programa}')"]`);
    const textoOriginal = boton.innerHTML;
    boton.disabled = true;
    boton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Desinstalando...';

    fetch(`/api/server/${serverId}/programas`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ programa })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) alert("Error: " + data.error);
        cargarProgramas();
    })
    .finally(() => {
        boton.disabled = false;
        boton.innerHTML = textoOriginal;
    });
}

function abrirModalProgramas() {
    document.getElementById('programasModal').style.display = 'block';
    cargarProgramas();
}

function cerrarModalProgramas() {
    document.getElementById('programasModal').style.display = 'none';
}
