
# docker-compose-graph (generalized)
# Read docker-compose.yml and generate Mermaid/PlantUML diagrams grouping services by role.
import os, yaml
import networkx as nx
from collections import defaultdict

COMPOSE_PATH = os.environ.get("COMPOSE_PATH", "/mnt/data/docker-compose.yml")

def load_compose(path: str):
    assert os.path.exists(path), f"File not found: {path}"
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

# ---------- Heuristics ----------

# Port -> role hints (most common)
PORT_HINTS = {
    22: "Infra/SSH",
    80: "Web/HTTP",
    443: "Web/HTTPS",
    3000: "UI/Grafana",
    4040: "Compute/Spark UI",
    5050: "Orchestration/Airflow UI",
    5432: "DB/PostgreSQL",
    5500: "Dev/LiveReload",
    5601: "UI/Kibana",
    5672: "Messaging/RabbitMQ",
    5900: "UI/VNC",
    6379: "Cache/Redis",
    6380: "Cache/Redis",
    7000: "DB/Cassandra",
    7077: "Compute/Spark Master",
    7199: "DB/Cassandra",
    8000: "Web/App",
    8001: "Web/App",
    8002: "Web/App",
    8020: "HDFS/Namenode RPC",
    8042: "YARN/NodeManager UI",
    8080: "Web/App",
    8081: "Web/App",
    8088: "YARN/ResourceManager UI",
    8089: "YARN/ResourceManager UI (host)",
    8188: "MapReduce/HistoryServer UI",
    8500: "Infra/Consul",
    8501: "ML/TF Serving UI",
    8529: "DB/ArangoDB",
    8530: "DB/ArangoDB",
    8649: "Monitoring/Ganglia",
    8761: "Web/Eureka",
    8888: "UI/Jupyter",
    9000: "Storage/MinIO Console",
    9001: "Storage/MinIO Console",
    9002: "Storage/MinIO API",
    9042: "DB/Cassandra",
    9090: "Monitoring/Prometheus",
    9091: "Monitoring/Prometheus Pushgateway",
    9092: "Messaging/Kafka",
    9093: "Monitoring/Alertmanager",
    9100: "Monitoring/Node Exporter",
    9200: "Search/Elasticsearch",
    9300: "Search/Elasticsearch Transport",
    9870: "HDFS/Namenode UI",
    9864: "HDFS/Datanode UI",
    9866: "YARN/NM Log",
    9868: "YARN/RM Log",
    10000: "Hive/HS2 Thrift",
    16010: "HBase/Master UI",
    2181: "Infra/ZooKeeper",
    3306: "DB/MySQL",
    3389: "UI/RDP",
    4242: "Observability/Vector",
    5600: "Observability/Tempo",
    4317: "Observability/OTLP",
}

# Image/name tokens -> role hints
TOKEN_HINTS = {
    # Databases
    "postgres": "DB/PostgreSQL",
    "mysql": "DB/MySQL",
    "mariadb": "DB/MariaDB",
    "mongo": "DB/MongoDB",
    "redis": "Cache/Redis",
    "memcached": "Cache/Memcached",
    "cassandra": "DB/Cassandra",
    "clickhouse": "DB/ClickHouse",
    "influxdb": "DB/InfluxDB",
    "elasticsearch": "Search/Elasticsearch",
    "opensearch": "Search/OpenSearch",
    "solr": "Search/Solr",
    "neo4j": "DB/Neo4j",
    "timescaledb": "DB/PostgreSQL-Timescale",
    "minio": "Storage/MinIO",
    # Messaging/streaming
    "kafka": "Messaging/Kafka",
    "redpanda": "Messaging/Kafka",
    "pulsar": "Messaging/Pulsar",
    "rabbitmq": "Messaging/RabbitMQ",
    "zookeeper": "Infra/ZooKeeper",
    "nats": "Messaging/NATS",
    "mosquitto": "Messaging/MQTT",
    # Big Data / Analytics
    "hadoop": "BigData/Hadoop",
    "namenode": "HDFS/NameNode",
    "datanode": "HDFS/DataNode",
    "resourcemanager": "YARN/ResourceManager",
    "nodemanager": "YARN/NodeManager",
    "historyserver": "MapReduce/HistoryServer",
    "spark": "Compute/Spark",
    "hive": "SQL/Hive",
    "hiveserver": "SQL/HiveServer2",
    "trino": "SQL/Trino",
    "presto": "SQL/Presto",
    "flink": "Compute/Flink",
    "hue": "UI/Hue",
    "superset": "UI/Superset",
    # Web/Proxy
    "nginx": "Web/Proxy",
    "httpd": "Web/HTTPD",
    "caddy": "Web/Caddy",
    "traefik": "Web/Traefik",
    "haproxy": "Web/HAProxy",
    # Observability
    "prometheus": "Monitoring/Prometheus",
    "grafana": "Monitoring/Grafana",
    "loki": "Observability/Loki",
    "tempo": "Observability/Tempo",
    "promtail": "Observability/Promtail",
    "jaeger": "Observability/Jaeger",
    "zipkin": "Observability/Zipkin",
    # Orchestration / CI
    "airflow": "Orchestration/Airflow",
    "jenkins": "CI/Jenkins",
    "gitlab": "CI/GitLab",
    # Auth/Security
    "keycloak": "Auth/Keycloak",
    "vault": "Security/Vault",
    # Dev tools
    "jupyter": "Dev/Jupyter",
    "notebook": "Dev/Jupyter",
    "mlflow": "ML/MLflow",
}

def first_truthy(*vals):
    for v in vals:
        if v:
            return v
    return None

