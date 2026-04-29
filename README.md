# CLI Converter

Collezione di utility CLI per conversione e trasformazione di file multimediali:

- `img2webp`: PNG/JPG -> WebP
- `heic2jpg`: HEIC/HEIF -> JPEG
- `pdf2jpeg`: PDF -> JPEG, con rendering pagine o estrazione immagini incorporate
- `pdfcompress`: compressione PDF
- `rmbg`: rimozione di sfondi a tinta unita
- `vid2audio`: estrazione audio da file video

Il repository espone piu eseguibili indipendenti tramite `pyproject.toml`.

## Requisiti

- Python `>=3.10,<3.13`
- `ffmpeg` e `ffprobe` nel `PATH` per `vid2audio`

Dipendenze Python principali:

- `typer`
- `rich`
- `Pillow`
- `pillow-heif`
- `PyMuPDF`
- `numpy`
- `scipy`

## Installazione

Con `pip` in editable mode:

```bash
pip install -e .
```

Oppure con `poetry`:

```bash
poetry install
```

Dopo l'installazione avrai questi comandi:

```bash
img2webp
heic2jpg
pdf2jpeg
pdfcompress
rmbg
vid2audio
```

## Convenzioni CLI

- I tool con un solo comando si invocano direttamente, senza subcommand:
  - `img2webp`
  - `heic2jpg`
  - `pdfcompress`
  - `rmbg`
- I tool con piu modalita usano subcommand:
  - `pdf2jpeg pages`
  - `pdf2jpeg extract`
  - `vid2audio extract`
  - `vid2audio info`
- Quasi tutti i tool accettano uno o piu file oppure directory.
- Quando un tool supporta `-r/--recursive`, la scansione entra nelle sottocartelle.
- Quando un tool supporta `--dry-run`, mostra i file che verrebbero processati senza scrivere output.
- Tutti i comandi Typer espongono `--help`. I comandi root espongono anche `--install-completion` e `--show-completion`.

## Tool

## `img2webp`

Converte immagini `PNG`, `JPG`, `JPEG` in formato `WebP`.

Input supportati:

```text
.png .jpg .jpeg
```

Output:

- estensione sempre `.webp`
- nome file basato sullo stem originale
- output nella stessa directory del sorgente, salvo `--output`

Uso base:

```bash
img2webp INPUT [INPUT ...] [opzioni]
```

Opzioni:

- `inputs`: uno o piu file o directory
- `-o, --output PATH`: directory di destinazione
- `-q, --quality INTEGER`: qualita WebP lossy da `1` a `100`, default `80`
- `--lossless`: abilita compressione WebP lossless
- `-W, --width INTEGER`: ridimensiona alla larghezza indicata
- `-H, --height INTEGER`: ridimensiona all'altezza indicata
- `-m, --max-size INTEGER`: riduce proporzionalmente finche il lato lungo e `<= max-size`; ha priorita su `--width/--height`
- `--strip-metadata / --keep-metadata`: rimuove o conserva i metadata Exif/XMP; di default li rimuove
- `-r, --recursive`: scansione ricorsiva delle directory
- `--dry-run`: anteprima senza scrittura file

Note operative:

- Se specifichi solo `--width` o solo `--height`, il rapporto d'aspetto viene preservato.
- Se specifichi sia `--width` sia `--height`, il resize forza esattamente quelle dimensioni.
- Se `--lossless` e attivo, `--quality` viene ignorato.
- Le immagini con trasparenza vengono salvate come WebP mantenendo il canale alpha.

Esempi:

```bash
# Conversione base
img2webp photo.jpg

# Qualita piu aggressiva
img2webp hero.png --quality 65

# WebP lossless
img2webp logo.png --lossless

# Resize sul lato lungo a 1600 px
img2webp ./assets --max-size 1600 -r

# Output centralizzato e metadata conservati
img2webp img1.jpg img2.png -o ./out --keep-metadata

# Anteprima batch senza scrivere file
img2webp ./catalog -r --dry-run
```

## `heic2jpg`

Converte immagini `HEIC` e `HEIF` in `JPEG`.

Input supportati:

```text
.heic .heif
```

Output:

- estensione `.jpg`
- stesso nome base del file sorgente
- stessa directory del sorgente, salvo `--output`

Uso base:

```bash
heic2jpg INPUT [INPUT ...] [opzioni]
```

Opzioni:

