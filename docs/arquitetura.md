# Arquitetura inicial

```text
App Flutter
  SQLite + arquivos locais + fila de saída
       |
       | HTTPS/JWT, sincronização incremental e idempotente
       v
API intermediária (FastAPI)
  autenticação | OS | mídia | estoque | sincronização | auditoria
       |                         |
       v                         v
Adaptador MK-AUTH             Porta OLT
  simulado/real          simulador agora, fabricante depois
```

## Decisões principais

1. **O app não acessa o MK-AUTH diretamente.** A API protege credenciais, normaliza versões e mantém auditoria.
2. **Offline-first.** Toda ação do técnico é salva primeiro no celular. Cada mutação recebe um `operation_id` UUID; reenvios não duplicam ações.
3. **Sincronização incremental.** O app envia a fila de saída e solicita mudanças posteriores ao seu último cursor. Conflitos usam versão otimista e ficam explícitos para revisão.
4. **Fotos e assinaturas são arquivos.** O banco guarda metadados, hash e estado de envio. Uploads serão retomáveis; não viajam no JSON principal de sincronização.
5. **OLT é uma porta de domínio.** `OltGateway` define o contrato. `SimulatedOltGateway` permite desenvolver e testar; o adaptador do fabricante será plugado posteriormente.
6. **MK-AUTH também é adaptador.** O formato interno não replica tabelas do ERP. Isso reduz o impacto de mudanças de versão.

## Módulos planejados

- Identidade e dispositivos
- Ordens de serviço e checklist
- Captura: foto, assinatura e QR Code
- GPS, trilha e roteamento
- Estoque do técnico e movimentações
- Sincronização e conflitos
- Integração MK-AUTH
- Provisionamento de OLT/ONU
- Auditoria, observabilidade e administração

## Estados iniciais da OS

`assigned → traveling → arrived → in_progress → completed`

Saídas alternativas: `blocked` e `not_completed`. Toda transição registra técnico, horário, coordenadas, observação e versão anterior.

## Evolução das fases

- Fase 0: levantamento, contratos e esqueleto.
- Fase 1: autenticação, agenda e OS offline.
- Fase 2: fotos, assinatura, QR, GPS e estoque.
- Fase 3: sincronização robusta e integração real com MK-AUTH.
- Fase 4: rotas, painel operacional e observabilidade.
- Fase 5: integrar a OLT real, homologar em bancada e executar piloto controlado.

