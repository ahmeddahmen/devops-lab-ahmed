# TP3 Report — Docker Networking and Docker Compose

**Student:** Ahmed Dahmen  
**Course:** DevOps — MPSRCC1  
**TP:** TP 3 — Docker Networking and Docker Compose  

---

## Part 0 — Environment Check

```
docker --version       # Docker version installed
docker compose version # Docker Compose v2 installed
docker info            # Docker daemon running
docker ps -a           # List all containers
docker network ls      # List existing networks
```

Old TP2 containers were removed before starting:
```
docker rm -f product-service order-service
```

---

## Task 1 — Explore Networking and DNS

### 1.1 Default vs User-Defined Bridge

```bash
docker network ls
docker network inspect bridge
docker network create tp3-net
docker network inspect tp3-net
```

**Findings:**
- Default `bridge` network: containers communicate by IP only. No automatic DNS name resolution between containers.
- User-defined bridge (`tp3-net`): automatic DNS name resolution by container name. This is why `order-service` can reach `product-service` by name.

### 1.2 DNS Test on Custom Bridge

```bash
docker run -d --name tp3-web --network tp3-net nginx:alpine
docker run --rm --network tp3-net busybox:1.36 nslookup tp3-web
docker network inspect tp3-net
```

**Result:** `nslookup tp3-web` resolved to the container's IP within `tp3-net`. This confirms Docker DNS works on user-defined networks.

**Why name > IP:** Container IPs are dynamically assigned and can change on restart. Names are stable as long as the container name stays the same.

### 1.3 Cleanup

```bash
docker rm -f tp3-web
docker network rm tp3-net
```

---

## Task 2 — compose.yaml

The `compose.yaml` file (at project root) defines both services:

```yaml
services:
  product-service:
    build:
      context: .
      dockerfile: product-service/Dockerfile.reference
    ports:
      - "8001:8001"
    networks:
      - app-net

  order-service:
    build:
      context: .
      dockerfile: order-service/Dockerfile.reference
    ports:
      - "8002:8002"
    environment:
      PRODUCT_SERVICE_URL: http://product-service:8001
    depends_on:
      - product-service
    networks:
      - app-net

networks:
  app-net:
    driver: bridge
```

**Why `context: .`?** The `Dockerfile.reference` files use `COPY product-service/main.py` and `COPY order-service/requirements.txt`, which reference paths relative to the project root. The build context must be `.` (project root) so Docker can resolve those paths.

**Why `http://product-service:8001` and not `http://localhost:8001`?**  
Inside the Order Service container, `localhost` refers to the container itself — not the host machine and not any other container. `product-service` is resolved by Docker DNS within `app-net` to the Product Service container.

Validation:
```bash
docker compose config
```

---

## Task 3 — Deploy and Test

### 3.1 Build and Start

```bash
docker compose up -d --build
docker compose ps
docker compose logs --tail=20
```

### 3.2 HTTP Endpoints Verification

```
curl.exe http://localhost:8001/health
# {"service":"product-service","status":"healthy"}

curl.exe http://localhost:8001/products
# [{"id":1,"name":"Laptop","price":999.99},{"id":2,"name":"Mouse","price":29.99},{"id":3,"name":"Keyboard","price":79.99}]

curl.exe http://localhost:8002/health
# {"service":"order-service","status":"healthy"}

curl.exe http://localhost:8002/orders
# []
```

### 3.3 Create an Order (PowerShell)

```powershell
$body = @{ product_id = 1; quantity = 2 } | ConvertTo-Json
Invoke-RestMethod -Uri "http://localhost:8002/orders" -Method Post -ContentType "application/json" -Body $body
```

**Expected response:**
```json
{
  "order_id": 1,
  "product_id": 1,
  "quantity": 2,
  "product_name": "Laptop",
  "total": 1999.98
}
```

Order Service called Product Service internally via `http://product-service:8001/products/1` over `app-net`.

### 3.4 DNS Inspection

```bash
docker network ls
docker compose logs order-service
docker compose exec order-service python -c "import socket; print(socket.gethostbyname('product-service'))"
```

