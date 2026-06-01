import os

import json

import psycopg2

import psycopg2.extras

from datetime import datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")

def generar_reporte():

    """Genera un reporte de estadisticas y lo guarda en la tabla reportes"""

    if not DATABASE_URL:

        print("ERROR: DATABASE_URL no configurada")

        return

    

    conn = psycopg2.connect(DATABASE_URL)

    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    

    # Recopilar estadisticas

    cur.execute("SELECT COUNT(*) as total FROM materias WHERE activa = true")

    total = cur.fetchone()["total"]

    

    cur.execute("""

        SELECT semestre, COUNT(*) as materias, SUM(creditos) as creditos

        FROM materias WHERE activa = true

        GROUP BY semestre ORDER BY semestre

    """)

    por_semestre = cur.fetchall()

    

    cur.execute("""

        SELECT tipo, COUNT(*) as total

        FROM materias WHERE activa = true

        GROUP BY tipo

    """)

    por_tipo = cur.fetchall()

    

    # Construir reporte

    reporte = {

        "total_materias_activas": total,

        "por_semestre": por_semestre,

        "por_tipo": por_tipo,

        "generado_por": "Cron Job automatico",

        "timestamp": datetime.now().isoformat()

    }

    

    # Guardar en tabla reportes

    cur.execute("""

        INSERT INTO reportes (tipo, datos)

        VALUES (%s, %s)

    """, ("estadisticas_automaticas", json.dumps(reporte, default=str)))

    

    conn.commit()

    cur.close()

    conn.close()

    

    print(f"[{datetime.now()}] Reporte generado: {total} materias activas")

    print(json.dumps(reporte, indent=2, default=str))

if __name__ == "__main__":

    generar_reporte()
