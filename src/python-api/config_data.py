# -*- coding: utf-8 -*-
"""
Módulo de Configuración de Datos Semilla.

Este archivo contiene los datos maestros (semillas) que se utilizarán para la generación
de datos sintéticos en el pipeline. Estos datos son estáticos y deterministas para
garantizar la consistencia de la arquitectura de servicios simulada.
"""
from datetime import datetime

# --- CLIENTES BASE (SEMILLA) ---
# Se mantienen los clientes originales
clientes = [
    (1, "Stripe", "fintech", datetime(2022, 1, 15)),
    (2, "Chime", "fintech", datetime(2021, 11, 20)),
    (3, "Plaid", "fintech", datetime(2020, 5, 10)),
    (4, "Coinbase", "fintech", datetime(2023, 3, 5)),
    (5, "BierzoSEO", "e-commerce", datetime(2022, 8, 10)),
]

# --- TOPOLOGÍA DE TRÁFICO POR ROLES ---
# Define las reglas de comunicación permitidas entre roles de servicio.
# Un rol de la izquierda (key) puede llamar a los roles de la derecha (value list).
topologia_trafico = {
    "ENTRYPOINT": ["COMPUTE", "AI_MODEL"],
    "COMPUTE": ["COMPUTE", "DATA", "AI_MODEL"],
    "AI_MODEL": ["DATA"],
    "DATA": [],
    "ISOLATED": [],
}

# --- CATÁLOGO DE SERVICIOS SEMÁNTICOS ---
# Define los "planos" de los servicios de aplicación, su tipo de infraestructura subyacente y su rol en el tráfico.
# Formato: (nombre_semantico, tipo_infraestructura, rol_trafico)
servicios_catalogo = [
    # Entrypoints (Puertas de entrada)
    ('Public-API', 'API Gateway', 'ENTRYPOINT'),
    ('Mobile-Gateway', 'Load Balancer', 'ENTRYPOINT'),
    
    # Compute (Lógica de negocio)
    ('Auth-Service', 'Lambda', 'COMPUTE'),
    ('Users-Service', 'ECS', 'COMPUTE'),
    ('Transaction-Processor', 'EC2', 'COMPUTE'),
    ('Reporting-Engine', 'EC2', 'COMPUTE'),

    # Data (Bases de datos y almacenamiento)
    ('Customers-DB', 'RDS', 'DATA'),
    ('Transactions-DB', 'DynamoDB', 'DATA'),
    ('Cache-Service', 'ElastiCache', 'DATA'),
    ('Data-Lake', 'S3', 'DATA'),

    # AI (Modelos de Machine Learning)
    ('Fraud-Detection-AI', 'SageMaker', 'AI_MODEL'),

    # Isolated (Servicios de soporte sin tráfico directo de aplicación)
    ('Monitoring-Service', 'CloudWatch', 'ISOLATED'),
    ('Security-Manager', 'IAM', 'ISOLATED'),
]

