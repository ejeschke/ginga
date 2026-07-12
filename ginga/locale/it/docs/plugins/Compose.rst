
Un plugin per comporre immagini RGB da immagini monocromatiche costituenti.

**Tipo di plugin: Locale**

``Compose`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Avvia il plugin ``Compose`` dal menu « Operation->RGB » (in basso) o
« Plugins->RGB » (in alto).  La scheda dovrebbe comparire sotto la scheda
« Dialogs » nel visualizzatore a destra come « IMAGE:Compose ».

1. Seleziona il tipo di composizione che vuoi realizzare dal menu a discesa
   « Compose Type »: « RGB » per comporre tre immagini monocromatiche in
   un'immagine a colori, « Alpha » per comporre una serie di immagini come
   livelli con valori alfa diversi per ciascun livello.
2. Premi « Nuova immagine » per iniziare a comporre una nuova immagine.

***Per la composizione RGB***

1. Trascina le tue tre immagini costituenti che formeranno i piani R, G e B
   nella finestra « Preview » -- trascinale nell'ordine R (rosso), G (verde) e B
   (blu).  In alternativa, puoi caricare le immagini nel visualizzatore di
   canale una alla volta e, dopo ciascuna, premere « Inserisci da canale »
   (allo stesso modo, fallo nell'ordine R, G e B).

Nell'interfaccia del plugin, le immagini R, G e B dovrebbero comparire come tre
controlli a cursore nell'area « Layers » del plugin, e l'anteprima dovrebbe
mostrare una versione a bassa risoluzione di come appare l'immagine composita
con i cursori impostati.

.. figure:: figures/compose-rgb.png
   :width: 800px
   :align: center
   :alt: Composizione di un'immagine RGB

   Composizione di un'immagine RGB.

2. Gioca con i livelli alfa di ciascun livello usando i cursori nel plugin
   ``Compose``; man mano che regoli un cursore, l'immagine di anteprima
   dovrebbe aggiornarsi.
3. Quando vedi qualcosa che ti piace, puoi salvarlo in un file usando il
   pulsante « Salva con nome » (usa « jpeg » o « png » come estensione del
   file), oppure inserirlo nel canale usando il pulsante « Salva nel canale ».

***Per la composizione Alpha***

Per la composizione di tipo Alpha le immagini vengono semplicemente combinate
nell'ordine mostrato nella pila, con il livello 0 come livello inferiore e i
livelli successivi impilati sopra.  Il livello alfa di ciascun livello è
regolabile tramite un cursore nello stesso modo descritto sopra.

.. figure:: figures/compose-alpha.png
   :width: 800px
   :align: center
   :alt: Composizione Alpha di un'immagine

   Composizione Alpha di un'immagine.

1. Trascina le tue N immagini costituenti che formeranno i livelli nella
   finestra « Preview », oppure carica le immagini nel visualizzatore di canale
   una alla volta e, dopo ciascuna, premi « Inserisci da canale » (la prima
   immagine sarà in fondo alla pila -- livello 0).
2. Gioca con i livelli alfa di ciascun livello usando i cursori nel plugin
   ``Compose``; man mano che regoli un cursore, l'immagine di anteprima
   dovrebbe aggiornarsi.
3. Quando vedi qualcosa che ti piace, puoi salvarlo in un file usando il
   pulsante « Salva con nome » (usa « fits » come estensione del file), oppure
   inserirlo nel canale usando il pulsante « Salva nel canale ».

***Note generali***

- La finestra di anteprima è semplicemente un widget ginga, quindi si applicano
  tutte le associazioni consuete; puoi impostare mappe di colore, livelli di
  taglio, ecc. con le associazioni di mouse e tastiera.