- `inputs`: uno o piu file o directory
- `-o, --output PATH`: directory di destinazione
- `-q, --quality INTEGER`: qualita JPEG da `1` a `100`, default `92`
- `--strip-metadata / --keep-metadata`: rimuove o conserva i metadata Exif; di default li rimuove
- `-r, --recursive`: scansione ricorsiva
- `--overwrite`: sovrascrive output `.jpg` gia esistenti
- `--dry-run`: anteprima senza scrittura file

Note operative:

- L'orientamento Exif viene normalizzato prima del salvataggio.
- Senza `--overwrite`, il comando fallisce sul file se l'output esiste gia.

Esempi:

```bash
# Conversione singola
heic2jpg IMG_0001.HEIC

# Batch ricorsivo in una cartella dedicata
heic2jpg ./iphone-export -r -o ./jpg

# JPEG ad alta qualita con metadata conservati
heic2jpg portrait.heif --quality 96 --keep-metadata

# Sovrascrittura esplicita di file gia generati
heic2jpg ./shots --overwrite -r

# Dry run
heic2jpg ./incoming -r --dry-run
```

## `pdf2jpeg`

Converte PDF in JPEG con due modalita diverse:

- `pages`: renderizza le pagine del PDF
- `extract`: estrae le immagini raster incorporate nel PDF

Input supportati:

```text
.pdf
```

### `pdf2jpeg pages`

Renderizza ogni pagina come immagine JPEG.

Output:

- PDF a pagina singola: `nomefile.jpg`
- PDF multipagina: `nomefile_p0001.jpg`, `nomefile_p0002.jpg`, ...
- se l'output non e specificato:
  - PDF singolo output nella stessa cartella del PDF
  - PDF multipagina output in una sottocartella con il nome del PDF

Uso:

```bash
pdf2jpeg pages INPUT [INPUT ...] [opzioni]
```

Opzioni:

- `inputs`: uno o piu PDF o directory
- `-o, --output PATH`: directory di destinazione
- `-q, --quality INTEGER`: qualita JPEG `1..100`, default `85`
- `-d, --dpi INTEGER`: DPI di rendering, da `36` a `600`, default `200`
- `-f, --from INTEGER`: prima pagina da renderizzare, indice `1-based`
- `-t, --to INTEGER`: ultima pagina da renderizzare, inclusiva, `1-based`
- `-W, --width INTEGER`: resize alla larghezza indicata
- `-H, --height INTEGER`: resize all'altezza indicata
- `-m, --max-size INTEGER`: downscale del lato lungo, prioritario rispetto a `--width/--height`
- `--strip-metadata / --keep-metadata`: rimuove o conserva metadata Exif; di default li rimuove
- `-r, --recursive`: scansione ricorsiva
- `--dry-run`: anteprima senza scrittura file

Esempi:

```bash
# Render completo del PDF
pdf2jpeg pages report.pdf

# Solo un intervallo di pagine
pdf2jpeg pages manual.pdf --from 10 --to 25

# DPI piu alti per qualita di stampa
pdf2jpeg pages brochure.pdf --dpi 300 --quality 92

# Downscale lato lungo e output centralizzato
pdf2jpeg pages ./pdf -r --max-size 1800 -o ./jpeg-pages

# Dry run
pdf2jpeg pages ./archive -r --dry-run
```

### `pdf2jpeg extract`

Estrae immagini raster gia presenti nel PDF e le salva come JPEG.

Output:

- PDF con una sola immagine utile: `nomefile.jpg`
- PDF con piu immagini: `nomefile_img0001.jpg`, `nomefile_img0002.jpg`, ...
- se l'output non e specificato:
  - immagine singola nella stessa cartella del PDF
  - immagini multiple in una sottocartella con il nome del PDF

Opzioni:

- `inputs`: uno o piu PDF o directory
- `-o, --output PATH`: directory di destinazione
- `-q, --quality INTEGER`: qualita JPEG `1..100`, default `85`
- `--min-width INTEGER`: scarta immagini incorporate piu strette di questa soglia
- `--min-height INTEGER`: scarta immagini incorporate piu basse di questa soglia
- `-W, --width INTEGER`: resize alla larghezza indicata
- `-H, --height INTEGER`: resize all'altezza indicata
- `-m, --max-size INTEGER`: downscale del lato lungo, prioritario rispetto a `--width/--height`
- `--strip-metadata / --keep-metadata`: rimuove o conserva metadata Exif; di default li rimuove
- `-r, --recursive`: scansione ricorsiva
- `--dry-run`: anteprima senza scrittura file

Note operative:

- Le immagini duplicate vengono deduplicate in base al loro `xref` nel PDF.
- Questa modalita e utile quando vuoi estrarre asset esistenti senza renderizzare l'intera pagina.

