# Fase 0 — levantamento do ambiente

Preencher sem registrar senhas neste arquivo. Segredos devem ser trocados por canal seguro e armazenados apenas no `.env` local/cofre de produção.

## Responsáveis e escopo

- Responsável técnico do provedor:
- Responsável pelo MK-AUTH:
- Técnicos participantes do piloto:
- Quantidade de técnicos/dispositivos:
- Android mínimo e modelos de celulares: Samsung Galaxy A51 (SM-A515F), Android 13 / One UI 5.1
- Rede de bancada isolada confirmada: [ ]
- Backup/snapshot antes dos testes confirmado: [ ]

## Estação de desenvolvimento

- Sistema operacional: Windows 11 atualizado
- Memória RAM: 16 GB
- Acesso administrativo ao Windows: confirmado
- Emulador Android: não será utilizado
- Dispositivo de teste: celular Android físico via USB/depuração sem fio
- Virtualização/WSL/Docker: fora do escopo inicial
- Ferramentas instaladas: nenhuma; instalação será feita antes da Fase 1

## MK-AUTH de bancada

- Versão exata: MK-AUTH 25.03 / TUX 6.12
- URL/IP interno: confirmado visualmente na rede de bancada; manter fora de documentação compartilhada
- Tipo de certificado HTTPS:
- Documentação/API disponível e versão:
- Forma de autenticação da API:
- Endpoint de clientes:
- Endpoint de ordens de serviço:
- Endpoint de títulos/bloqueio:
- Webhooks disponíveis:
- Limites de requisição conhecidos:
- Fuso horário configurado:
- Usuário técnico exclusivo e permissões mínimas: [ ]

### Dados fictícios mínimos

- [ ] Cliente ativo
- [ ] Cliente bloqueado
- [ ] Cliente aguardando instalação
- [ ] OS de instalação
- [ ] OS de manutenção
- [ ] Cliente rural com coordenadas
- [ ] Materiais/equipamentos com números de série

## Rede e MikroTik

- Modelo e RouterOS: MikroTik hEX, RouterOS 7.23.2
- IP de gerenciamento interno: confirmado visualmente na rede de bancada; manter fora de documentação compartilhada
- PPPoE/RADIUS usado: autenticação somente PPPoE; confirmar se o MK-AUTH entrega autenticação por RADIUS
- Profiles/pools de teste:
- API habilitada somente na rede de bancada: [ ]
- Usuário exclusivo com permissões mínimas: [ ]

### Pendência RADIUS observada

- O MikroTik já possui configuração RADIUS, mas a tentativa de autenticação PPPoE retorna `RADIUS timeout`.
- Essa falha não bloqueia a instalação do ambiente, o app offline, o backend ou o simulador de OLT.
- Ela bloqueia apenas o teste integrado de autenticação PPPoE e deverá ser resolvida antes da homologação com MK-AUTH.
- Não alterar simultaneamente segredo, firewall e endereços: o diagnóstico será feito por camadas e com cliente fictício.

### Interfaces observadas no MikroTik

- `ether1_wan`
- `ether4_Mk-Auth`
- `ether5_local`
- `bridgeLocal`

Os nomes ajudam no diagnóstico, mas não devem ser fixados no código. Serão parâmetros de configuração.

## OLT (quando chegar)

- Fabricante/modelo/firmware:
- Protocolos disponíveis (SSH, Telnet, SNMP, API):
- MIB/documentação/CLI:
- Modos de provisionamento e perfis VLAN:
- ONU/ONTs compatíveis e números de série de teste:
- Critério de sucesso (registro, potência, VLAN, PPPoE):

## Regras operacionais a decidir

- Quem pode receber/repassar uma OS?
- Quais campos são obrigatórios para concluir cada tipo de OS?
- Quantas fotos e quais categorias são obrigatórias?
- Assinatura é obrigatória em quais cenários?
- Precisão mínima do GPS e política de retenção?
- O técnico pode ajustar estoque sem aprovação?
- Como tratar duas edições offline na mesma OS?
- Por quantos dias o celular guarda dados offline?
- O que deve ser apagado após desligamento de um técnico?

## Teste de conectividade (a executar na bancada)

1. Notebook alcança a API do MK-AUTH pela rede isolada.
2. Conta de integração só consegue ler/alterar os recursos autorizados.
3. Consulta de um cliente fictício funciona.
4. Consulta e atualização de uma OS fictícia funcionam.
5. Repetição da mesma atualização não duplica registros.
6. Logs não exibem senha, token, documento ou foto.
