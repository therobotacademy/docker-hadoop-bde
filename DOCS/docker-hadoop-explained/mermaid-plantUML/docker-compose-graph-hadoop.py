# Read docker-compose.yml again and generate Mermaid and PlantUML snippets + save to files.
import yaml, os
import networkx as nx

compose_path = "/mnt/data/docker-compose.yml"
assert os.path.exists(compose_path), f"File not found: {compose_path}"

with open(compose_path, "r", encoding="utf-8") as f:
    compose = yaml.safe_load(f)

services = compose.get("services", {})

# Build graph
G = nx.DiGraph()

def classify(name):
    n = name.lower()
    if "namenode" in n or n == "nn":
        return "HDFS NameNode"
    if "datanode" in n or n == "dn":
        return "HDFS DataNode"
    if "resourcemanager" in n:
        return "YARN ResourceManager"
    if "nodemanager" in n:
        return "YARN NodeManager"
    if "historyserver" in n or "jobhistory" in n:
        return "MapReduce HistoryServer"
    if "hive" in n and "metastore" in n:
        return "Hive Metastore"
    if "hiveserver" in n or "hiveserver2" in n or "hs2" in n:
        return "HiveServer2"
    if "postgres" in n or "mysql" in n or "mariadb" in n:
        return "Metastore DB"
    if "zookeeper" in n or n == "zk":
        return "ZooKeeper"
    if "kafka" in n:
        return "Kafka"
    if "spark" in n and "thrift" not in n:
        return "Spark"
    if "hue" in n:
        return "Hue"
    return name

# add nodes
for sname, sdef in services.items():
    G.add_node(sname, role=classify(sname), defn=sdef)

# depends_on edges
for sname, sdef in services.items():
    depends = sdef.get("depends_on", {})
    deps = list(depends.keys()) if isinstance(depends, dict) else (depends if isinstance(depends, list) else [])
    for dep in deps:
        if dep in services:
            G.add_edge(dep, sname, kind="depends_on")

# group families
families = {
    "HDFS NameNode": "HDFS",
    "HDFS DataNode": "HDFS",
    "YARN ResourceManager": "YARN / MapReduce",
    "YARN NodeManager": "YARN / MapReduce",
    "MapReduce HistoryServer": "YARN / MapReduce",
    "Hive Metastore": "Hive",
    "HiveServer2": "Hive",
    "Metastore DB": "Hive",
    "ZooKeeper": "Infra",
    "Kafka": "Infra",
    "Spark": "Compute",
    "Hue": "UI",
}
groups = {}
for n in G.nodes:
    groups[n] = families.get(G.nodes[n]["role"], "Other")

# invert mapping
from collections import defaultdict
group_to_nodes = defaultdict(list)
for n, g in groups.items():
    group_to_nodes[g].append(n)

def service_label(name, role, ports):
    ports_txt = "\\n".join(ports) if ports else ""
    base = f"{name}\\n({role})"
    return f"{base}\\n{ports_txt}" if ports_txt else base

# Mermaid text
lines_mermaid = ["graph LR"]
for gname, nodes in group_to_nodes.items():
    lines_mermaid.append(f'  subgraph {gname}')
    for n in sorted(nodes):
        role = G.nodes[n]["role"]
        ports = G.nodes[n]["defn"].get("ports", [])
        label = service_label(n, role, ports)
        lines_mermaid.append(f'    {n}["{label}"]')
    lines_mermaid.append("  end")
for u, v, data in G.edges(data=True):
    if data.get("kind") == "depends_on":
        lines_mermaid.append(f"  {u} --> {v}")
mermaid_text = "\n".join(lines_mermaid)

# PlantUML text
lines_puml = [
    "@startuml",
    "skinparam componentStyle rectangle",
    "title Arquitectura Hadoop derivada de docker-compose",
]
for gname, nodes in group_to_nodes.items():
    lines_puml.append(f'package "{gname}" {{')
    for n in sorted(nodes):
        role = G.nodes[n]["role"]
        ports = G.nodes[n]["defn"].get("ports", [])
        label = service_label(n, role, ports)
        alias = n.replace("-", "_")
        lines_puml.append(f'  ["{label}"] as {alias}')
    lines_puml.append("}")
for u, v, data in G.edges(data=True):
    if data.get("kind") == "depends_on":
        lines_puml.append(f"{u.replace('-', '_')} --> {v.replace('-', '_')}")
lines_puml.append("@enduml")
puml_text = "\n".join(lines_puml)

# Save
mm_path = "/mnt/data/hadoop_architecture.mmd"
puml_path = "/mnt/data/hadoop_architecture.puml"
with open(mm_path, "w", encoding="utf-8") as f:
    f.write(mermaid_text)
with open(puml_path, "w", encoding="utf-8") as f:
    f.write(puml_text)

print("### Mermaid (.mmd)\n")
print("```mermaid")
print(mermaid_text)
print("```")
print("\n\n### PlantUML (.puml)\n")
print("```plantuml")
print(puml_text)
print("```")
print(f"\nArchivos guardados:\n- {mm_path}\n- {puml_path}")
