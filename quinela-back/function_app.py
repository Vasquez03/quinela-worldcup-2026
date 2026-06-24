import azure.functions as func
import json
import pandas as pd
import io
import requests
import sys



app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)


@app.route(route="obtenerPosiciones")
def obtenerPosiciones(req: func.HttpRequest) -> func.HttpResponse:
    SHEET_ID = "1PMOGPxPeZEL1ug5V7sHdeTIdtS32FZF3PKmEyIUMZLk"
    url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

    try:

        response = requests.get(url)
        response.raise_for_status()
        response.encoding = 'utf-8'

        df = pd.read_csv(io.StringIO(response.text), skiprows=1)
        df.columns = df.columns.str.strip()

        todas_jornadas = [col for col in df.columns if 'Día' in col]
        # Identificamos cuáles jornadas tienen datos reales digitados

        jornadas_activas = []

        for col in todas_jornadas:
            primer_valor = df[col].iloc[0]
            if pd.notnull(primer_valor) and str(primer_valor).strip() != "":
                jornadas_activas.append(col)
            else:
                break

        participantes_lista = []

        for index, row in df.iterrows():
            if pd.isnull(row['Nombre']) or str(row['Nombre']).strip() == "":
                continue
               
            historial_puntos = []

            # Como tus datos en la hoja ya vienen acumulados, los metemos directo al historial

            for col in jornadas_activas:
                val = row[col]
                try:
                    puntos_acumulados_fecha = float(val) if pd.notnull(val) and str(val).strip() != "" else 0.0
                except ValueError:
                    puntos_acumulados_fecha = 0.0
                historial_puntos.append(puntos_acumulados_fecha)
        
            # El total actual es el último dato del historial
            puntos_totales_actuales = historial_puntos[-1] if len(historial_puntos) > 0 else 0.0
           
            # Calculamos cuántos puntos hizo SOLO en la última jornada (Última menos Penúltima)

            if len(historial_puntos) >= 2:
                puntos_hoy = historial_puntos[-1] - historial_puntos[-2]
            elif len(historial_puntos) == 1:
                puntos_hoy = historial_puntos[0]
            else:
                puntos_hoy = 0.0
           
            participantes_lista.append({

                "nombre": str(row['Nombre']).strip(),
                "puntos_totales": puntos_totales_actuales,
                "puntos_hoy": puntos_hoy,
                "historial": historial_puntos

            })

        # Lógica de KPIs de la jornada actual

        max_hoy = -999.0
        min_hoy = 999.0
        nombre_max = "N/A"
        nombre_min = "N/A"
       
        for p in participantes_lista:
            puntos_hoy = p["puntos_hoy"]
            if puntos_hoy > max_hoy:
                max_hoy = puntos_hoy
                nombre_max = p["nombre"]
            if puntos_hoy < min_hoy:
                min_hoy = puntos_hoy
                nombre_min = p["nombre"]

        # Ordenamos la tabla de mayor a menor según el acumulado real de la hoja

        tabla_ordenada = sorted(participantes_lista, key=lambda x: x['puntos_totales'], reverse=True)
      
        for pos, p in enumerate(tabla_ordenada):
            p["posicion_actual"] = pos + 1
            del p["puntos_hoy"] # Limpiamos campo auxiliar

        resultado_final = {
            "status": "success",
            "jornada_actual": len(jornadas_activas),
            "kpis": {
                "mas_puntos_jornada": nombre_max,
                "puntos_max_jornada": max_hoy,
                "menos_puntos_jornada": nombre_min,
                "puntos_min_jornada": min_hoy
            },
            "tabla": tabla_ordenada

        }
       
        return func.HttpResponse(
            json.dumps(resultado_final, ensure_ascii=False),
            mimetype="application/json",
            status_code=200,
            headers={"Access-Control-Allow-Origin": "*"}
        )
      
    except Exception as e:

        return func.HttpResponse(
            json.dumps({"status": "error", "message": str(e)}),
            mimetype="application/json",
            status_code=500,
            headers={"Access-Control-Allow-Origin": "*"}
        )

