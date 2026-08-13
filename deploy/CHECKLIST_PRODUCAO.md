# Checklist de produção — eco-auth.com

Use esta lista, de cima para baixo, quando a VPS estiver pronta. Cada item
marcado como **[crítico]** nunca pode reaproveitar valor de bancada.

## 1. DNS

- [ ] Criar registro **A** de `eco-auth.com` apontando para o IP da VPS
- [ ] Criar registro **A** de `www.eco-auth.com` apontando para o mesmo IP
- [ ] Esperar a propagação (`nslookup eco-auth.com` deve devolver o IP certo)

## 2. Firewall da VPS

- [ ] Liberar só as portas **22** (SSH), **80** e **443**
- [ ] **Nunca** expor a porta 5432 (Postgres) publicamente — no
      `docker-compose.yml` ela já fica só na rede interna do Docker por
      padrão; confirme que continua assim
- [ ] Se usar `ufw`: `sudo ufw allow 22,80,443/tcp && sudo ufw enable`

## 3. Segredos — gerar valores novos [crítico]

Gere cada um com:
```
python3 -c "import secrets; print(secrets.token_urlsafe(48))"
```

- [ ] `JWT_SECRET` — novo, nunca o `bench-session-...` de bancada
- [ ] `INTEGRATION_ENCRYPTION_KEY` — novo, separado do `JWT_SECRET`
- [ ] `POSTGRES_PASSWORD` — novo
- [ ] `CENTRAL_PASSWORD` — nova senha forte (não `Bancada@2026`)
- [ ] `PLATFORM_ADMIN_PASSWORD` — nova senha forte, diferente da `CENTRAL_PASSWORD`
- [ ] `TECHNICIAN_PASSWORD` — usada só como fallback de bancada; cada
      técnico real deve ter seu próprio usuário criado pela Central
      (Técnicos → Criar), nunca use essa conta genérica em campo

## 4. Configuração das integrações reais [crítico]

- [ ] `MKAUTH_BASE_URL` — endereço real do MK-AUTH do provedor
- [ ] `MKAUTH_CLIENT_ID` / `MKAUTH_CLIENT_SECRET` — gerados no painel do MK-AUTH
- [ ] `MKAUTH_VERIFY_SSL=true` — só use `false` se o certificado do
      MK-AUTH for autoassinado (bancada); em produção, prefira certificado
      válido e deixe `true`
- [ ] `MKAUTH_WRITES_ENABLED` — comece com `false`, confirme o
      diagnóstico e a leitura de dados primeiro, só depois ative
- [ ] `ROUTEROS_HOST` / `ROUTEROS_USERNAME` / `ROUTEROS_PASSWORD` — do
      MikroTik real de cada provedor (usuário de API dedicado, só leitura)

## 5. Deploy

- [ ] Clonar o repositório na VPS
- [ ] Copiar `backend/.env.production.example` para `backend/.env` e
      preencher com os valores dos passos 3 e 4
- [ ] `cd backend && docker compose up -d --build`
- [ ] Confirmar que os dois serviços subiram: `docker compose ps`
- [ ] Testar localmente na VPS antes do Nginx entrar:
      `curl http://127.0.0.1:8000/health` deve responder `{"status":"ok"}`

## 6. Nginx + HTTPS

- [ ] Seguir o passo a passo em `deploy/nginx/eco-auth.conf`
- [ ] Confirmar HTTPS funcionando: abrir `https://eco-auth.com/central/login`
      no navegador e checar o cadeado
- [ ] Confirmar o redirecionamento: `http://eco-auth.com` deve levar
      automaticamente para `https://`

## 7. Backup

- [ ] Copiar `backend/scripts/backup_database.sh` para a VPS
- [ ] Testar rodando manualmente uma vez (veja se o arquivo `.sql.gz`
      aparece em `/var/backups/eco-auth`)
- [ ] Agendar no cron (diário, de madrugada):
      ```
      0 3 * * * DATABASE_URL=postgresql://... /caminho/backup_database.sh >> /var/log/eco-auth-backup.log 2>&1
      ```
- [ ] Guardar uma cópia dos backups **fora da VPS** também (ex.: enviar
      pra um bucket S3/Backblaze, ou baixar periodicamente pro seu PC) —
      um backup que mora só no mesmo servidor não protege contra a VPS
      inteira falhar

## 8. Primeiro login real

- [ ] Entrar em `https://eco-auth.com/central/login` com o
      `CENTRAL_USERNAME`/`CENTRAL_PASSWORD` novos
- [ ] Trocar a senha do primeiro acesso, se ainda não tiver feito
- [ ] Confirmar diagnóstico do MK-AUTH (Integração MK-AUTH → Executar
      diagnóstico) — deve aparecer `"status":"connected"`
- [ ] Confirmar diagnóstico do MikroTik da mesma forma
- [ ] Criar o primeiro técnico de verdade (não o de bancada)
