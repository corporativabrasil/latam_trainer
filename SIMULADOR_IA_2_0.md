# Corporativa LATAM Trainer — Simulador IA 2.0

## Incluído nesta única entrega

- Turma com 1 a 8 participantes
- Personalidades e objetivos ocultos
- Perfis curiosos, resistentes, técnicos, tímidos e pragmáticos
- Perguntas e reações baseadas no conteúdo real
- Memória completa da conversa
- Avaliação invisível durante a sessão
- Relatório final somente ao encerrar
- Métricas: espanhol, conteúdo, clareza, didática, empatia, controle da turma, exemplos e engajamento
- Persistência no PostgreSQL
- Recuperação da última sessão após atualizar a página

## Instalação

Extraia o ZIP na raiz do projeto e substitua os arquivos.

```powershell
docker compose build backend frontend --no-cache
docker compose up -d
docker compose logs backend --tail=100
```

O backend criará automaticamente a tabela `virtual_participants`.

Não use `docker compose down -v`.


## Correção TypeScript Strict

Esta revisão corrige os erros:

- `session.participants.length is possibly undefined`
- `session is possibly null`

O frontend agora usa uma coleção segura:

```tsx
const participants = session?.participants ?? [];
```

## Comandos recomendados

Como o build anterior falhou, execute exatamente:

```powershell
docker compose build backend frontend --no-cache
docker compose up -d --force-recreate
docker compose ps
docker compose logs backend --tail=100
```

Depois faça `Ctrl + Shift + R` no navegador.
