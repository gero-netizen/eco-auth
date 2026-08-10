# Integração MK-AUTH somente leitura

Fontes oficiais consultadas em 04/08/2026:

- Portal da API: https://postman.mk-auth.com.br/
- Guia oficial: https://wiki.mk-auth.com.br/doku.php?id=mk-auth_api
- Autenticação e exemplo de planos: https://wiki.mk-auth.com.br/doku.php?id=api_token

## Contrato confirmado

- Uma conta de integração recebe `client_id` e `client_secret` no controle de usuários.
- A autenticação inicial usa Basic Auth em `GET /api/`.
- O JWT retornado tem validade documentada de 10 minutos.
- As chamadas seguintes usam Bearer Token.
- O endpoint documentado `GET /api/plano/listagem` permite um primeiro teste somente leitura.
- O perfil do usuário deve liberar explicitamente o método GET necessário.

## Proteções adotadas

- O modo padrão continua `MKAUTH_MODE=simulated`.
- O cliente real não contém métodos de alteração.
- Credenciais nunca são gravadas no repositório.
- A URL real precisa usar HTTPS.
- A validação de certificado permanece habilitada.
- Não serão desabilitadas verificações TLS para contornar a tela HTTP atual da bancada.

## Pendências para o primeiro teste

- Configurar HTTPS com certificado válido no MK-AUTH de bancada.
- Criar usuário exclusivo de integração.
- Habilitar apenas GET para o teste de planos.
- Preencher o `.env` local, sem compartilhar seus valores.
- Confirmar na documentação da versão 25.03 os endpoints de OS antes de implementá-los.
