# Contrato de sincronização v1

## Envio (`POST /api/v1/sync/push`)

```json
{
  "device_id": "uuid-do-celular",
  "operations": [
    {
      "operation_id": "uuid-unico",
      "entity_type": "work_order",
      "entity_id": "os-123",
      "kind": "transition",
      "base_version": 3,
      "occurred_at": "2026-08-03T12:00:00Z",
      "payload": {"to_status": "arrived", "latitude": -23.5, "longitude": -46.6}
    }
  ]
}
```

O servidor responde `accepted`, `duplicate`, `conflict` ou `rejected` por operação. Um `operation_id` já processado sempre devolve o resultado anterior.

O diário de idempotência é persistido em SQLite. Reiniciar a API não faz o servidor esquecer operações já recebidas do celular.

## Recebimento (`GET /api/v1/sync/pull?cursor=...`)

Retorna alterações autorizadas para o técnico e um novo cursor opaco. A primeira carga usa cursor vazio. Remoções são tombstones para que também sejam aplicadas offline.

O cursor atual é uma sequência crescente representada como texto. O backend registra cada alteração aceita no mesmo diário persistente usado para idempotência. Repetir um cursor é seguro e devolve somente alterações posteriores a ele.

## Anexos

1. O app cria metadado local e hash SHA-256.
2. Solicita uma sessão de upload.
3. Envia o binário de forma retomável.
4. Anexa a referência à OS por uma operação idempotente.
5. Só remove o arquivo local conforme a política de retenção.