# --- INSTANCIAS DE SERVICIOS DESPLEGADOS ---
# Asignación estática de servicios a instancias para 20 nodos.
# Formato: (instancia_id, contrato_id, estado, nombre_servicio_asignado, fqdn_simulado)
instancias_servicios = [
    # Cliente 1: Stripe (Contrato ID: 1)
    ('inst_001', 1, 'running', 'Public-API', 'api.stripe.com'),
    ('inst_002', 1, 'running', 'Transaction-Processor', 'tx.internal.stripe.com'),
    ('inst_003', 1, 'stopped', 'Reporting-Engine', 'reports.internal.stripe.com'),
    ('inst_101', 1, 'running', 'Transactions-DB', 'db.tx.internal.stripe.com'),

    # Cliente 2: Chime (Contrato ID: 2)
    ('inst_004', 2, 'running', 'Mobile-Gateway', 'mobile.chime.com'),
    ('inst_005', 2, 'running', 'Users-Service', 'users.internal.chime.com'),
    ('inst_102', 2, 'running', 'Customers-DB', 'db.users.internal.chime.com'),
    ('inst_006', 2, 'running', 'Auth-Service', 'auth.internal.chime.com'),

    # Cliente 3: Plaid (Contrato ID: 3)
    ('inst_007', 3, 'running', 'Public-API', 'api.plaid.com'),
    ('inst_008', 3, 'running', 'Fraud-Detection-AI', 'fraud.internal.plaid.com'),
    ('inst_103', 3, 'running', 'Data-Lake', 'lake.internal.plaid.com'),
    ('inst_009', 3, 'degraded', 'Cache-Service', 'cache.internal.plaid.com'),
    
    # Cliente 4: Coinbase (Contrato ID: 4)
    ('inst_010', 4, 'running', 'Public-API', 'api.coinbase.com'),
    ('inst_011', 4, 'running', 'Transaction-Processor', 'tx.internal.coinbase.com'),
    ('inst_104', 4, 'running', 'Transactions-DB', 'db.tx.internal.coinbase.com'),
    ('inst_012', 4, 'running', 'Monitoring-Service', 'cw.internal.coinbase.com'), # Servicio aislado
    
    # Cliente 5: BierzoSEO (Contrato ID: 5)
    ('inst_013', 5, 'running', 'Public-API', 'api.bierzoseo.es'),
    ('inst_014', 5, 'running', 'Users-Service', 'users.internal.bierzoseo.es'),
    ('inst_105', 5, 'running', 'Customers-DB', 'db.users.internal.bierzoseo.es'),
    ('inst_015', 5, 'error', 'Cache-Service', 'cache.internal.bierzoseo.es'),
]

# --- RUTAS DE TRÁFICO (SEMILLA) ---
# Conexiones estáticas y deterministas entre instancias, respetando la topología de roles.
# Formato: (id_instancia_origen, id_instancia_destino, protocolo_simulado)
rutas_trafico_seed = [
    # Flujo Cliente 1 (Stripe)
    ('inst_001', 'inst_002', 'HTTPS'),   # Public-API -> Transaction-Processor
    ('inst_002', 'inst_101', 'TCP'),     # Transaction-Processor -> Transactions-DB

    # Flujo Cliente 2 (Chime)
    ('inst_004', 'inst_006', 'HTTPS'),   # Mobile-Gateway -> Auth-Service
    ('inst_006', 'inst_005', 'GRPC'),    # Auth-Service -> Users-Service
    ('inst_005', 'inst_102', 'TCP'),     # Users-Service -> Customers-DB

    # Flujo Cliente 3 (Plaid)
    ('inst_007', 'inst_008', 'HTTPS'),   # Public-API -> Fraud-Detection-AI
    ('inst_008', 'inst_009', 'GRPC'),    # Fraud-Detection-AI -> Cache-Service (Degraded)
    ('inst_008', 'inst_103', 'TCP'),     # Fraud-Detection-AI -> Data-Lake

    # Flujo Cliente 4 (Coinbase)
    ('inst_010', 'inst_011', 'HTTPS'),   # Public-API -> Transaction-Processor
    ('inst_011', 'inst_104', 'TCP'),     # Transaction-Processor -> Transactions-DB

    # Flujo Cliente 5 (BierzoSEO)
    ('inst_013', 'inst_014', 'HTTPS'),   # Public-API -> Users-Service
    ('inst_014', 'inst_105', 'TCP'),     # Users-Service -> Customers-DB
    ('inst_014', 'inst_015', 'TCP'),     # Users-Service -> Cache-Service (Error)
]

# --- RANGOS DE RENDIMIENTO (SEMILLA) ---
# Umbrales para simulación de métricas (sin cambios).
rangos_rendimiento = {
  "latency_p95_normal_ms": (80, 200),
  "latency_p95_alerta_ms": (201, 500),
  "latency_p95_critica_ms": (501, 5000),
  "error_rate_normal": (0.0, 0.1),
  "error_rate_alerta": (0.11, 2.0),
  "cpu_normal_percent": (10, 40),
  "cpu_alerta_percent": (41, 85),
  "sla_tipico": ["99.9%", "99.95%", "99.99%"]
}