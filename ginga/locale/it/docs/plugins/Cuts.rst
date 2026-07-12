
Un plugin per generare un grafico dei valori lungo una linea o un percorso.

**Tipo di plugin: Locale**

``Cuts`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

``Cuts`` traccia un semplice grafico dei valori dei pixel rispetto all'indice per
una linea tracciata attraverso l'immagine.  È possibile tracciare più tagli.

Sono disponibili quattro tipi di tagli: line, path, freepath e beziercurve:

* Il taglio « line » è una linea retta tra due punti.
* Il taglio « path » viene disegnato come un poligono aperto, con segmenti
  rettilinei tra i punti.
* Il taglio « freepath » è come un taglio path, ma disegnato con un tratto a mano
  libera che segue il movimento del cursore.
* Il percorso « beziercurve » è una curva di Bézier cubica.

Se una nuova immagine viene aggiunta al canale mentre il plugin è attivo, esso
si aggiornerà con i nuovi tagli calcolati sulla nuova immagine.

Se l'impostazione « enable slit » è abilitata, questo plugin consentirà anche la
funzionalità di immagine a fenditura (per immagini multidimensionali) tramite
una scheda « Slit ».  Nell'interfaccia della scheda, seleziona un asse
dall'elenco « Axes » e disegna una linea.  Questo creerà un'immagine 2D che
assume che i primi due assi siano spaziali e indicizza i dati lungo l'asse
selezionato.  Proprio come ``Cuts``, puoi visualizzare le altre immagini a
fenditura usando la casella a discesa di selezione del taglio.

**Disegnare i tagli**

Il menu « New Cut Type » ti consente di scegliere che tipo di taglio disegnerai.

Scegli « New Cut » dal menu a discesa « Cut » se vuoi disegnare un nuovo taglio.
Altrimenti, se è selezionato un particolare taglio denominato, questo verrà
sostituito da qualsiasi taglio appena disegnato.

Mentre disegni un taglio path o beziercurve, premi « v » per aggiungere un
vertice, o « z » per rimuovere l'ultimo vertice aggiunto.

**Scorciatoie da tastiera**

Mentre passi il cursore, premi « h » per un taglio orizzontale completo e « j »
per un taglio verticale completo.

**Eliminare i tagli**

Per eliminare un taglio, seleziona il suo nome dal menu a discesa « Cut » e fai
clic sul pulsante « Elimina ».  Per eliminare tutti i tagli, premi « Elimina
tutto ».

**Modificare i tagli**

Usando la funzione di modifica della tela, è possibile aggiungere nuovi vertici
a un percorso esistente e spostare i vertici.  Fai clic sul pulsante di opzione
« Modifica » per mettere la tela in modalità modifica.  Se un taglio non viene
selezionato automaticamente, ora puoi selezionare la linea, il percorso o la
curva facendo clic su di essa, il che dovrebbe abilitare i punti di controllo
alle estremità o ai vertici -- puoi trascinarli.  Per aggiungere un nuovo
vertice a un percorso, passa con cura il cursore sulla linea dove vuoi il nuovo
vertice e premi « v ».  Per eliminare un vertice, passa il cursore su di esso e
premi « z ».

Noterai un punto di controllo extra per la maggior parte degli oggetti, che ha
un centro di colore diverso -- questo è un punto di controllo di movimento per
spostare l'intero oggetto sull'immagine quando si è in modalità modifica.

Puoi anche selezionare « Sposta » per spostare semplicemente un taglio senza
modificarlo.

**Cambiare la larghezza dei tagli**

La larghezza dei tagli « line » può essere cambiata usando il menu « Width
Type »:

* « none » indica un taglio di raggio zero; cioè mostrando solo i valori dei
  pixel lungo la linea
* « x » traccerà la somma dei valori lungo l'asse X ortogonale al taglio.
* « y » traccerà la somma dei valori lungo l'asse Y ortogonale al taglio.
* « perpendicular » traccerà la somma dei valori lungo un asse perpendicolare al
  taglio.

Il « Width radius » controlla la larghezza della sommatoria ortogonale di una
quantità su ciascun lato del taglio -- 1 sarebbe 3 pixel, 2 sarebbe 5 pixel,
ecc.

**Salvare i tagli**

Usa il pulsante « Salva » per salvare il grafico di ``Cuts`` come immagine e i
dati come archivio Numpy compresso.

**Copiare i tagli**

Per copiare un taglio, seleziona il suo nome dal menu a discesa « Cut » e fai
clic sul pulsante « Copia taglio ».  Ne verrà creato un nuovo taglio.  Puoi poi
manipolare il nuovo taglio in modo indipendente.

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_Cuts.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # Cuts plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_Cuts.cfg"

  # If set to True will always select a cut after drawing it
  select_new_cut = True

  # If set to True will automatically change to "move" mode after draw
  draw_then_move = True

  # If set to True will label cuts with a text annotation
  label_cuts = True

  # If set to True will add a legend to the cuts plot
  show_cuts_legend = False

  # If set to True will add Slit tab
  enable_slit = False

  # Default cut colors
  colors = ['magenta', 'skyblue2', 'chartreuse2', 'cyan', 'pink', 'burlywood2', 'yellow3', 'turquoise', 'coral1', 'mediumpurple2']

  # If set to True, will update graph continuously as cursor is dragged
  # around image
  drag_update = False
