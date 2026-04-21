# -*- coding: utf-8 -*-
"""
Módulo Generador de Datos de Observabilidad.

Este módulo contiene la lógica principal para generar datos sintéticos de métricas,
logs y trazas (interacciones de tráfico), simulando el comportamiento de un 
sistema real basado en los Golden Signals de SRE y un mapa de servicios.
"""

import pandas as pd
import numpy as np
import uuid
from datetime import datetime, timedelta
import config_data

class ObservabilityGenerator:
    """
    Generador de datos de observabilidad optimizado para alto rendimiento.
    """
    def __init__(self):
        """
        Inicializa el generador cargando y procesando los datos semilla de configuración.
        """
        self.instancias_map = {
            inst[0]: {'contrato_id': inst[1], 'estado': inst[2], 'nombre_servicio': inst[3], 'fqdn': inst[4]}
            for inst in config_data.instancias_servicios
        }
        self.rutas_trafico_seed = config_data.rutas_trafico_seed
        
        self.instances = [
            inst_id for inst_id, data in self.instancias_map.items() if data['estado'] == 'running'
        ]
        self.num_instances = len(self.instances)

        self.protocolos_latencia = {
            "HTTP": (20, 100),
            "HTTPS": (30, 120),
            "TCP": (5, 20),
            "RPC": (10, 40),
            "GRPC": (15, 50),
        }

    def generate_traffic_interactions(self) -> pd.DataFrame:
        """
        Genera un DataFrame de interacciones de tráfico basado en las rutas semilla,
        introduciendo datos sucios aleatoriamente.
        """
        traffic_data = []
        now = datetime.now()

        for origen_id, destino_id, protocolo in self.rutas_trafico_seed:
            if self.instancias_map.get(origen_id, {}).get('estado') != 'running':
                continue

            num_calls = np.random.randint(10, 51)
            latencia_base = self.protocolos_latencia.get(protocolo.upper(), (10, 20))
            nombre_servicio_origen = self.instancias_map[origen_id]['nombre_servicio']

            for _ in range(num_calls):
                timestamp = now - timedelta(seconds=np.random.randint(0, 60))
                
                # Variabilidad en latencia y bytes
                latencia_ms = int(np.random.normal(latencia_base[0], latencia_base[1]))
                latencia_ms = max(1, latencia_ms) # Evitar negativos
                bytes_sent = int(np.random.exponential(500))
                bytes_recv = int(np.random.exponential(1500))
                
                # Introducir error en un 2% de las llamadas
                status_code = 200
                if np.random.random() < 0.02:
                    status_code = np.random.choice([500, 503, 404, 408])
                
                traffic_data.append({
                    "timestamp": timestamp,
                    "origen_id": origen_id,
                    "destino_id": destino_id,
                    "nombre_servicio": nombre_servicio_origen, # Agregado para consistencia
                    "protocolo": protocolo,
                    "latencia_ms": latencia_ms,
                    "bytes_sent": bytes_sent,
                    "bytes_recv": bytes_recv,
                    "status_code": status_code
                })
        
        return pd.DataFrame(traffic_data)

    def generate_batch(self, start_date: str, end_date: str, frequency_seconds: int = 600):
        """
        Genera un lote histórico de datos entre dos fechas.
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1) # Incluir el día final completo
        
        current_dt = start_dt
        
        # Listas para acumular DataFrames (más eficiente que concat en bucle)
        all_metrics = []
        all_logs = []
        
        print(f"Generando datos desde {start_date} hasta {end_date}...")

        while current_dt < end_dt:
            # Aquí llamamos a una versión modificada de generate_realtime_batch que acepte timestamp manual
            # Para simplificar, reutilizamos la lógica pero pasando el timestamp
            batch_metrics, batch_logs, _ = self._generate_snapshot(current_dt)
            all_metrics.append(batch_metrics)
            all_logs.append(batch_logs)
            
            current_dt += timedelta(seconds=frequency_seconds)
        
        metrics_df = pd.concat(all_metrics, ignore_index=True)
        logs_df = pd.concat(all_logs, ignore_index=True)
        traffic_df = self.generate_traffic_interactions() # Tráfico se genera aparte por ahora
        return metrics_df, logs_df, traffic_df

    def _generate_snapshot(self, timestamp: datetime):
        """
        Genera un snapshot de métricas y logs para un timestamp específico.
        Similar a generate_realtime_batch pero acepta timestamp.
        """
        total_rows = self.num_instances
        timestamps = [timestamp] * total_rows
        # Usamos self.instances directamente para evitar la suciedad del paso anterior si hubiera
        instance_ids = self.instances.copy() 

        throughput_rpm = np.random.randint(500, 5001, size=total_rows)
        error_rate_percent = np.random.uniform(0.0, 0.05, size=total_rows).round(4)
        latency_p95_ms = np.random.randint(50, 181, size=total_rows)
        high_throughput_mask = throughput_rpm > 4000
        latency_p95_ms = np.where(high_throughput_mask, np.random.randint(150, 201, size=total_rows), latency_p95_ms)
        cpu_percent_clean = np.random.uniform(15.0, 45.0, size=total_rows)

        memory_usage_percent = np.random.uniform(30.0, 70.0, size=total_rows)
        high_cpu_mask_mem = cpu_percent_clean > 80
        memory_usage_percent[high_cpu_mask_mem] += np.random.uniform(10.0, 20.0, size=np.sum(high_cpu_mask_mem))
        
        # --- DATOS SUCIOS MEMORIA ---
        num_mem_to_dirty = int(total_rows * 0.05)
        indices_mem_to_dirty = np.random.choice(total_rows, num_mem_to_dirty, replace=False)
        memory_usage_percent[indices_mem_to_dirty] = np.random.choice([-10.0, 105.0], size=num_mem_to_dirty)

        service_names = np.array([self.instancias_map[inst_id]['nombre_servicio'] for inst_id in instance_ids])
        is_db_service = (
            np.core.defchararray.find(service_names, 'DB')!=-1) | \
            (np.core.defchararray.find(service_names, 'Data-Lake')!=-1) | \
            (np.core.defchararray.find(service_names, 'Storage')!=-1
        )
        disk_io_wait_ms = np.zeros(total_rows, dtype=int)
        disk_io_wait_ms[is_db_service] = np.random.randint(10, 51, size=np.sum(is_db_service))
        disk_io_wait_ms[~is_db_service] = np.random.randint(0, 11, size=np.sum(~is_db_service))

        active_connections_count = (throughput_rpm / 10 + np.random.randint(-20, 21, size=total_rows))
        active_connections_count = np.maximum(0, active_connections_count).astype(float)
        
        # --- DATO SUCIO CONEXIONES (NaN) ---
        num_conn_to_nan = int(total_rows * 0.05)
        indices_conn_to_nan = np.random.choice(total_rows, num_conn_to_nan, replace=False)
        active_connections_count[indices_conn_to_nan] = np.nan

        cpu_percent = cpu_percent_clean.round(2).astype(object)
        
        # --- DATO SUCIO CPU (String con coma) ---
        num_cpu_to_change = int(total_rows * 0.25)
        indices_cpu_to_change = np.random.choice(total_rows, num_cpu_to_change, replace=False)
        for i in indices_cpu_to_change:
            cpu_percent[i] = str(cpu_percent[i]).replace('.', ',')

        # --- DATO SUCIO INSTANCIA ID (Espacios) ---
        # Primero guardamos los nombres de servicio LIMPIOS basados en los IDs limpios
        service_names_clean = [self.instancias_map.get(str(i).strip(), {}).get('nombre_servicio', 'Unknown') for i in self.instances]

        # Ahora ensuciamos los IDs
        instance_ids = np.array(instance_ids, dtype=object)
        num_id_to_change = int(total_rows * 0.20)
        indices_id_to_change = np.random.choice(total_rows, num_id_to_change, replace=False)
        for i in indices_id_to_change:
            instance_ids[i] = f" {instance_ids[i]} "

        metrics_df = pd.DataFrame({
            'timestamp': timestamps,
            'instancia_id': instance_ids,
            'nombre_servicio': service_names_clean, # Nueva columna agregada
            'throughput_rpm': throughput_rpm,
            'error_rate_percent': error_rate_percent,
            'latency_p95_ms': latency_p95_ms,
            'cpu_percent': cpu_percent,
            'memory_usage_percent': memory_usage_percent.round(2),
            'disk_io_wait_ms': disk_io_wait_ms,
            'active_connections_count': active_connections_count,
        })
        
        # Logs Generation logic (Simplified for snapshot)
        logs_data = [] 
        # ... (Log generation logic could be improved/restored if needed, maintaining simplest form for now)
        # Re-using the logic from original generate_realtime_batch for logs would be ideal but keeping it concise here.
        # Let's restore basic log generation for high latency events
        anomalous_events = metrics_df[pd.to_numeric(metrics_df['latency_p95_ms'], errors='coerce').fillna(0) > 180]
        if not anomalous_events.empty:
            sample_events = anomalous_events.sample(frac=0.3, random_state=1)
            for _, row in sample_events.iterrows():
                logs_data.append({
                    'timestamp': row['timestamp'],
                    'instancia_id': row['instancia_id'],
                    'nombre_servicio': row['nombre_servicio'], # Agregado tambien a logs
                    'log_level': 'ERROR',
                    'message': f"High latency detected: {row['latency_p95_ms']}ms",
                    'module': 'api.handler'
                })
        
        logs_df = pd.DataFrame(logs_data)
        return metrics_df, logs_df, None


    def generate_realtime_batch(self, frequency_seconds: int = 30):
        """
        Genera un lote de datos en tiempo real.
        """
        return self._generate_snapshot(datetime.now().replace(microsecond=0))