# Kwai Reposts — prova de conceito isolada

Teste de infraestrutura Android em repositório público próprio. Não contém coleta de vídeos, login, cookies, postagem ou agendamento.

## Executar

Actions → **Android KVM proof of concept** → **Run workflow** → branch `main`.

O workflow usa `ubuntu-latest`, habilita e verifica leitura/escrita de `/dev/kvm`, inicia Android API 35 x86_64 com aceleração obrigatória, valida ADB e boot completo, abre a tela inicial e verifica a assinatura PNG do screenshot. Limite: 20 minutos; uma execução por vez. Não depende de computador ou celular ligado após o disparo.

Em **Artifacts**, o ZIP `android-poc-<run_id>` contém o screenshot e as evidências de KVM, ADB, versão, modelo, ABIs e resultado. Retenção de um dia para minimizar armazenamento. Nenhum snapshot do Android ou cache é persistido.

## Kwai: instalação condicional

Fonte consultada: [site oficial](https://www.kwai.com/about) e [Central de Ajuda](https://www.kwai.com/pt-BR/support/app). Ambos direcionam à distribuição pelas lojas oficiais. Não foi obtido um APK direto oficial com compatibilidade x86_64 verificada. Portanto a instalação está **SKIPPED**, documentada em `kwai-status.txt`; não usamos APKs de terceiros.

A validação da infraestrutura não comprova que o Kwai aceita esse emulador, login, persistência de sessão ou automação. Esses pontos permanecem pendentes.

## Credenciais futuras

Esta versão não lê nenhum segredo. `GITHUB_TOKEN` tem somente `contents: read`; os passos não fazem checkout nem persistem credenciais Git.

Se outra etapa precisar de autenticação, configurar em **Settings → Secrets and variables → Actions → New repository secret**, nunca em arquivos, commits, issues ou variáveis públicas. Nomes reservados para futura implementação: `KWAI_SESSION_ENCRYPTION_KEY` e `KWAI_SESSION_BLOB` (nenhum valor criado). GitHub Secrets não garante sozinho que uma sessão Android possa ser restaurada; isso exige teste separado. Dados grandes de sessão não devem ser colocados em Secrets.

`.gitignore` exclui ambientes locais, cookies, credenciais, tokens, sessões, chaves, APKs, AVDs e artefatos. É uma proteção auxiliar: revisar conteúdo antes de qualquer commit. Não publicar logs/screenshot de sessões autenticadas nem compartilhar snapshots em artefatos públicos.

## Custos e escopo

[Documentação do GitHub](https://docs.github.com/en/billing/concepts/product-billing/github-actions): runners padrão em repositórios públicos têm uso gratuito. Esta PoC não usa runners maiores, serviços pagos ou assinatura. Armazenamento de artefatos possui limites próprios; o teste mantém apenas evidências pequenas por um dia. A gratuidade de um sistema completo futuro ainda não está comprovada.

Sem `schedule`, `push` ou `pull_request`: apenas execução manual autorizada. Nenhuma publicação de vídeo.
