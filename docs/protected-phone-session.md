# Sessão protegida de login por telefone

Workflow: `.github/workflows/kwai-api34-phone-remote-login.yml`.
Reutiliza a preparação e navegação de `kwai-api34-router-phone-proof-v2.yml`; Android 14 sem janela gráfica. Não usa o fluxo Google.

Requer o secret existente `KWAI_REMOTE_EMAIL`. Cloudflared inicia somente com `--allowed-mail`; antes de publicar o link, o script exige redirecionamento de autenticação ao acessar /health sem cookies. Se receber a resposta do servidor diretamente ou não conseguir comprovar a proteção, encerra o túnel. Referência: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/ .

O status de commit `kwai/phone-remote` informa quando o formulário está pronto e contém o link temporário. A sessão dura aproximadamente 25 minutos após a inicialização da página. O status registra prontidão naquele instante, não monitoramento permanente; o link deixa de funcionar quando o runner encerra. Inicie outra execução manual quando necessário.

A página permite tocar na tela, rolar a lista de países, voltar e digitar somente números, espaços e +. Selecione Brasil +55 antes de informar o telefone. O PIN de acesso recebido por e-mail pertence ao gateway; o código recebido pelo telefone pertence ao Kwai. Ambos são digitados somente nas respectivas telas, nunca em issues, chat ou logs.

## Backup experimental

Depois de autenticar, o usuário pode fornecer uma senha de 16 a 256 caracteres na página protegida e baixar `kwai-session-encrypted.bin`. O servidor para o Kwai e lê /data/user/0/com.kwai.kuaishou.video.live. O conteúdo fica em memória, é criptografado com AES-256-GCM e enviado para download. A senha não é gravada. Nenhum artifact ou cache da sessão é publicado.

Formato: cabeçalho ASCII `KWAI-APPDATA-V1\n`, salt de 16 bytes, nonce de 12 bytes, seguido de ciphertext e tag GCM. Derivação scrypt: N=32768, r=8, p=1, 32 bytes, senha UTF-8. O cabeçalho completo, salt e nonce são autenticados como AAD.

A exportação dos dados do app NÃO prova que a conta continuará autenticada em outro runner. Android Keystore e identificadores do dispositivo não estão incluídos. O teste anterior entre runners verificou dados sem autenticação e de outra variante do pacote. Não publicar automaticamente nem declarar persistência de login antes de testar restauração real.

O servidor escuta apenas em 127.0.0.1, não registra requests nem comandos, não aceita shell arbitrário e exige token CSRF nas mutações. Sua cópia de ambiente exclui o token do GitHub e o e-mail de acesso. Screenshots do login ficam somente nas respostas do acesso protegido, sem gravação em artifacts.
