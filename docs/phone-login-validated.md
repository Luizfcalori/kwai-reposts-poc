# Login por telefone validado — 2026-10-04

## Resultado confirmado

Execução: https://github.com/Luizfcalori/kwai-reposts-poc/actions/runs/37175907829
Commit testado: `8e11c772bc475b982e50ce71bac7779d61518a6b`.
Workflow reutilizado: `.github/workflows/kwai-api34-router-phone-proof-v2.yml`.
Android 14/API 34, google_apis, x86_64, pacote ARM64 via tradução nativa.
Kwai `com.kwai.kuaishou.video.live`, versão `13.8.30.646601` (646601).
Certificado SHA-256 conferido com o pin já usado no workflow full-community:
`588774ea798843484c7100da2450005090522fda0dcb64be01c04079349c0acc`.

## Rota reproduzida

1. Instalar o bundle completo da variante acima.
2. Iniciar o roteador exportado `com.kscorp.oversea.platform.router.ui.UriRouterActivity` com ação VIEW e URI `kwai://loginchannel?login=phone`.
3. Aguardar `com.yxcorp.gifshow.login.activity.CommonLoginActivity`.
4. Localizar `login_platform_expand_text`, cujo texto observado foi `or use Facebook  |  Phone`.
5. Clicar no trecho Phone dentro desse TextView, calculando a posição a partir do texto e dos bounds atuais. Ele não aparece como nó independente com texto exatamente Phone.
6. Confirmar `com.yxcorp.gifshow.login.PhoneAccountActivityV2` em primeiro plano e um EditText habilitado pertencente ao pacote do Kwai.
7. Parar antes de preencher dados ou tocar Get Code.

Resultado do artefato:

```text
status=phone_field_visible
activity=com.yxcorp.gifshow.login.PhoneAccountActivityV2
texts=Enter your phone number | US +1 | Phone number | Get Code | Or login with Google
```

Screenshot e XML foram inspecionados: campo vazio, seletor de país US +1, teclado numérico e Get Code desabilitado. Nenhum telefone, senha, OTP ou conta foi utilizado. O runner terminou; não há sessão interativa mantida aberta. Para autenticação futura, primeiro preparar interação protegida e selecionar Brasil +55 na interface legítima.

## Por que as análises anteriores não resolveram

O artefato JADX 37175513353 é da variante `com.kwai.video`: TinyLoginActivity.initView configura apenas Google. `arg_tiny_login_source` é repassado como origem; não foi encontrada seleção de telefone nessa classe.

O artefato do teste 37137091030 já mostrava CommonLoginActivity e o texto composto contendo Phone. O detector exigia Phone isolado e não executou o clique. A correção reconhece o trecho no texto composto. Não é necessário iniciar activities não exportadas, modificar APK ou alterar a segurança do Android.

A URI sozinha abriu o painel completo; este teste comprova a combinação roteador + clique legítimo, não um redirecionamento automático por `login=phone`.

## Limites e continuidade

Esta prova confirma apenas navegação até o formulário. Não comprova autenticação, restauração de sessão autenticada nem publicação automática. Não repetir as rotas descartadas como primeira tentativa. Reutilizar este workflow e esta variante para a próxima etapa. Credenciais, tokens, OTPs e snapshots autenticados não podem ser publicados no repositório ou nos artifacts públicos. Os artifacts desta prova têm retenção de um dia; este registro mantém as conclusões e identificadores.
