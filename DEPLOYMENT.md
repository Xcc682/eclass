# Linux server deployment (IP access)

This project keeps `docker-compose.yml` for local development. Use the separate
`docker-compose.production.yml` on a Linux server.

## First deployment

1. Install Docker Engine and the Docker Compose plugin.
2. Copy the project to the server, then enter its directory.
3. Create the production environment file:

   ```bash
   cp .env.production.example .env
   chmod 600 .env
   ```

4. Edit `.env`. Replace `SERVER_PUBLIC_IP` with the server's public IPv4 address
   and replace every `REPLACE_...` value. Generate a JWT secret with:

   ```bash
   openssl rand -hex 32
   ```

5. Build and start the stack:

   ```bash
   docker compose -f docker-compose.production.yml config
   docker compose -f docker-compose.production.yml up -d --build
   docker compose -f docker-compose.production.yml ps
   ```

6. Allow TCP port 5667 in both the server firewall and the cloud provider's
   security group. Then open `http://SERVER_PUBLIC_IP:5667`.

## Operations

```bash
# Follow backend logs
docker compose -f docker-compose.production.yml logs -f backend

# Verify readiness from the server
curl http://127.0.0.1:7899/health/ready

# Update after pulling new code
docker compose -f docker-compose.production.yml up -d --build
```

The production stack exposes the frontend on HTTP port 5667. PostgreSQL, Redis
and MinIO remain accessible only to containers on the private Docker network.
FastAPI is additionally bound to `127.0.0.1:7899`, so it is available only from
the Linux server itself. Add a domain and HTTPS reverse proxy before exposing
this to real users.
