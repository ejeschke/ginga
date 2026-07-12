
``Histogram`` traccia un istogramma per una regione disegnata nell'immagine, o
per l'intera immagine.

**Tipo di plugin: Locale**

``Histogram`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

Fai clic e trascina per definire una regione all'interno dell'immagine che verrà
usata per calcolare l'istogramma.  Per prendere l'istogramma dell'immagine
intera, fai clic sul pulsante nell'interfaccia etichettato « Immagine intera ».

.. note:: A seconda della dimensione dell'immagine, calcolare l'istogramma
          completo può richiedere tempo.

Se viene selezionata una nuova immagine per il canale, il grafico
dell'istogramma verrà ricalcolato in base ai parametri attuali con i nuovi dati.

A meno che non sia disabilitato nel file di impostazioni del plugin
dell'istogramma, viene calcolata una riga di semplici statistiche per il
riquadro e mostrata in una riga sotto il grafico.

**Controlli dell'interfaccia**

Tre pulsanti di opzione nella parte inferiore dell'interfaccia servono a
controllare gli effetti dell'azione clic/trascina:

* seleziona « Sposta » per trascinare la regione in una posizione diversa
* seleziona « Disegna » per disegnare una nuova regione
* seleziona « Modifica » per modificare la regione

Per fare un grafico logaritmico dell'istogramma, seleziona la casella
« Istogramma log ».  Per tracciare secondo l'intero intervallo di valori
dell'immagine invece che secondo l'intervallo entro i valori di taglio,
deseleziona la casella « Traccia per tagli ».

Il parametro « NumBins » determina quanti contenitori vengono usati nel calcolo
dell'istogramma.  Digita un numero nella casella e premi « Invio » per cambiare
il valore predefinito.

**Controlli pratici dei livelli di taglio**

Poiché un istogramma è un utile riscontro per impostare i livelli di taglio,
nell'interfaccia sono forniti controlli per impostare i livelli di taglio basso
e alto nell'immagine, oltre che per eseguire livelli di taglio automatici,
secondo le impostazioni dei livelli di taglio automatici nelle preferenze del
canale.

Puoi impostare i livelli di taglio facendo clic nel grafico dell'istogramma:

* clic sinistro: imposta il taglio basso
* clic centrale: reimposta (livelli di taglio automatici)
* clic destro: imposta il taglio alto

Inoltre, puoi regolare dinamicamente il divario tra i tagli basso e alto
scorrendo la rotellina nel grafico (cioè la « larghezza » della curva del
grafico dell'istogramma).  Questo ha l'effetto di aumentare o diminuire il
contrasto nell'immagine.  La quantità che viene cambiata a ogni clic della
rotellina è impostata dall'impostazione ``scroll_pct`` del file di
configurazione del plugin.  Il valore predefinito è 10 %.

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_Histogram.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Histogram plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Histogram.cfg"

  # Switch to "move" mode after selection
  draw_then_move = True

  # Number of bins for histogram
  num_bins = 2048

  # Histogram color
  hist_color = 'aquamarine'

  # Calculate extra statistics on box
  show_stats = True

  # Controls formatting (width) of statistics numbers
  maxdigits = 7

  # percentage to adjust cuts gap when scrolling in histogram
  scroll_pct = 0.10
