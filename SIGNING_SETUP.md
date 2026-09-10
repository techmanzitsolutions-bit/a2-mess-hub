# A2 MESS HUB permanent Android signing

The production APK must always use the same private Android keystore. Never commit the keystore or its passwords to this public repository.

Create these GitHub Actions repository secrets:

- `ANDROID_KEYSTORE_BASE64` — base64 text of the permanent `.jks` file
- `ANDROID_KEYSTORE_PASSWORD` — keystore password
- `ANDROID_KEY_ALIAS` — permanent key alias
- `ANDROID_KEY_PASSWORD` — key password

The release workflow must decode `ANDROID_KEYSTORE_BASE64` only inside the GitHub Actions runner, build/sign the APK with that keystore, and upload only the signed APK artifact.

Every new APK must also use a versionCode greater than the previous installed build. A recommended CI scheme is `1000 + GITHUB_RUN_NUMBER` for the canonical release workflow.

Do not publish the keystore, base64 keystore data, passwords, or key password in source files, workflow logs, issues, or commits.
