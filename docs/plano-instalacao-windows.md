# Preparação do Windows 11

Este roteiro será executado antes da Fase 1. Não usar emulador Android.

## Bloco 1 — ferramentas básicas

- Git for Windows
- Visual Studio Code
- Python 3.12 de 64 bits

Validação: Git e Python respondem no terminal, e o VS Code abre o projeto.

## Bloco 2 — Android e Flutter

- Flutter SDK estável em uma pasta sem espaços, por exemplo `C:\dev\flutter`
- Android Studio
- Android SDK, SDK Platform, Build-Tools, Command-line Tools e Platform-Tools
- Extensões Flutter e Dart no VS Code
- Aceitar licenças com `flutter doctor --android-licenses`

Não instalar nem criar Android Virtual Device.

## Bloco 3 — celular físico

1. Ativar opções do desenvolvedor.
2. Ativar depuração USB.
3. Instalar driver do fabricante, se o Windows não reconhecer o aparelho.
4. Autorizar a chave RSA mostrada no celular.
5. Confirmar o dispositivo com ADB e `flutter devices`.

Durante o desenvolvimento, o celular e o computador deverão estar na mesma rede quando o app acessar a API pelo Wi-Fi. `127.0.0.1` no celular aponta para o próprio celular, não para o computador; o app usará o IP local configurável do computador.

## Bloco 4 — projeto

- Criar ambiente virtual do backend.
- Instalar FastAPI e dependências de teste.
- Gerar os projetos Android/iOS do Flutter; no Windows, somente Android será compilado.
- Instalar pacotes Flutter.
- Executar testes do backend e do aplicativo.
- Subir a API em modo simulado e abrir o app no celular.

## Cuidados

- Não usar a conta `admin` dos equipamentos no aplicativo.
- Criar contas exclusivas de integração com privilégio mínimo.
- Não salvar senhas em código, capturas ou Git.
- Manter firewall liberado apenas para a rede privada de bancada.
- Começar o MK-AUTH em modo somente-leitura.

