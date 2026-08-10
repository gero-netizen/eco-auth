# ISP Field — integração móvel com MK-AUTH

Monorepo inicial para o aplicativo de técnicos do provedor. O desenho é offline-first: o celular trabalha com uma base local, registra todas as alterações em uma fila e sincroniza com uma API intermediária quando a conexão volta.

## Componentes

- `backend/`: API intermediária, regras de negócio e adaptadores do MK-AUTH/OLT.
- `mobile/`: aplicativo Flutter, banco SQLite local e fila de sincronização.
- `docs/`: levantamento do ambiente, arquitetura e contratos.

## Estado da Fase 0

- [x] Arquitetura modular definida
- [x] Contrato inicial da API e sincronização
- [x] Domínio inicial de ordens de serviço
- [x] Adaptador de OLT desacoplado e simulador em memória
- [x] Esqueleto Flutter offline-first
- [ ] Preencher `docs/levantamento-ambiente.md` com o responsável pelo provedor
- [ ] Validar versão e API disponível no MK-AUTH de bancada
- [ ] Instalar Flutter e gerar as pastas nativas Android/iOS
- [ ] Configurar segredos localmente e executar o primeiro teste integrado

## Início rápido do backend

Requer Python 3.11+.

```bash
cd backend
python -m venv .venv
pip install -e ".[dev]"
uvicorn app.main:app --reload
```

A documentação interativa ficará em `http://127.0.0.1:8000/docs`. O projeto inicia em modo simulado; nenhuma chamada é feita ao MK-AUTH ou à OLT reais.

## Segurança

Não grave senhas, tokens, IPs públicos ou backups reais no repositório. Copie `.env.example` para `.env` somente na máquina de desenvolvimento. Em produção, a API intermediária deve ser a única parte com acesso ao MK-AUTH, MikroTik e OLT; o app nunca recebe essas credenciais.

