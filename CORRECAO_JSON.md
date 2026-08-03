# Correção JSON — Simulador IA 2.0

Corrige o erro `JSONDecodeError: Expecting value`.

## Arquivos

- backend/app/services/ai.py
- backend/app/api/routes.py

## Instalação

Extraia na raiz do projeto e substitua os arquivos. Depois execute:

```powershell
docker compose build backend --no-cache
docker compose up -d --force-recreate backend
docker compose logs backend --tail=100
```

Não é necessário reconstruir o frontend.
