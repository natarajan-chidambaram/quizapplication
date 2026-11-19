# Generated app

The services of this app and how they are built are described in
`web_app/docker-compose.yml`; Docker Compose builds and starts them together.

## Run it

From this folder, with Docker running:

```bash
cd web_app
docker compose up --build
```

| Service | Address |
| --- | --- |
| frontend | http://localhost:3000 |
| backend | http://localhost:8000 |
| library_agent_agent | http://localhost:8765 |
| library_agent_agent | http://localhost:5000 |

## Using other ports

Each service's `ports` entry in `web_app/docker-compose.yml` reads `"<port on this machine>:<port in
the container>"`. Change the first number to publish a service on another port. The web
app's API address is fixed when its image is built (`VITE_API_URL` in the same
file), so change it too when you move the API.

<!-- Run instructions written by BESSER and rewritten on each generation. Delete this line to keep your own edits. -->
