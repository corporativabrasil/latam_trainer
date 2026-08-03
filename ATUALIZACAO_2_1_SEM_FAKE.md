# Corporativa LATAM Trainer AI 2.1 — Núcleo funcional

Esta atualização mantém a mesma base e remove os principais comportamentos demonstrativos.

## Implementado
- IA não devolve mais texto de demonstração: sem `OPENAI_API_KEY`, a API retorna erro claro 503.
- Simulador gera pergunta real e avaliação estruturada com notas calculadas pela IA.
- A nota da simulação é persistida em `study_sessions`.
- Pronúncia usa reconhecimento de voz real do Chrome/Edge, compara a transcrição com a frase e persiste a pontuação.
- Plano de preparação usa dados reais por treinamento.
- Dashboard não exibe mais empresa, treinamento ou tarefas fictícias.
- Manual do instrutor é persistido e pode ser editado/salvo.
- Exclusão real de materiais e arquivo físico disponível pela API.
- Dependências Vite fixadas, sem `latest`.

## Configuração obrigatória para IA
No `.env`:

```
OPENAI_API_KEY=sua-chave
OPENAI_MODEL=gpt-4.1-mini
```

## Atualização

```
docker compose down
docker compose build --no-cache
docker compose up
```

O banco existente é preservado se você não usar `-v` no `docker compose down`.