Esempi:

```bash
# Estrai tutte le immagini incorporate
pdf2jpeg extract catalog.pdf

# Filtra icone o miniature troppo piccole
pdf2jpeg extract scan.pdf --min-width 500 --min-height 500

# Ridimensiona gli asset estratti e salva in una cartella comune
pdf2jpeg extract ./docs -r --max-size 1600 -o ./jpeg-assets

# Dry run
pdf2jpeg extract ./docs -r --dry-run
```

## `pdfcompress`

Comprime PDF riscrivendo le immagini incorporate con una qualita selezionabile e salvando un nuovo file ottimizzato.

Input supportati:

```text
.pdf
```

Output:

- nome file: `nomefile_compressed.pdf`
- stessa cartella del sorgente, salvo `--output`

Uso base:

```bash
pdfcompress INPUT [INPUT ...] [opzioni]
```

Opzioni:

- `inputs`: uno o piu PDF o directory
- `-o, --output PATH`: directory di destinazione
- `-q, --quality INTEGER`: qualita immagini incorporate da `1` a `100`, default `75`
- `-r, --recursive`: scansione ricorsiva
- `--overwrite`: sovrascrive PDF compressi gia esistenti
- `--dry-run`: anteprima senza scrittura file

Note operative:

- Il tool salva sempre un nuovo PDF, non modifica il file sorgente in-place.
- Oltre alla ricompressione delle immagini usa salvataggio con cleanup e stream compression aggressivi.
- Su PDF gia ottimizzati il guadagno puo essere minimo o nullo.

Esempi:

```bash
# Compressione standard
pdfcompress report.pdf

# Compressione piu spinta
pdfcompress scans.pdf --quality 45

# Batch ricorsivo con output dedicato
pdfcompress ./pdf -r -o ./compressed

# Rigenera anche file gia presenti
pdfcompress ./pdf --overwrite -r

# Dry run
pdfcompress ./pdf -r --dry-run
```

## `rmbg`

Rimuove uno sfondo a tinta unita da un'immagine e genera un `PNG` con trasparenza.

Input supportati:

```text
.png .jpg .jpeg .bmp .tiff .tif .webp
```

Output:

- formato sempre `.png`
- suffix di default `_nobg`
- nome file di default: `nomefile_nobg.png`
- stessa cartella del sorgente, salvo `--output`

Uso base:

```bash
rmbg INPUT [INPUT ...] [opzioni]
```

Opzioni:

- `inputs`: uno o piu file o directory
- `-o, --output PATH`: directory di destinazione
- `-c, --color TEXT`: colore dello sfondo da rimuovere; accetta `#RRGGBB`, `RRGGBB` o `R,G,B`
- `-t, --tolerance INTEGER`: soglia distanza colore da `0` a `442`, default `30`
- `-f, --feather INTEGER`: blur gaussiano sul canale alpha per bordi piu morbidi, default `0`
- `--invert`: inverte la selezione; mantiene lo sfondo e rimuove il resto
- `-e, --edges-only`: rimuove solo lo sfondo connesso ai bordi dell'immagine
- `--crop`: ritaglia i bordi completamente trasparenti
- `-s, --suffix TEXT`: suffix del file output, default `_nobg`
- `-r, --recursive`: scansione ricorsiva
- `--dry-run`: anteprima senza scrittura file

Note operative:

- `tolerance=0` rimuove solo il match cromatico esatto.
- Valori piu alti allargano la selezione a sfumature vicine.
- `--edges-only` usa una flood fill a 4-connettivita e preserva regioni interne dello stesso colore non collegate ai bordi.
- `--invert` e utile per ottenere una maschera inversa o isolare il background.
- `--crop` taglia automaticamente i margini diventati trasparenti.

Esempi:

```bash
# Rimuovi sfondo bianco con tolleranza di default
rmbg logo.png

# Sfondo nero, tolleranza alta per catturare ombre
rmbg icon.png --color "#000000" --tolerance 80

# Colore espresso come RGB decimale
rmbg diagram.png --color "240,240,240" --tolerance 20

# Bordi morbidi con feathering di 3 px
rmbg photo.png --color "#FFFFFF" --tolerance 40 --feather 3

# Rimuovi solo sfondo connesso ai bordi
rmbg logo.png --edges-only

# Inverti: tieni solo lo sfondo, rimuovi il soggetto
rmbg photo.png --invert

# Crop automatico dei bordi trasparenti
rmbg icon.png --crop

# Batch ricorsivo, output centralizzato, suffix custom
rmbg ./assets -r -o ./transparent --suffix "_clean"

# Anteprima batch
rmbg ./assets -r --dry-run
```

