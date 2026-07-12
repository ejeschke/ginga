Un plugin per generare sovrapposizioni di colore che rappresentano la
sottoesposizione e la sovraesposizione nell'immagine caricata.

**Tipo di plugin: Locale**

``Overlays`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Scegli i colori dai menu a discesa per il limite inferiore e/o superiore
(« Colore basso » e « Colore alto », rispettivamente).  Specifica i limiti per
i valori bassi e alti nelle caselle dei limiti (« Limite basso » e « Limite
alto », rispettivamente).  Imposta l'opacità delle sovrapposizioni con un valore
compreso tra 0 e 1 nella casella « Opacità ».  Infine, premi il pulsante
« Ripeti ».

La sovrapposizione di colore dovrebbe mostrare le aree sotto il limite inferiore
con un colore basso e le aree sopra il limite superiore con il colore alto.  Se
si omette un limite (casella lasciata vuota), quel colore non verrà mostrato
nella sovrapposizione.

Se viene selezionata una nuova immagine per il canale, l'immagine di
sovrapposizione verrà ricalcolata in base ai parametri attuali con i nuovi dati.
