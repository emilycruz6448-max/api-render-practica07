import os
from flask import Flask, request, jsonify
from datetime import datetime
from functools import wraps
from psycopg.errors import UniqueViolation

# Intentar importar psycopg2
try:
    import psycopg
    from psycopg.rows import dict_row

    USAR_DB = True
    print("PSYCOPG CARGADO CORRECTAMENTE")
except Exception as e:
    print("ERROR PSYCOPG:", e)
    USAR_DB = False

app = Flask(__name__)

# Configuracion desde variables de entorno
DATABASE_URL = os.environ.get("DATABASE_URL", "")
API_KEY = os.environ.get("API_KEY", "clave-practica-07")
APP_ENV = os.environ.get("APP_ENV", "development")

# ============================================
# Funciones de base de datos
# ============================================

def get_db():
    if not USAR_DB:
        return None

    if not DATABASE_URL:
        return None

    try:
        return psycopg.connect(
            DATABASE_URL,
            row_factory=dict_row
        )
    except Exception as e:
        print(f"ERROR DB: {e}")
        return None

def init_db():
    conn = get_db()
    if not conn:
        return

    cur = conn.cursor()
    
    # Tabla de materias
    cur.execute("""
        CREATE TABLE IF NOT EXISTS materias (
            id SERIAL PRIMARY KEY,
            clave VARCHAR(15) NOT NULL UNIQUE,
            nombre VARCHAR(150) NOT NULL,
            semestre INTEGER NOT NULL CHECK (semestre BETWEEN 1 AND 9),
            creditos INTEGER DEFAULT 5,
            tipo VARCHAR(30) DEFAULT 'Obligatoria',
            horas_teoria INTEGER DEFAULT 3,
            horas_practica INTEGER DEFAULT 2,
            competencia VARCHAR(200),
            activa BOOLEAN DEFAULT true,
            fecha_registro TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Tabla de reportes (para el Cron Job)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS reportes (
            id SERIAL PRIMARY KEY,
            tipo VARCHAR(50),
            datos JSONB,
            fecha TIMESTAMP DEFAULT NOW()
        )
    """)
    
    # Insertar datos iniciales si la tabla esta vacia
    cur.execute("SELECT COUNT(*) AS count FROM materias")
    count = cur.fetchone()["count"]
    
    if count == 0:
        materias_iniciales = [
            ('INF-101', 'Fundamentos de Programacion', 1, 6, 'Obligatoria', 3, 3, 'Desarrollo de software'),
            ('INF-102', 'Matematicas Discretas', 1, 5, 'Obligatoria', 4, 1, 'Logica computacional'),
            ('INF-201', 'Estructura de Datos', 2, 6, 'Obligatoria', 3, 3, 'Desarrollo de software'),
            ('INF-202', 'Arquitectura de Computadoras', 2, 5, 'Obligatoria', 4, 1, 'Hardware y redes'),
            ('INF-301', 'Bases de Datos', 3, 6, 'Obligatoria', 3, 3, 'Gestion de datos'),
            ('INF-302', 'Redes de Computadoras', 3, 5, 'Obligatoria', 3, 2, 'Hardware y redes'),
            ('INF-401', 'Ingenieria de Software', 4, 6, 'Obligatoria', 3, 3, 'Desarrollo de software'),
            ('INF-402', 'Sistemas Operativos', 4, 5, 'Obligatoria', 3, 2, 'Infraestructura'),
            ('INF-501', 'Servicios en la Nube', 5, 5, 'Obligatoria', 2, 3, 'Infraestructura'),
            ('INF-502', 'Administracion de Datos', 5, 5, 'Obligatoria', 3, 2, 'Gestion de datos'),
            ('INF-601', 'Inteligencia Artificial', 6, 5, 'Obligatoria', 3, 2, 'IA y datos'),
            ('INF-602', 'Seguridad Informatica', 6, 5, 'Obligatoria', 3, 2, 'Infraestructura'),
            ('INF-701', 'Desarrollo de Apps Moviles', 7, 5, 'Optativa', 2, 3, 'Desarrollo de software'),
            ('INF-702', 'Big Data y Analitica', 7, 5, 'Optativa', 3, 2, 'IA y datos'),
        ]
        
        for m in materias_iniciales:
            cur.execute("""
                INSERT INTO materias (clave, nombre, semestre, creditos, tipo, 
                                     horas_teoria, horas_practica, competencia)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, m)
    
    conn.commit()
    cur.close()
    conn.close()

# ============================================
# Middleware de autenticacion simple
# ============================================

def requiere_api_key(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        key = request.headers.get("X-API-Key", "")
        if key != API_KEY:
            return jsonify({
                "error": "API Key invalida o no proporcionada",
                "instruccion": "Incluye el header X-API-Key con tu clave"
            }), 401
        return f(*args, **kwargs)
    return decorated

# ============================================
# Pagina principal (documentacion interactiva)
# ============================================

@app.route("/")
def index():
    base_url = request.url_root.rstrip("/")
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>API Materias - Practica 07</title>
        <style>
            * {{ box-sizing: border-box; margin: 0; padding: 0; }}
            body {{
                font-family: 'Courier New', monospace;
                background: #0d1117;
                color: #c9d1d9;
                padding: 20px;
            }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            h1 {{ color: #58a6ff; margin: 20px 0; }}
            h2 {{ color: #7ee787; margin: 20px 0 10px; }}
            .endpoint {{
                background: #161b22;
                border: 1px solid #30363d;
                border-radius: 6px;
                padding: 15px;
                margin: 10px 0;
            }}
            .method {{
                display: inline-block;
                padding: 3px 8px;
                border-radius: 4px;
                font-weight: bold;
                font-size: 0.85em;
                margin-right: 8px;
            }}
            .get {{ background: #1f6feb; color: white; }}
            .post {{ background: #238636; color: white; }}
            .put {{ background: #9e6a03; color: white; }}
            .delete {{ background: #da3633; color: white; }}
            code {{
                background: #1f2937;
                padding: 2px 6px;
                border-radius: 3px;
                color: #f0883e;
            }}
            pre {{
                background: #1f2937;
                padding: 12px;
                border-radius: 6px;
                overflow-x: auto;
                margin: 8px 0;
            }}
            .info {{
                background: #0d419d33;
                border-left: 3px solid #58a6ff;
                padding: 12px;
                margin: 15px 0;
                border-radius: 0 6px 6px 0;
            }}
            a {{ color: #58a6ff; }}
            #resultado {{
                background: #1f2937;
                padding: 15px;
                border-radius: 6px;
                margin-top: 10px;
                min-height: 50px;
                white-space: pre-wrap;
                display: none;
            }}
            button {{
                background: #238636;
                color: white;
                border: none;
                padding: 6px 14px;
                border-radius: 4px;
                cursor: pointer;
                margin: 3px;
            }}
            button:hover {{ background: #2ea043; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>API REST: Catalogo de Materias</h1>
            <p>Practica 07 - PaaS Render | Servicios en la Nube | TecNM</p>
            
            <div class="info">
                <strong>Ambiente:</strong> {APP_ENV} | 
                <strong>DB:</strong> {'Conectada' if (USAR_DB and DATABASE_URL) else 'No configurada'} |
                <strong>Base URL:</strong> <code>{base_url}</code>
            </div>
            <h2>Prueba rapida</h2>
            <p>Haz clic para probar los endpoints:</p>
            <button onclick="probar('/api/materias')">GET /api/materias</button>
            <button onclick="probar('/api/materias?semestre=5')">Semestre 5</button>
            <button onclick="probar('/api/estadisticas')">Estadisticas</button>
            <button onclick="probar('/api/status')">Status</button>
            <div id="resultado"></div>
            <h2>Endpoints disponibles</h2>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/materias</code>
                <p>Lista todas las materias. Filtros opcionales: <code>?semestre=5</code>, <code>?tipo=Optativa</code>, <code>?competencia=datos</code></p>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/materias/&lt;id&gt;</code>
                <p>Detalle de una materia especifica por ID</p>
            </div>
            <div class="endpoint">
                <span class="method post">POST</span> <code>/api/materias</code>
                <p>Crear nueva materia (requiere header <code>X-API-Key</code>)</p>
                <pre>Body JSON: {{"clave": "INF-801", "nombre": "IoT", "semestre": 8, "creditos": 5}}</pre>
            </div>
            <div class="endpoint">
                <span class="method put">PUT</span> <code>/api/materias/&lt;id&gt;</code>
                <p>Actualizar materia existente (requiere <code>X-API-Key</code>)</p>
            </div>
            <div class="endpoint">
                <span class="method delete">DELETE</span> <code>/api/materias/&lt;id&gt;</code>
                <p>Desactivar materia (requiere <code>X-API-Key</code>)</p>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/estadisticas</code>
                <p>Resumen: materias por semestre, por tipo, total creditos</p>
            </div>
            <div class="endpoint">
                <span class="method get">GET</span> <code>/api/reportes</code>
                <p>Reportes generados automaticamente por el Cron Job</p>
            </div>
            <h2>Ejemplo con curl</h2>
            <pre>
# Listar materias
curl {base_url}/api/materias
# Filtrar por semestre
curl "{base_url}/api/materias?semestre=5"
# Crear materia (requiere API Key)
curl -X POST {base_url}/api/materias \\
  -H "Content-Type: application/json" \\
  -H "X-API-Key: {API_KEY}" \\
  -d '{{"clave":"INF-801","nombre":"IoT","semestre":8,"creditos":5}}'
            </pre>
            <div class="info">
                <strong>¿Por que API Key?</strong> En aplicaciones reales, no quieres que cualquiera pueda 
                modificar datos. GET es publico (lectura), pero POST/PUT/DELETE requieren autenticacion. 
                La API Key es el metodo mas simple. En produccion usarias OAuth2 o JWT.
            </div>
        </div>
        <script>
            async function probar(endpoint) {{
                const div = document.getElementById('resultado');
                div.style.display = 'block';
                div.textContent = 'Cargando...';
                try {{
                    const res = await fetch(endpoint);
                    const data = await res.json();
                    div.textContent = JSON.stringify(data, null, 2);
                }} catch(e) {{
                    div.textContent = 'Error: ' + e.message;
                }}
            }}
        </script>
    </body>
    </html>
    """

# ============================================
# API REST - Endpoints
# ============================================

@app.route("/api/materias", methods=["GET"])
def listar_materias():
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503
    
    cur = conn.cursor()
    
    # Filtros opcionales
    semestre = request.args.get("semestre")
    tipo = request.args.get("tipo")
    competencia = request.args.get("competencia")
    
    query = "SELECT * FROM materias WHERE activa = true"
    params = []
    
    if semestre:
        try:
            semestre = int(semestre)
        except ValueError:
            return jsonify({
                "error": "El semestre debe ser numerico"
            }), 400

        query += " AND semestre = %s"
        params.append(semestre)

    if tipo:
        query += " AND LOWER(tipo) = LOWER(%s)"
        params.append(tipo)

    if competencia:
        query += " AND LOWER(competencia) LIKE LOWER(%s)"
        params.append(f"%{competencia}%")

    query += " ORDER BY semestre, clave"

    cur.execute(query, params)
    materias = cur.fetchall()

    cur.close()
    conn.close()

    for m in materias:
        if m.get("fecha_registro"):
            m["fecha_registro"] = m["fecha_registro"].isoformat()

    return jsonify({
        "total": len(materias),
        "filtros": {
            "semestre": semestre,
            "tipo": tipo,
            "competencia": competencia
        },
        "materias": materias
    })

@app.route("/api/materias/<int:id>", methods=["GET"])
def obtener_materia(id):
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM materias WHERE id = %s", (id,))
    materia = cur.fetchone()
    cur.close()
    conn.close()
    
    if not materia:
        return jsonify({"error": f"Materia con id {id} no encontrada"}), 404
    
    if materia.get("fecha_registro"):
        materia["fecha_registro"] = materia["fecha_registro"].isoformat()
    
    return jsonify(materia)

@app.route("/api/materias", methods=["POST"])
@requiere_api_key
def crear_materia():
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503

    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON requerido"}), 400

    campos_requeridos = ["clave", "nombre", "semestre"]
    for campo in campos_requeridos:
        if campo not in data:
            return jsonify({
                "error": f"Campo requerido: {campo}"
            }), 400

    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO materias (
                clave,
                nombre,
                semestre,
                creditos,
                tipo,
                horas_teoria,
                horas_practica,
                competencia
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING *
        """, (
            data["clave"],
            data["nombre"],
            data["semestre"],
            data.get("creditos", 5),
            data.get("tipo", "Obligatoria"),
            data.get("horas_teoria", 3),
            data.get("horas_practica", 2),
            data.get("competencia", "")
        ))

        nueva = cur.fetchone()
        conn.commit()

        if nueva.get("fecha_registro"):
            nueva["fecha_registro"] = nueva["fecha_registro"].isoformat()

        return jsonify({
            "mensaje": "Materia creada",
            "materia": nueva
        }), 201

    except UniqueViolation:
        conn.rollback()
        return jsonify({
            "error": f"La clave {data['clave']} ya existe"
        }), 409
    except Exception as e:
        conn.rollback()
        return jsonify({
            "error": str(e)
        }), 500
    finally:
        cur.close()
        conn.close()

@app.route("/api/materias/<int:id>", methods=["PUT"])
@requiere_api_key
def actualizar_materia(id):
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({"error": "Body JSON requerido"}), 400
    
    campos_permitidos = ["nombre", "semestre", "creditos", "tipo", 
                         "horas_teoria", "horas_practica", "competencia"]
    updates = []
    values = []
    
    for campo in campos_permitidos:
        if campo in data:
            updates.append(f"{campo} = %s")
            values.append(data[campo])
    
    if not updates:
        return jsonify({"error": "No se proporcionaron campos para actualizar"}), 400
    
    values.append(id)
    
    cur = conn.cursor()
    cur.execute(f"""
        UPDATE materias SET {', '.join(updates)} 
        WHERE id = %s RETURNING *
    """, values)
    
    actualizada = cur.fetchone()
    conn.commit()
    cur.close()
    conn.close()
    
    if not actualizada:
        return jsonify({"error": f"Materia {id} no encontrada"}), 404
    
    if actualizada.get("fecha_registro"):
        actualizada["fecha_registro"] = actualizada["fecha_registro"].isoformat()
    
    return jsonify({"mensaje": "Materia actualizada", "materia": actualizada})

@app.route("/api/materias/<int:id>", methods=["DELETE"])
@requiere_api_key
def eliminar_materia(id):
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503
    
    cur = conn.cursor()
    cur.execute("UPDATE materias SET activa = false WHERE id = %s AND activa = true", (id,))
    afectadas = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    
    if afectadas == 0:
        return jsonify({"error": f"Materia {id} no encontrada o ya inactiva"}), 404
    
    return jsonify({"mensaje": f"Materia {id} desactivada (soft delete)"})

@app.route("/api/estadisticas", methods=["GET"])
def estadisticas():
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503
    
    cur = conn.cursor()
    
    # Materias por semestre
    cur.execute("""
        SELECT semestre, COUNT(*) as total, SUM(creditos) as total_creditos
        FROM materias WHERE activa = true
        GROUP BY semestre ORDER BY semestre
    """)
    por_semestre = cur.fetchall()
    
    # Materias por tipo
    cur.execute("""
        SELECT tipo, COUNT(*) as total
        FROM materias WHERE activa = true
        GROUP BY tipo
    """)
    por_tipo = cur.fetchall()
    
    # Materias por competencia
    cur.execute("""
        SELECT competencia, COUNT(*) as total
        FROM materias WHERE activa = true AND competencia IS NOT NULL AND competencia != ''
        GROUP BY competencia ORDER BY total DESC
    """)
    por_competencia = cur.fetchall()
    
    # Totales
    cur.execute("""
        SELECT COUNT(*) as total_materias, 
               SUM(creditos) as total_creditos,
               ROUND(AVG(creditos), 1) as promedio_creditos
        FROM materias WHERE activa = true
    """)
    totales = cur.fetchone()
    
    cur.close()
    conn.close()
    
    return jsonify({
        "resumen": totales,
        "por_semestre": por_semestre,
        "por_tipo": por_tipo,
        "por_competencia": por_competencia,
        "generado": datetime.now().isoformat()
    })

@app.route("/api/reportes", methods=["GET"])
def listar_reportes():
    conn = get_db()
    if not conn:
        return jsonify({"error": "Base de datos no disponible"}), 503
    
    cur = conn.cursor()
    cur.execute("SELECT * FROM reportes ORDER BY fecha DESC LIMIT 10")
    reportes = cur.fetchall()
    cur.close()
    conn.close()
    
    for r in reportes:
        if r.get("fecha"):
            r["fecha"] = r["fecha"].isoformat()
    
    return jsonify({"total": len(reportes), "reportes": reportes})

@app.route("/api/status")
def status():
    return jsonify({
        "status": "ok",
        "ambiente": APP_ENV,
        "plataforma": "Render.com",
        "modelo": "PaaS",
        "servicios": {
            "api": "activa",
            "base_datos": "conectada" if (USAR_DB and DATABASE_URL) else "no configurada",
            "cron_job": "configurado"
        },
        "timestamp": datetime.now().isoformat()
    })

# Inicializar DB al arrancar
with app.app_context():
    init_db()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(APP_ENV == "development"))
