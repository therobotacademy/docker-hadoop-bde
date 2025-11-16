## Cómo usar **Mermaid**

En un README.md (GitHub/GitLab/VS Code)

1. Abre el `.mmd` y copia su contenido.
2. Pégalo dentro de un bloque en tu Markdown:

````markdown
```mermaid
# pega aquí el contenido de hadoop_architecture.mmd
````

3) En **VS Code**, instala la extensión “Markdown Preview Mermaid Support” para verlo en la preview.


## Cómo usar **PlantUML**

### Opción 1 — VS Code
1) Instala la extensión **PlantUML**.  
2) Abre `hadoop_architecture.puml` y usa “Open Preview”.

### Opción 2 — Línea de comandos (local)
1) Requisitos: **Java** y **Graphviz** instalados.  
2) Descarga `plantuml.jar` y ejecuta:

```bash
java -jar plantuml.jar hadoop_architecture.puml
# Genera PNG/SVG en el mismo directorio
```

### Opción 3 — Docker

```bash
docker run --rm -v "$PWD":/data plantuml/plantuml hadoop_architecture.puml
```

## ANEXO DE CÓDIGO: `docker-compose-graph_general.py`
**Generalización de `classify`** para que funcione con **cualquier** `docker-compose`:


* **Tokens**: inspecciona `service name`, `image`, `labels` y variables de `environment` para detectar tecnologías comunes (Postgres, Redis, Kafka, Spark, Nginx, Keycloak, etc.).
* **Puertos**: si los tokens no bastan, infiere el **rol** por puertos expuestos (mapa de >40 puertos habituales: 5432→Postgres, 9092→Kafka, 9200→Elasticsearch, 8088→YARN RM UI, 9870→HDFS NN, 80/443→HTTP/HTTPS, etc.).
* **Heurística de nombre**: si encuentra `api`, `app`, `backend`, `frontend`, `ui`, clasifica como **Web/App** o **Web/Frontend**.
* **Fallback**: si no hay coincidencias, etiqueta como `Other/<ServiceName>`.
* **Agrupación automática**: agrupa por el **dominio** de la etiqueta (`DB`, `Messaging`, `Web`, `Compute`, `BigData`, `Monitoring`, `Observability`, `Orchestration`, `Auth`, `Storage`, `Infra`, `UI`, `Dev`, `CI`, `Security`, `Other`…).

Cómo usarlo:
1. Pon tu `docker-compose.yml` en la misma carpeta (o usa la ruta por defecto que ya apunta a `/mnt/data/docker-compose.yml`).
2. Ejecuta el script (puedes setear `COMPOSE_PATH` si quieres otra ruta):

```bash
python /mnt/data/docker-compose-graph.py
# o
COMPOSE_PATH=/ruta/a/tu/docker-compose.yml python docker-compose-graph.py
```

3. Se generan dos ficheros **editables** al lado del compose:

* 🐟 `compose_architecture.mmd` (Mermaid)
* 🌿 `compose_architecture.puml` (PlantUML)


