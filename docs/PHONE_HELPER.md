# Kwai Phone Helper

Aplicativo Android local para iniciar um fluxo de postagem no Kwai a partir de um aparelho real já autenticado.

## Escopo do primeiro teste

1. Instalar o APK de debug gerado pelo workflow `Build Kwai Phone Helper APK`.
2. Abrir o app e ativar o serviço `Kwai Phone Helper` em **Configurações > Acessibilidade**.
3. Escolher um vídeo pelo seletor do Android.
4. Escrever a legenda.
5. Manter **Publicar automaticamente** desmarcado no primeiro teste.
6. Tocar em **Preparar no Kwai**.
7. Confirmar que o Kwai recebeu o vídeo e a legenda e que o helper consegue avançar pelas telas.
8. Depois do primeiro teste visual, ativar **Publicar automaticamente** para testar o clique final.

## Privacidade

O app não possui permissão de Internet própria, não lê SMS, não conhece a senha do Kwai e não exporta a sessão da conta. O serviço de Acessibilidade é limitado ao pacote `com.kwai.kuaishou.video.live` e só age quando existe uma tarefa iniciada manualmente no helper.

## Observação

Os textos e a estrutura de telas do Kwai podem mudar. O serviço procura rótulos em português e inglês e poderá precisar de ajustes depois do primeiro teste em um aparelho real.
