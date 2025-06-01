console.log("script.js cargado");

document.addEventListener("DOMContentLoaded", () => {

    // --- SI ESTÁS EN PÁGINA DE SERVIDOR ---
    if (typeof idServidor !== 'undefined') {
        cargarUsuariosGrupos();
        obtenerMetricas();
        setInterval(obtenerMetricas, 10000);
        cargarProgramas();

        // Crear usuario
        document.getElementById("formUsuario").addEventListener("submit", function (e) {
            e.preventDefault();
            const nombreUsuario = document.getElementById("usuario").value;
            const clave = document.getElementById("clave").value;

            fetch(`/api/servidor/${idServidor}/usuario`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nombre_usuario: nombreUsuario, contraseña: clave })
            })
            .then(res => res.json())
            .then(data => {
                mostrarMensaje("msgUsuario", data.success ? "¡Usuario creado!" : data.error, data.success);
                if (data.success) {
                    cargarUsuariosGrupos();
                    e.target.reset();
                }
            });
        });

        // Crear grupo
        document.getElementById("formGrupo").addEventListener("submit", function (e) {
            e.preventDefault();
            const nombreGrupo = document.getElementById("grupo").value;

            fetch(`/api/servidor/${idServidor}/grupo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nombre_grupo: nombreGrupo })
            })
            .then(res => res.json())
            .then(data => {
                mostrarMensaje("msgGrupo", data.success ? "¡Grupo creado!" : data.error, data.success);
                if (data.success) {
                    cargarUsuariosGrupos();
                    e.target.reset();
                }
            });
        });

        // Añadir usuario a grupo
        document.getElementById("formUsuGrupo").addEventListener("submit", function (e) {
            e.preventDefault();
            const nombreUsuario = document.getElementById("usuarioGrupo").value;
            const nombreGrupo = document.getElementById("grupoUsu").value;

            fetch(`/api/servidor/${idServidor}/usuario_grupo`, {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nombre_usuario: nombreUsuario, nombre_grupo: nombreGrupo })
            })
            .then(res => res.json())
            .then(data => {
                mostrarMensaje("msgUsuGrupo", data.success ? "¡Usuario añadido al grupo!" : data.error, data.success);
                if (data.success) {
                    cargarUsuariosGrupos();
                    e.target.reset();
                }
            });
        });
    }

    // --- SI ESTÁS EN index.html ---
    const formServidor = document.getElementById("formServidor");
    if (formServidor) {
        formServidor.addEventListener("submit", function (e) {
            e.preventDefault();
            const nombre = document.getElementById("nombre").value;
            const host = document.getElementById("host").value;
            const nombreUsuario = document.getElementById("usuario").value;
            const clave = document.getElementById("clave").value;

            fetch("/api/servidor", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ nombre: nombre, host: host, usuario: nombreUsuario, contraseña: clave })
            })
            .then(res => res.json())
            .then(data => {
                const msg = document.getElementById("msgServidor");
                msg.textContent = data.success ? "Servidor añadido correctamente" : "Error: " + data.error;
                msg.className = "message " + (data.success ? "success" : "error");
                if (data.success) {
                    setTimeout(() => location.reload(), 1000);
                }
            });
        });
    }
});

// --- MÉTRICAS DE SERVIDOR ---
function obtenerMetricas() {
    fetch(`/api/servidor/${idServidor}/metricas`)
        .then(res => res.json())
        .then(data => {
            if (data.error) {
                console.error("Error al obtener métricas:", data.error);
                document.getElementById('uso-ram').textContent = "Error";
                document.getElementById('uso-cpu').textContent = "Error";
                document.getElementById('uso-disco').textContent = "Error";
            } else {
                document.getElementById('uso-ram').textContent = data.ram + "%";
                document.getElementById('uso-cpu').textContent = data.cpu + "%";
                document.getElementById('uso-disco').textContent = data.disco;
            }
        })
        .catch(err => console.error("Error de red:", err));
}

// --- CARGAR USUARIOS Y GRUPOS ---
function cargarUsuariosGrupos() {
    fetch(`/api/servidor/${idServidor}/usuarios_grupos`)
        .then(res => res.json())
        .then(data => {
            if (data.error) return;

            const listaUsuarios = document.getElementById("lista-usuarios");
            const listaGrupos = document.getElementById("lista-grupos");
            listaUsuarios.innerHTML = "";
            listaGrupos.innerHTML = "";

            data.usuarios.forEach(u => {
                const li = document.createElement("li");
                li.textContent = u;
                listaUsuarios.appendChild(li);
            });

            for (const g in data.grupos) {
                const li = document.createElement("li");
                const ul = document.createElement("ul");
                ul.style.marginLeft = "10px";

                data.grupos[g].forEach(miembro => {
                    const mi = document.createElement("li");
                    mi.textContent = miembro;
                    ul.appendChild(mi);
                });

                li.innerHTML = `<strong>${g}</strong>`;
                li.appendChild(ul);
                listaGrupos.appendChild(li);
            }
        });
}

// --- MOSTRAR MENSAJES ---
function mostrarMensaje(id, texto, exito = true, tiempo = 4000) {
    const div = document.getElementById(id);
    div.textContent = texto;
    div.style.color = exito ? 'green' : 'red';
    setTimeout(() => { div.textContent = ""; }, tiempo);
}

// --- TOGGLE DE LISTAS ---
function alternarLista(id, btn) {
    const lista = document.getElementById(id);
    const visible = lista.style.display !== 'none';
    lista.style.display = visible ? 'none' : 'block';
    btn.innerHTML = (id === 'lista-usuarios' ? '👤 Usuarios ' : '👥 Grupos ') + (visible ? '▶' : '▼');
}

// --- ELIMINAR SERVIDOR ---
function eliminarServidor(id) {
    if (!confirm("¿Seguro que deseas eliminar este servidor?")) return;

    fetch(`/api/servidor/${id}`, {
        method: "DELETE"
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            document.getElementById(`srv-${id}`).remove();
        } else {
            alert("Error al eliminar servidor: " + data.error);
        }
    })
    .catch(err => {
        console.error("Error:", err);
        alert("Error de red al eliminar servidor.");
    });
}

// --- PROCESOS TOP ---
function mostrarTop(tipo) {
    fetch(`/api/servidor/${idServidor}/procesos/${tipo}`)
        .then(res => res.json())
        .then(data => {
            if (data.error) return alert("Error: " + data.error);

            const tbody = document.getElementById("tabla-procesos");
            tbody.innerHTML = "";

            data.procesos.forEach(p => {
                const fila = document.createElement("tr");
                fila.innerHTML = `<td>${p.pid}</td><td>${p.nombre}</td><td>${p.uso}</td>`;
                tbody.appendChild(fila);
            });

            document.getElementById("titulo-modal").textContent =
                tipo === "ram" ? "Procesos por uso de RAM" : "Procesos por uso de CPU";
            document.getElementById("modal-procesos").style.display = "block";
        });
}

function cerrarModal() {
    document.getElementById("modal-procesos").style.display = "none";
}

// --- ACCIONES (apagar, reiniciar, actualizar) ---
function ejecutarAccion(accion) {
    if (!confirm(`¿Seguro que deseas ejecutar "${accion}" en el servidor?`)) return;

    fetch(`/api/servidor/${idServidor}/accion`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ accion })
    })
    .then(res => res.json())
    .then(data => {
        mostrarMensaje("msgAccion", data.success ? "¡Acción ejecutada!" : data.error, data.success);
    })
    .catch(err => {
        console.error("Error de red:", err);
        mostrarMensaje("msgAccion", "Error de red", false);
    });
}

// --- CARGAR PROGRAMAS ---
function cargarProgramas() {
    fetch(`/api/servidor/${idServidor}/programas`)
        .then(res => res.json())
        .then(data => {
            const contenedor = document.getElementById("seccion-programas");
            contenedor.innerHTML = "";

            data.forEach(p => {
                const tarjeta = document.createElement("div");
                tarjeta.className = "card-programa";
                tarjeta.innerHTML = `
                    <img src="${p.imagen}" alt="${p.nombre}" class="icono">
                    <h4>${p.nombre}</h4>
                    <p>${p.descripcion}</p>
                    <p><b>${p.instalado ? "Instalado" : "No instalado"}</b></p>
                    <p>Estado: ${p.activo === null ? "-" : (p.activo ? "Activo" : "Inactivo")}</p>
                    <button class="btn ${p.instalado ? 'danger' : 'success'}" onclick="${p.instalado ? `desinstalar('${p.paquete}')` : `instalar('${p.paquete}')`}">
                        ${p.instalado ? 'Desinstalar' : 'Instalar'}
                    </button>
                `;
                contenedor.appendChild(tarjeta);
            });
        });
}

function instalar(paquete) {
    const btn = document.querySelector(`[onclick="instalar('${paquete}')"]`);
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Instalando...';

    fetch(`/api/servidor/${idServidor}/programas`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ programa: paquete })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) alert("Error: " + data.error);
        cargarProgramas();
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = original;
    });
}

function desinstalar(paquete) {
    const btn = document.querySelector(`[onclick="desinstalar('${paquete}')"]`);
    const original = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Desinstalando...';

    fetch(`/api/servidor/${idServidor}/programas`, {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ programa: paquete })
    })
    .then(res => res.json())
    .then(data => {
        if (!data.success) alert("Error: " + data.error);
        cargarProgramas();
    })
    .finally(() => {
        btn.disabled = false;
        btn.innerHTML = original;
    });
}

function abrirModalProgramas() {
    document.getElementById("modal-programas").style.display = "block";
    cargarProgramas();
}

function cerrarModalProgramas() {
    document.getElementById("modal-programas").style.display = "none";
}
