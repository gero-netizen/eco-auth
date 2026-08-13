#!/usr/bin/env bash
# Faz backup do banco PostgreSQL do eco-auth, comprime e mantém só os
# backups mais recentes (apaga os antigos sozinho).
#
# Uso:
#   DATABASE_URL=postgresql://usuario:senha@host:5432/banco ./backup_database.sh
#
# Agendamento sugerido (cron, todo dia às 3h da manhã):
#   0 3 * * * DATABASE_URL=postgresql://... /caminho/backup_database.sh >> /var/log/eco-auth-backup.log 2>&1

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/var/backups/eco-auth}"
KEEP_LAST="${KEEP_LAST:-14}"  # quantos backups manter (padrão: últimos 14 dias)

if [ -z "${DATABASE_URL:-}" ]; then
  echo "ERRO: defina a variável DATABASE_URL (postgresql://usuario:senha@host:porta/banco)." >&2
  exit 1
fi

if [[ "$DATABASE_URL" != postgresql://* && "$DATABASE_URL" != postgres://* ]]; then
  echo "ERRO: este script só funciona com PostgreSQL. Para SQLite, basta copiar o arquivo .db." >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"

timestamp="$(date -u +%Y%m%d-%H%M%S)"
backup_file="$BACKUP_DIR/eco-auth-$timestamp.sql.gz"
tmp_file="$backup_file.tmp"

echo "[$(date -u +%FT%TZ)] Iniciando backup em $backup_file"

if pg_dump "$DATABASE_URL" --no-owner --no-privileges | gzip > "$tmp_file"; then
  mv "$tmp_file" "$backup_file"
  size="$(du -h "$backup_file" | cut -f1)"
  echo "[$(date -u +%FT%TZ)] Backup concluído com sucesso ($size): $backup_file"
else
  echo "[$(date -u +%FT%TZ)] ERRO: falha ao gerar o backup." >&2
  rm -f "$tmp_file"
  exit 1
fi

# Rotação: mantém só os $KEEP_LAST backups mais recentes, apaga o resto.
backup_count="$(find "$BACKUP_DIR" -maxdepth 1 -name 'eco-auth-*.sql.gz' | wc -l)"
if [ "$backup_count" -gt "$KEEP_LAST" ]; then
  to_remove=$((backup_count - KEEP_LAST))
  echo "[$(date -u +%FT%TZ)] Removendo $to_remove backup(s) antigo(s), mantendo os $KEEP_LAST mais recentes."
  find "$BACKUP_DIR" -maxdepth 1 -name 'eco-auth-*.sql.gz' -print0 \
    | xargs -0 ls -1t \
    | tail -n "$to_remove" \
    | xargs -r rm -v
fi

echo "[$(date -u +%FT%TZ)] Backup finalizado. Total de backups mantidos: $(find "$BACKUP_DIR" -maxdepth 1 -name 'eco-auth-*.sql.gz' | wc -l)"
