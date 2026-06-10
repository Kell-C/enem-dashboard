# Painel ENEM MS — Web Estatico

Versao web estatica do painel ENEM 2019-2024 para Mato Grosso do Sul.

## Como publicar (gratuito)

### Opcao 1: GitHub Pages (recomendada)

1. Faca push desta pasta `web/` para um repositorio GitHub.
2. Va em **Settings > Pages > Source** e selecione a pasta `/web` (ou raiz, se `web/` for a raiz do branch).
3. O site estara disponivel em `https://seu-usuario.github.io/nome-do-repo/`.

### Opcao 2: Netlify (drag & drop)

1. Acesse [netlify.com](https://netlify.com) e faca login.
2. Va em **Sites > Add new site > Deploy manually**.
3. Arraste a pasta `web/` para a area indicada.
4. Pronto — URL gerada automaticamente.

### Opcao 3: Vercel

1. Instale o CLI: `npm i -g vercel`
2. Dentro de `web/`, execute: `vercel --prod`
3. Ou importe o repositorio no [vercel.com](https://vercel.com).

### Opcao 4: Cloudflare Pages

1. Acesse [dash.cloudflare.com](https://dash.cloudflare.com) > Pages.
2. Crie um projeto e conecte ao repositorio GitHub.
3. Build settings: **None** (estatico).
4. Deploy.

## Estrutura

```
web/
  index.html          # Painel completo (HTML+CSS+JS)
  data/
    mock_data.js      # Dados em formato JS (fonte primaria)
    data.json         # Dados em formato JSON (alternativa)
```

## Atualizar os dados

Para regenerar `data.json` a partir dos parquets:

```bash
cd ..
python scripts/gerar_web_data.py
```

Isso le os parquets em `data/agregados/` e gera `web/data/data.json`.

Para usar o JSON em vez do JS, substitua no `index.html`:

```html
<!-- Antes -->
<script src="data/mock_data.js"></script>

<!-- Depois -->
<script>
fetch('data/data.json')
  .then(r=>r.json())
  .then(d=>{window.MOCK=d;});
</script>
```

Nota: o painel usa Plotly via CDN. Nenhuma dependencia local necessaria.
