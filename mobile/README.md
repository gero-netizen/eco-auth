# Aplicativo Flutter

O código inicial separa apresentação, domínio, persistência e sincronização. Como o Flutter SDK não está instalado neste ambiente, as pastas nativas ainda não foram geradas.

Após instalar Flutter 3.22+:

```bash
cd mobile
flutter create --platforms=android,ios .
flutter pub get
dart run build_runner build
flutter test
flutter run
```

O app começa com dados demonstrativos e uma faixa explícita de estado offline. Antes do piloto, devem ser adicionados armazenamento seguro de token, login, permissões Android/iOS, criptografia local conforme a política definida e a implementação HTTP real do `SyncRemoteDataSource`.
