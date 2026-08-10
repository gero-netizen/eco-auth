# Diagnóstico local — 2026-08-03

- Pasta inicial: vazia, sem repositório Git.
- Flutter 3.44.8 stable / Dart 3.12.2: instalados e validados.
- Docker: não disponível no terminal.
- Node/npm: não disponíveis no terminal do sistema.
- Python 3.12.10 / pip 25.0.1: instalados e validados no Windows.
- Git for Windows 2.55.0: instalado e validado.
- Android Studio 2026.1.3, Android SDK 37 e licenças: instalados e validados.
- Samsung Galaxy A51 / Android 13: autorizado via ADB e reconhecido pelo Flutter.
- Primeiro APK de depuração: compilado, instalado e executado com sucesso no Galaxy A51 em 2026-08-03.
- Tela validada no aparelho: lista demonstrativa de OS, estado offline e ação de rota.
- Backend FastAPI: ambiente virtual criado, 3 testes aprovados e servidor executado na rede privada.
- Integração móvel: Galaxy A51 consultou `/api/v1/work-orders` e exibiu “Conectado à central” em 2026-08-03.
- Persistência local: código Drift/SQLite gerado; `flutter analyze` sem problemas e 2 testes Flutter aprovados.
- Teste offline no aparelho: API desligada, app reaberto e OS recuperada do SQLite com aviso de central indisponível.
- Ciclo de escrita offline aprovado: transição para “Em deslocamento” persistida, operação UUID enfileirada, enviada após reconexão e reconhecida sem duplicação.
- Fila sequencial aprovada: três transições feitas offline foram enviadas em ordem após religar a API, respeitando o versionamento otimista.
- Evidências offline validadas no Galaxy A51: foto, assinatura PNG e QR Code associados à OS e persistidos no SQLite/armazenamento privado do app.
- Upload de evidências aprovado: foto e assinatura verificadas por SHA-256, QR vinculado por UUID e fila local zerada após confirmação idempotente da API.
- Dependências FastAPI/pytest: ainda não instaladas no ambiente virtual do projeto.
- Rede MK-AUTH: dados de conexão ainda não fornecidos; nenhuma tentativa de acesso foi feita.
- OLT: indisponível fisicamente; modo `simulated` é o padrão seguro.

## Ambiente informado

- Windows 11 atualizado, 16 GB de RAM.
- Testes móveis somente em Samsung Galaxy A51 (SM-A515F), Android 13 / One UI 5.1; não instalar emulador.
- Não depender de virtualização, WSL 2 ou Docker na etapa inicial.
- MK-AUTH 25.03, TUX 6.12.
- MikroTik hEX com RouterOS 7.23.2.
- Autenticação de assinantes somente PPPoE.
- Integração RADIUS configurada, porém atualmente apresenta timeout e será diagnosticada separadamente.
- Endereços internos apareceram nas capturas, mas não serão incorporados ao código.

## Instalação prevista no Windows

1. Atualizações do Windows e confirmação de acesso administrativo.
2. Git for Windows.
3. Visual Studio Code e extensões Dart, Flutter e Python.
4. Python 3.12 de 64 bits.
5. Flutter SDK estável, que já inclui Dart.
6. Android Studio apenas para Android SDK, platform-tools e ferramentas de compilação; sem AVD/emulador.
7. Driver USB do fabricante do celular, quando necessário.
8. Dependências Python do backend e dependências Flutter do aplicativo.
9. Testes com `flutter doctor`, ADB, celular físico e API local.

Node.js, Docker Desktop, WSL 2 e PostgreSQL não são necessários para o primeiro ciclo. A base inicial pode usar SQLite; PostgreSQL será preparado quando houver necessidade de implantação multiusuário.

## Próxima sessão de bancada

1. Preencher o levantamento do ambiente.
2. Instalar/configurar as ferramentas de desenvolvimento.
3. Criar `.env` a partir do exemplo, sem compartilhar segredos no chat.
4. Rodar os testes e subir a API local.
5. Confirmar a API da versão instalada do MK-AUTH com dados fictícios.
6. Implementar primeiro o adaptador somente-leitura; habilitar escrita após homologação.
