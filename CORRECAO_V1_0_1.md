# Corporativa LATAM Trainer 1.0.1

## Correção aplicada

A página `frontend/src/pages/Projects.tsx` utilizava uma função assíncrona diretamente como callback do `useEffect`, causando erro no build TypeScript.

Foi alterado de:

```tsx
useEffect(load, []);
```

para:

```tsx
useEffect(() => {
  void load();
}, []);
```

## Implantação limpa

No PowerShell, dentro da pasta do projeto:

```powershell
docker compose down

docker compose build --no-cache

docker compose up
```

Acesse `http://localhost:5173`.
