Visualizza l'output di registro del visualizzatore di riferimento.

**Tipo di plugin: Globale**

``Log`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Il plugin ``Log`` costruisce un'interfaccia che include un grande widget di
testo scorrevole che mostra l'output attivo del logger.  L'output più recente
compare in basso.  Questo può essere utile per la risoluzione dei problemi.

Ci sono quattro controlli:

* La casella combinata in basso a sinistra permette di scegliere il livello di
  registrazione desiderato.  I quattro livelli, in ordine di verbosità, sono:
  « debug », « info », « warn » ed « error ».
* La casella con il numero in basso a destra permette di impostare quante righe
  di input conservare nel buffer di visualizzazione (ad es. conservare solo le
  ultime 1000 righe).
* La casella « Scorrimento automatico », se selezionata, fa scorrere il grande
  widget di testo fino alla fine man mano che vengono aggiunti nuovi messaggi
  di registro.  Deselezionala se desideri consultare e studiare i messaggi più
  vecchi.
* Il pulsante « Cancella » serve a cancellare il widget di testo, in modo che
  compaia solo la registrazione nuova.
