# Pendência de bancada — RADIUS timeout

O objetivo deste diagnóstico futuro é descobrir por que o MikroTik não recebe resposta do serviço RADIUS usado pelo MK-AUTH. Ele não faz parte da instalação das ferramentas do Windows.

## Ordem segura de verificação

1. Confirmar que o serviço RADIUS está ativo no servidor MK-AUTH.
2. Confirmar o endereço do servidor configurado no MikroTik.
3. Confirmar que o endereço de origem/NAS do MikroTik está cadastrado no MK-AUTH.
4. Testar alcance IP entre MikroTik e servidor nos dois sentidos.
5. Conferir firewall e tráfego UDP das portas de autenticação e contabilização configuradas.
6. Conferir se o segredo compartilhado é idêntico nos dois lados, sem expô-lo em capturas ou logs.
7. Confirmar que o serviço `ppp` está habilitado na entrada RADIUS do MikroTik.
8. Conferir `/ppp aaa` e se `use-radius` está habilitado.
9. Observar os logs do MikroTik e do RADIUS durante uma tentativa feita com cliente fictício.
10. Só depois revisar NAT, rota de retorno, horário e parâmetros específicos do MK-AUTH.

## Interpretação inicial

`RADIUS timeout` normalmente significa ausência de resposta, não necessariamente usuário ou senha PPPoE incorretos. Credenciais PPPoE rejeitadas por um servidor alcançável tendem a produzir uma rejeição explícita. Portanto, começaremos por serviço, conectividade, firewall, portas, NAS e segredo compartilhado.

## Evidências a coletar quando iniciarmos

- Configuração RADIUS sem o segredo.
- Estado de `PPP AAA`.
- Rota até o servidor MK-AUTH.
- Regras de firewall relevantes.
- Log de uma única tentativa fictícia, com dados pessoais ocultos.