The DNS lookup resolves `product-service` to its container IP within `app-net` — not a fixed address but assigned by Docker's embedded DNS.

---

## Task 4 — Failure and Recovery

### 4.1 Stop Product Service

```bash
docker compose stop product-service
docker compose ps
# order-service: running, product-service: exited
```

### 4.2 Order Attempt While Product Service Is Down

```powershell
$body = @{ product_id = 2; quantity = 1 } | ConvertTo-Json
try {
  Invoke-RestMethod -Uri "http://localhost:8002/orders" -Method Post -ContentType "application/json" -Body $body
} catch { $_.Exception.Message }
```

**Result:** HTTP 503 — Order Service returned `{"detail":"Failed to connect to product service: ..."}`.  
Order Service remained **running** but could not complete the request because it depends on Product Service to retrieve product details.

```bash
docker compose logs --tail=30 order-service
```

### 4.3 Restore and Retry

```bash
docker compose start product-service
Invoke-RestMethod -Uri "http://localhost:8002/orders" -Method Post -ContentType "application/json" -Body $body
```

**Result:** Order creation succeeded again after Product Service was back up.

**Why does `depends_on` not guarantee readiness?**  
`depends_on` only controls **startup order** — it starts Product Service before Order Service. It does **not** wait for the application inside the container to be ready to accept HTTP requests. The process may still be initializing when Order Service tries to connect.

---

## Report Questions

**Q1. Compare the default bridge network with a user-defined bridge.**  
The default `bridge` network allows containers to communicate by IP address only. A user-defined bridge (like `app-net`) automatically provides DNS name resolution, so containers can reach each other by service name. User-defined bridges also offer better isolation.

**Q2. Explain service-name DNS and why Order Service uses `http://product-service:8001`.**  
Docker's embedded DNS resolver allows containers on the same user-defined network to resolve each other's names. Inside `app-net`, the hostname `product-service` resolves to the Product Service container's IP. `localhost` inside a container refers only to that container, so it cannot be used to reach another service.

**Q3. Explain `services`, `build`, `ports`, `environment` and `networks` in `compose.yaml`.**  
- `services`: Declares the containers to run.
- `build`: Specifies how to build the image (context = directory, dockerfile = path to Dockerfile).
- `ports`: Maps host port to container port (`HOST:CONTAINER`).
- `environment`: Passes environment variables into the container at runtime.
- `networks`: Attaches the service to named networks for inter-container communication.

**Q4. Why is build context `"."` for these reference Dockerfiles?**  
The `Dockerfile.reference` files use `COPY product-service/main.py .` which is a path relative to the build context. The build context must be the project root (`.`) so that Docker can find files in both `product-service/` and `order-service/` subdirectories.

**Q5. Compare `docker compose up -d`, `stop` and `down`. What does `down` remove?**  
- `up -d`: Builds images (if needed), creates and starts containers in the background.
- `stop`: Stops running containers but does not remove them (state is preserved).
- `down`: Stops and **removes** containers and project networks. Does not remove built images or source code by default.

**Q6. What is the purpose and limitation of `depends_on`?**  
`depends_on` ensures that a service is **started** before the services that depend on it. Its limitation is that it does not wait for the service to be **ready** (i.e., accepting connections). A container can be "started" but its application still initializing.

**Q7. What happened when Product Service stopped, and why could Order Service remain running?**  
Order Service's process was still running — it did not crash. However, when it received a request that required calling Product Service, the HTTP call failed (connection refused/timeout), resulting in a 503 error. Microservices are independent processes; one stopping does not stop the other.

**Q8. How can you verify container DNS and inspect the Compose network?**  
```bash
# DNS verification (from within a running service container):
docker compose exec order-service python -c "import socket; print(socket.gethostbyname('product-service'))"

# Network inspection:
docker network ls
docker network inspect devops-microservices-tp2_app-net
```

---

## Clean-up

```bash
docker compose down
docker compose ps    # should be empty
docker network ls    # app-net should be gone
```
