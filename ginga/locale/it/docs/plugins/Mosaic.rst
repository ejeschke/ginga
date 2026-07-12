Plugin per creare un mosaico di immagini costruendo un'immagine composita.

**Tipo di plugin: Locale**

``Mosaic`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

.. warning:: Questo può richiedere molta memoria.

Questo plugin serve a costruire automaticamente un'immagine mosaico nel canale
usando immagini fornite dall'utente (ad es. usando ``FBrowser``).
La posizione di un'immagine nel mosaico è determinata dal suo WCS senza
correzione della distorsione.  È pensato come uno strumento di visione rapida,
non come un sostituto del « drizzling » di immagini che tiene conto della
distorsione dell'immagine, ecc.  Il mosaico esiste solo in memoria, ma puoi
salvarlo in un file FITS usando ``SaveImage``.

Quando un mosaico esce dalla memoria, non è più accessibile in Ginga.  Per
evitarlo, devi configurare la sessione in modo che la cache dati di Ginga sia
sufficientemente grande (vedi « Customizing Ginga » nel manuale).

Per creare un nuovo mosaico, imposta il FOV e trascina i file sulla finestra di
visualizzazione.  Le immagini devono avere un WCS funzionante.  Il WCS della
prima immagine verrà usato per orientare le altre tessere.

**Differenza rispetto al plugin `Collage`**

- Alloca un unico grande array per contenere tutto il contenuto del mosaico
- Più lento da costruire, ma può essere più rapido da manipolare per grandi
  immagini risultanti
- Può salvare il mosaico come un nuovo file di dati
- Riempie i valori tra le tessere con un valore di riempimento (può essere
  `NaN`)
