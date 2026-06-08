# wwdc2026.biolatti.it — copertura autonoma dell'Apple WWDC 2026

Sito statico che si aggiorna **da solo ogni ora** durante il WWDC 2026 (8-12 giugno),
senza bisogno del Mac acceso o di Cowork aperto. Stesso impianto editoriale del progetto
Google I/O 2026, ma con lo scheduler spostato su **GitHub Actions** e l'intelligenza
(ricerca + scrittura IT/EN) dentro uno script che chiama l'**API Claude con web search**.

## Come funziona

```
GitHub Actions (cron orario, gratis)
   -> update_news.py   = API Claude + web_search -> trova SOLO annunci nuovi, IT+EN
   -> dedup + build.py = rigenera il sito statico
   -> git commit/push
   -> Vercel (Hobby, gratis) = auto-deploy a ogni push -> wwdc2026.biolatti.it
   -> notifica Telegram quando pubblica qualcosa di nuovo
```

Modello di supervisione: **ibrido**. Pubblica diretto + ti avvisa su Telegram a ogni
aggiornamento. La revisione critica la facciamo insieme in Cowork quando ci sei e a
evento concluso (fase 2, vedi sotto).

Lo script si **auto-limita alla finestra evento** (fino al 12 giugno 23:59 + 12h di
grazia per i follow-up): fuori finestra esce subito senza fare nulla.

---

## Cosa serve da te (azioni manuali, una tantum)

Questi sono i passaggi che io non posso fare al posto tuo perche richiedono i tuoi
account. In ordine.

### 1. Repo GitHub
Crea un repo (anche privato) su GitHub, es. `wwdc2026-biolatti`, e carica il contenuto
di questa cartella (`wwdc-2026/`). Da terminale:

```bash
cd "wwdc-2026"
git init && git add -A && git commit -m "WWDC 2026 site - scaffold"
git branch -M main
git remote add origin https://github.com/<tuo-utente>/wwdc2026-biolatti.git
git push -u origin main
```

### 2. Secret e variabili del repo
Su GitHub: **Settings > Secrets and variables > Actions**.

Secrets (Repository secrets):
- `ANTHROPIC_API_KEY` — una API key da console.anthropic.com (Settings > API Keys).
- `TELEGRAM_BOT_TOKEN` — puoi **riusare il bot di "Un Mondo Che Cambia"** o crearne uno
  nuovo con @BotFather.
- `TELEGRAM_CHAT_ID` — l'ID della chat/canale dove vuoi le notifiche (il tuo chat id
  personale va benissimo).

Variabile opzionale (tab "Variables", non "Secrets"):
- `WWDC_MODEL` — modello da usare. Se non la imposti, default `claude-sonnet-4-6`.

### 3. Collega il repo a Vercel
Su vercel.com: **Add New > Project > Import** il repo GitHub.
- Framework Preset: **Other**
- Build Command: **vuoto** (lascialo disattivato / "Override" off)
- Output Directory: **`.`** (la root: serviamo HTML gia generato)
- Deploy.

Da qui in poi ogni push fatto dal workflow rideploya in automatico.

### 4. Sottodominio wwdc2026.biolatti.it
- In Vercel, nel progetto: **Settings > Domains > Add** -> `wwdc2026.biolatti.it`.
  Vercel ti mostra il record DNS da creare (di solito un **CNAME** verso
  `cname.vercel-dns.com`).
- Nel pannello DNS di **TopHost** (dove e gestito biolatti.it) aggiungi quel CNAME:
  host `wwdc2026`, valore quello indicato da Vercel.
- Attendi la propagazione (di solito pochi minuti, fino a un'ora).

### 5. Primo run e accensione
- Vai su **Actions > "WWDC 2026 hourly update" > Run workflow** per un primo run manuale
  di prova (puoi farlo anche prima del keynote: troverà 0 annunci ed uscirà pulito).
- Dopo il keynote (lunedi 8 ore 19:00) il cron orario inizia a popolare il sito.
- **Dopo il 13 giugno**: disattiva il workflow da **Actions > ... > Disable workflow**
  (non e strettamente necessario, lo script esce comunque subito, ma evita run inutili).

---

## Fase 2 — revisione finale e riclusterizzazione

A evento concluso, come per I/O, facciamo insieme in Cowork:
1. verifica copertura: controllo che non manchino annunci principali;
2. riclusterizzazione: rilettura di macro-aree e tag alla luce di cio che e stato
   davvero annunciato (gli intro in `intros_data.py` sono scritti in forma neutra,
   pronti a essere riscritti sui contenuti reali);
3. pagine pillar: scrittura di `analisi` (sostituendo il placeholder in
   `build.py` / `analisi/01-riepilogo-tematico.md`) e `top-10` (popolando
   `topStories` e `featuredStories` in `data/news.json`);
4. idee di diffusione: carousel LinkedIn, PDF, podcast NotebookLM, post social.

---

## Costi
- GitHub Actions: gratis (ampiamente entro i minuti free).
- Vercel: gratis (piano Hobby).
- API Claude: a consumo. Web search $10 ogni 1000 ricerche + token. Su una settimana
  di run orari parliamo di pochi dollari in tutto.

## Comandi locali utili
```bash
python3 build.py                 # rigenera il sito da data/news.json
WWDC_FORCE=1 ANTHROPIC_API_KEY=sk-... python3 update_news.py   # test reale di un run
```

## Struttura
- `build.py` — generatore statico (config evento + LABELS in cima al file).
- `intros_data.py` — intro narrativi di macro-aree e tag.
- `data/news.json` — unico data store (item, macro-aree, tag, featured, topStories).
- `update_news.py` — script autonomo del run orario.
- `.github/workflows/hourly-update.yml` — scheduler + commit + notifica.
- `assets/` — CSS, JS, favicon (le illustrazioni hero verranno eventualmente aggiunte in fase 2).
