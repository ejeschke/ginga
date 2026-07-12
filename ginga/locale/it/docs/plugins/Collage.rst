
Plugin per creare un mosaico di immagini tramite il metodo del collage.

**Tipo di plugin: Locale**

``Collage`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Questo plugin serve a creare automaticamente un collage a mosaico nel
visualizzatore di canale usando immagini fornite dall'utente.  La posizione di
un'immagine sul collage è determinata dal suo WCS senza correzione della
distorsione.  È pensato come uno strumento di visione rapida, non come un
sostituto del « drizzling » di immagini che tiene conto della distorsione
dell'immagine, ecc.

Il collage esiste solo come tracciato sulla tela di Ginga.  Non viene
effettivamente costruita alcuna nuova immagine singola (se lo desideri, vedi il
plugin « Mosaic »).  Alcuni plugin che si aspettano di operare su immagini
singole potrebbero non funzionare correttamente con un collage.

Per creare un nuovo collage, fai clic sul pulsante « Nuovo collage » e trascina
i file sulla finestra di visualizzazione (ad es. i file possono essere
trascinati dal plugin `FBrowser`).  Le immagini devono avere un WCS
funzionante.  La prima immagine elaborata verrà caricata e il suo WCS verrà
usato per orientare le altre tessere.  Puoi aggiungere nuove immagini a un
collage esistente semplicemente trascinando altri file.

**Controlli**

Il controllo « Metodo » serve a scegliere un metodo per comporre a mosaico le
immagini del collage.  Ha due valori: 'simple' e 'warp':

- 'simple' tenterà di ruotare e capovolgere le immagini secondo il WCS.  È un
  metodo veloce, a scapito della precisione.  Non gestirà le distorsioni vicino
  al bordo del campo che dovrebbero deformare l'immagine.
- 'warp' userà il WCS per spostare completamente ogni pixel dell'immagine
  secondo il WCS dell'immagine di riferimento.  Questo può lasciare pixel vuoti
  nell'immagine che vengono riempiti campionando dai pixel circostanti.  Sarà
  più lento del metodo semplice, e il tempo aumenta linearmente con la
  dimensione delle immagini.

Seleziona il pulsante « HDU del collage » per far sì che `Collage` tenti di
tracciare tutte le HDU immagine di un file trascinato invece che solo la prima
trovata.

Seleziona « Etichetta immagini » per far disegnare al plugin il nome di ciascuna
immagine su ogni tessera tracciata.

Se « Uniforma sfondo » è selezionato, lo sfondo di ciascuna tessera viene
regolato rispetto alla mediana della prima tessera tracciata (una sorta di
livellamento approssimativo).

La casella « Numero di thread » assegna quanti thread del pool di thread
verranno usati per caricare i dati.  Usare più thread di solito velocizza il
caricamento di molti file.

**Differenza rispetto al plugin `Mosaic`**

- Non alloca un grande array per contenere tutto il contenuto del mosaico
- Non è necessario specificare il FOV di uscita né preoccuparsene
- Può mostrare il risultato più velocemente (dipende un po' dalle immagini
  costituenti)
- Alcuni plugin non funzioneranno correttamente con un collage, o saranno più
  lenti
- Non può salvare il collage come file di dati (anche se puoi usare
  « ScreenShot »)

È personalizzabile usando ``~/.ginga/plugin_Collage.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Collage plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Collage.cfg"

  # Set to True when you want to collage image HDUs in a file
  collage_hdus = False

  # annotate images with their names
  annotate_images = False

  # Try to match backgrounds
  match_bg = False

  # Number of threads to devote to opening images
  num_threads = 4
