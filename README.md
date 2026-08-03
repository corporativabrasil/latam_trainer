# Corporativa LATAM Trainer AI — Enterprise 2.0

Plataforma de preparação do instrutor para tradução contextualizada, estudo, pronúncia e simulação de treinamentos em espanhol.

## Recursos incluídos

- Dashboard executivo de preparação
- Biblioteca de treinamentos
- Upload de PDF, DOCX, PPTX, TXT e Markdown
- Extração de conteúdo
- Tradução contextual com OpenAI
- Editor bilíngue português/espanhol
- Glossário por treinamento
- Manual do instrutor gerado por IA
- Plano de preparação
- Pronúncia guiada com síntese de voz do navegador
- Simulador de participantes com avaliação da resposta
- Autenticação JWT
- PostgreSQL, FastAPI, React/Vite, Docker e Nginx

## Executar

```powershell
docker compose down
docker compose build --no-cache
docker compose up
```

Acesse: http://localhost:5173

Login inicial:
- admin@corporativabrasil.com.br
- Admin@123

API: http://localhost:8000/docs

## Inteligência artificial

Preencha `OPENAI_API_KEY` no `.env` para ativar tradução, roteiro e simulação reais.

## Observação

A dependência `bcrypt==4.0.1` está fixada para compatibilidade com `passlib==1.7.4`.