def extract_tokens(service_name: str, service_def: dict):
    tokens = set()
    tokens.update(service_name.lower().replace("_","-").split("-"))
    image = (service_def.get("image") or "").lower()
    if image:
        tokens.update(image.replace("/", "-").split("-"))
        tokens.update(image.split(":")[:1])  # repo
    labels = service_def.get("labels", {})
    if isinstance(labels, dict):
        for k, v in labels.items():
            tokens.update(str(k).lower().split("."))
            tokens.update(str(v).lower().split("."))
    env = service_def.get("environment", {})
    if isinstance(env, dict):
        for k, v in env.items():
            tokens.update(str(k).lower().split("_"))
            if isinstance(v, str):
                tokens.update(v.lower().split("_"))
    return tokens

def extract_ports(service_def: dict):
    raw = service_def.get("ports", []) or []
    ports = []
    for p in raw:
        # formats: "host:container", "ip:host:container", "host:container/proto", "container"
        s = str(p)
        s = s.split("/")[0]
        parts = s.split(":")
        try:
            if len(parts) == 1:
                ports.append(int(parts[0]))
            else:
                ports.append(int(parts[-1]))
        except ValueError:
            continue
    return ports

def classify(service_name: str, service_def: dict) -> str:
    """
    Generic classifier:
    - Looks at image/name/labels/env tokens first.
    - Then infers from exposed ports (fallback).
    - Returns 'Domain/Role' or 'Other/<ServiceName>'.
    """
    tokens = extract_tokens(service_name, service_def)
    # direct token match
    for t in tokens:
        if t in TOKEN_HINTS:
            return TOKEN_HINTS[t]

    # port-based hints
    ports = extract_ports(service_def)
    for p in ports:
        if p in PORT_HINTS:
            return PORT_HINTS[p]

    # heuristics for common app keywords
    n = service_name.lower()
    if any(k in n for k in ["api", "app", "backend", "service", "server"]):
        return "Web/App"
    if any(k in n for k in ["frontend", "web", "ui"]):
        return "Web/Frontend"

    # final fallback
    return f"Other/{service_name}"

def build_graph(services: dict):
    G = nx.DiGraph()
    for name, sdef in services.items():
        G.add_node(name, role=classify(name, sdef), defn=sdef)

    for name, sdef in services.items():
        depends = sdef.get("depends_on", {})
        deps = list(depends.keys()) if isinstance(depends, dict) else (depends if isinstance(depends, list) else [])
        for dep in deps:
            if dep in services:
                G.add_edge(dep, name, kind="depends_on")

    # group by top-level domain before the slash (e.g., "DB/PostgreSQL" -> "DB")
    groups = {}
    for n in G.nodes:
        role = G.nodes[n]["role"]
        group = role.split("/", 1)[0] if "/" in role else role
        groups[n] = group

    group_to_nodes = defaultdict(list)
    for n, g in groups.items():
        group_to_nodes[g].append(n)

    return G, group_to_nodes

def service_label(name, role, ports):
    ports_txt = "\\n".join(ports) if ports else ""
    base = f"{name}\\n({role})"
    return f"{base}\\n{ports_txt}" if ports_txt else base

def to_mermaid(G, group_to_nodes):
    lines = ["graph LR"]
    for gname, nodes in group_to_nodes.items():
        lines.append(f'  subgraph {gname}')
        for n in sorted(nodes):
            role = G.nodes[n]["role"]
            ports = G.nodes[n]["defn"].get("ports", []) or []
            # show host:container strings as-is
            label = service_label(n, role, [str(p) for p in ports])
            lines.append(f'    {n}["{label}"]')
        lines.append("  end")
    for u, v, data in G.edges(data=True):
        if data.get("kind") == "depends_on":
            lines.append(f"  {u} --> {v}")
    return "\n".join(lines)

def to_plantuml(G, group_to_nodes):
    lines = [
        "@startuml",
        "skinparam componentStyle rectangle",
        "title Arquitectura derivada de docker-compose",
    ]
    for gname, nodes in group_to_nodes.items():
        lines.append(f'package "{gname}" {{')
        for n in sorted(nodes):
            role = G.nodes[n]["role"]
            ports = G.nodes[n]["defn"].get("ports", []) or []
            label = service_label(n, role, [str(p) for p in ports])
            alias = n.replace("-", "_")
            lines.append(f'  ["{label}"] as {alias}')
        lines.append("}")
    for u, v, data in G.edges(data=True):
        if data.get("kind") == "depends_on":
            lines.append(f"{u.replace('-', '_')} --> {v.replace('-', '_')}")
    lines.append("@enduml")
    return "\n".join(lines)

def main(compose_path=COMPOSE_PATH):
    compose = load_compose(compose_path)
    services = compose.get("services", {})
    G, group_to_nodes = build_graph(services)
    mermaid = to_mermaid(G, group_to_nodes)
    plantuml = to_plantuml(G, group_to_nodes)
    # write files next to compose file
    base_dir = os.path.dirname(compose_path) or "."
    mm_path = os.path.join(base_dir, "compose_architecture.mmd")
    puml_path = os.path.join(base_dir, "compose_architecture.puml")
    with open(mm_path, "w", encoding="utf-8") as f:
        f.write(mermaid)
    with open(puml_path, "w", encoding="utf-8") as f:
        f.write(plantuml)
    print(f"Written:\n- {mm_path}\n- {puml_path}")
    print("\n--- Mermaid ---\n")
    print(mermaid)
    print("\n--- PlantUML ---\n")
    print(plantuml)

if __name__ == "__main__":
    main()
