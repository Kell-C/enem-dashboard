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

## Abrir localmente (Windows)

**Nao abra `index.html` com duplo-clique.** O Chrome bloqueia `file://` e os dados nao carregam.

1. Duplo-clique em **`abrir_painel.bat`** nesta pasta.
2. O navegador abre em `http://127.0.0.1:8765/index.html`.

Alternativa manual (PowerShell na pasta `web/`):

```powershell
python -m http.server 8765
```

Depois acesse `http://127.0.0.1:8765/index.html`.

## Estrutura

```
web/
  index.html          # Painel completo (HTML+CSS+JS)
  data/
    painel_data.js    # Dados reais em JS (fonte primaria do site)
    data.json         # Mesmos dados em JSON (alternativa)
```

## Atualizar os dados

Para regenerar agregados e `data.json` (filtros INEP corrigidos):

```bash
cd scripts
python gerar_agregados.py
python gerar_web_data.py
```

- `gerar_agregados.py` lê `enem_completo_2019_2024_.parquet` + planilha SED → `data/agregados/*.parquet`
- `gerar_web_data.py` exporta `web/data/data.json` e `web/data/painel_data.js`

**Filtros:** concluintes SED (denominador); presentes 2 dias; eliminados = `TP_PRESENCA=2` ou `TP_STATUS_REDACAO=2`; redação em branco (4) **incluída**.

Para usar o JSON em vez do JS, substitua no `index.html`:

```html
<!-- Padrao -->
<script src="data/painel_data.js"></script>

<!-- Alternativa JSON -->
<script>
fetch('data/data.json')
  .then(r=>r.json())
  .then(d=>{window.PAINEL_DATA=d;});
</script>
```

Nota: o painel usa Plotly via CDN. Nenhuma dependencia local necessaria.
