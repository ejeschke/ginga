``Ruler`` è un semplice plugin progettato per misurare distanze su un'immagine.

**Tipo di plugin: Locale**

``Ruler`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

``Ruler`` misura la distanza calcolando una triangolazione sferica tramite la
mappatura WCS di tre punti definiti da un'unica linea tracciata sull'immagine.
Per impostazione predefinita, la distanza è mostrata in minuti d'arco di cielo,
ma usando il controllo « Unità », può essere cambiata per mostrare gradi o
distanza in pixel.

Fai clic e trascina per stabilire un righello tra due punti.  Quando termini
l'operazione di disegno, il righello è stabilito e l'interfaccia del plugin si
aggiorna per mostrare dettagli sulla linea, incluse le posizioni degli estremi e
l'angolo della linea.  Le unità dell'angolo possono essere commutate tra gradi e
radianti usando la casella a discesa adiacente.

Per cancellare il vecchio righello e crearne uno nuovo, fai clic e trascina di
nuovo.  Quando viene tracciata un'altra linea, questa sostituisce la prima.
Quando il plugin viene chiuso, la sovrapposizione grafica viene rimossa.  Se
desideri « righelli persistenti », usa il plugin ``Drawing`` (e scegli « Ruler »
come tipo di disegno).

**Modifica**

Per modificare un righello esistente, fai clic sul pulsante di opzione
nell'interfaccia del plugin etichettato « Modifica ».  Se il righello non viene
selezionato immediatamente, fai clic sulla diagonale che collega i due punti.
Questo dovrebbe stabilire un riquadro di delimitazione attorno al righello e
mostrarne i punti di controllo.  Trascina all'interno del riquadro di
delimitazione per spostare il righello, oppure fai clic e trascina gli estremi
per modificare il righello.  Il righello può anche essere scalato o ruotato
usando quei punti di controllo.

**Interfaccia**

Le unità mostrate per la distanza possono essere selezionate dalla casella a
discesa nell'interfaccia.  Puoi scegliere tra « arcmin », « degrees » o
« pixels ».  Le prime due richiedono un WCS valido e funzionante nell'immagine.

I valori degli estremi sono mostrati nell'interfaccia, ma possono inoltre essere
mostrati nel grafico del righello se la casella « Mostra estremi » è attivata.
Verranno mostrate linee a piombo se la casella « Mostra piombo » è attivata.

**Pulsanti**

Il pulsante « Sposta all'origine » sposterà l'immagine principale all'origine
della linea tracciata, mentre « Sposta alla destinazione » si sposterà alla
fine.  « Sposta al centro » imposta la posizione di spostamento sul punto
centrale della linea.  Questi pulsanti possono essere utili per il lavoro
ravvicinato e ingrandito sull'immagine.  « Cancella » cancella il righello
dall'immagine.

**Suggerimenti**
Apri il plugin « Zoom » per vedere con precisione i dettagli dell'area del
cursore.  Il plugin « Pick » può anche essere usato insieme a Ruler per
identificare il punto centrale di un oggetto, quando si allinea l'una o l'altra
estremità del righello.