## `vid2audio`

Estrae l'audio dai video oppure mostra i metadati dello stream audio.

Input supportati:

```text
.mp4 .mkv .avi .mov .webm .flv .wmv .m4v .ts .mpg .mpeg
```

Formati audio supportati in estrazione:

- `mp3`
- `aac`
- `opus`
- `flac`
- `wav`
- `ogg`
- `copy`

### `vid2audio extract`

Estrae la traccia audio con transcodifica oppure stream copy.

Output:

- nome file basato sul video sorgente
- estensione determinata dal formato richiesto
- con `--format copy` l'estensione viene dedotta dal codec audio sorgente; fallback `.mka`

Uso:

```bash
vid2audio extract INPUT [INPUT ...] [opzioni]
```

Opzioni:

- `inputs`: uno o piu file video o directory
- `-o, --output PATH`: directory di destinazione
- `-f, --format TEXT`: formato output, default `mp3`; valori ammessi `mp3`, `aac`, `opus`, `flac`, `wav`, `ogg`, `copy`
- `-b, --bitrate TEXT`: bitrate audio, esempio `192k`, `320k`; ignorato con `copy`
- `-s, --sample-rate INTEGER`: sample rate in Hz; ignorato con `copy`
- `-c, --channels INTEGER`: numero canali, da `1` a `8`; ignorato con `copy`
- `-v, --volume FLOAT`: moltiplicatore volume, esempio `1.5`, `0.5`; ignorato con `copy`
- `-ss, --start TEXT`: offset iniziale, in secondi o `HH:MM:SS`
- `-t, --duration TEXT`: durata da estrarre, in secondi o `HH:MM:SS`
- `-y, --overwrite`: sovrascrive file audio esistenti
- `-r, --recursive`: scansione ricorsiva
- `--dry-run`: anteprima senza scrittura file

Note operative:

- `copy` evita ricodifica quando possibile e copia direttamente il flusso audio.
- `--start` e `--duration` permettono di ritagliare un segmento senza processare l'intero video.
- Il comando richiede `ffmpeg` e `ffprobe` disponibili nel `PATH`.

Esempi:

```bash
# Estrazione base in MP3
vid2audio extract interview.mp4

# AAC a bitrate esplicito
vid2audio extract webinar.mov --format aac --bitrate 192k

# FLAC con sample rate e stereo forzato
vid2audio extract concert.mkv --format flac --sample-rate 48000 --channels 2

# Solo un segmento del video
vid2audio extract lesson.mp4 --start 00:10:00 --duration 00:02:30

# Copia diretta dello stream audio senza ricodifica
vid2audio extract source.mp4 --format copy

# Batch ricorsivo in cartella dedicata
vid2audio extract ./videos -r -o ./audio --format mp3 --bitrate 160k

# Dry run
vid2audio extract ./videos -r --dry-run
```

### `vid2audio info`

Mostra i metadati del primo stream audio trovato nel file video.

Campi riportati:

- codec
- sample rate
- canali
- bitrate
- durata

Uso:

```bash
vid2audio info INPUT [INPUT ...]
```

Esempi:

```bash
# Ispeziona un singolo file
vid2audio info movie.mp4

# Confronta piu file in una tabella unica
vid2audio info a.mp4 b.mkv c.mov
```

## Output e naming

Riepilogo rapido dei nomi generati:

- `img2webp`: `file.webp`
- `heic2jpg`: `file.jpg`
- `pdf2jpeg pages`: `file.jpg` oppure `file_p0001.jpg`
- `pdf2jpeg extract`: `file.jpg` oppure `file_img0001.jpg`
- `pdfcompress`: `file_compressed.pdf`
- `rmbg`: `file_nobg.png` oppure `file<SUFFIX>.png`
- `vid2audio extract`: `file.ext` in base al formato scelto

## Suggerimenti d'uso

- Usa `--dry-run` quando lavori su directory grandi o batch ricorsivi.
- Usa `--output` per centralizzare l'output ed evitare file sparsi accanto ai sorgenti.
- Usa `--overwrite` solo quando vuoi rigenerare output esistenti in modo esplicito.
- Per `rmbg`, parti da una `--tolerance` bassa e aumentala gradualmente.
- Per `pdf2jpeg`, scegli `pages` se ti serve la pagina renderizzata; scegli `extract` se vuoi recuperare gli asset originali incorporati.
- Per `vid2audio`, usa `--format copy` quando vuoi velocita e nessuna perdita dovuta a ricodifica.
