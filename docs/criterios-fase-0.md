# Critérios de saída da Fase 0

A Fase 0 estará concluída quando:

- [ ] versão e endpoints do MK-AUTH estiverem documentados;
- [ ] conta de integração de privilégio mínimo estiver criada;
- [ ] regras de OS, anexos, GPS e estoque estiverem decididas;
- [ ] ao menos um Android de teste e sua versão estiverem registrados;
- [x] backend subir e testes passarem na máquina de desenvolvimento;
- [x] app Flutter abrir no Android de teste;
- [x] app no Galaxy A51 consultar uma OS simulada pela API na rede local;
- [x] OS recebida permanecer disponível após desligar a API e reabrir o app;
- [ ] consulta somente-leitura de uma OS fictícia funcionar;
- [x] modo offline, reconexão e reenvio idempotente tiverem cenário de teste aprovado;
- [ ] política de segurança, backup e restauração da bancada estiver aceita.

O código de produção do adaptador MK-AUTH só começa após confirmar a documentação da versão instalada. O código da OLT real só começa após receber fabricante, modelo, firmware e protocolo suportado.
