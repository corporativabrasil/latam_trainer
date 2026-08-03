# Implementação local

1. Extraia a pasta `corporativa-latam-trainer`.
2. Abra o Docker Desktop.
3. No PowerShell, entre na pasta do projeto.
4. Execute:

```powershell
docker compose down
docker compose build --no-cache
docker compose up
```

5. Abra `http://localhost:5173`.

## Atualização sobre instalação anterior

Caso já exista uma instalação, não apague o volume do PostgreSQL. O comando `docker compose down` preserva os dados. Evite `docker compose down -v`.
