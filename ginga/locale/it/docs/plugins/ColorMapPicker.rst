Il plugin ``ColorMapPicker`` serve a sfogliare e selezionare graficamente una
mappa colori per un visualizzatore di immagini di canale.

**Tipo di plugin: Globale o Locale**

``ColorMapPicker`` è un plugin ibrido globale/locale, il che significa che può
essere invocato in entrambi i modi.  Se invocato come plugin locale è associato
a un canale ed è possibile aprire un'istanza per ciascun canale.  Può anche
essere aperto come plugin globale.

**Uso**

Il funzionamento del plugin è molto semplice: le mappe colori sono visualizzate
sotto forma di barre di colore ed etichette nel riquadro di vista principale del
plugin.  Fai clic su una qualsiasi delle barre per impostare la mappa colori del
canale associato (se invocato come plugin locale) o del canale attualmente
attivo (se invocato come plugin globale).

Puoi scorrere verticalmente o usare le barre di scorrimento per spostarti tra i
campioni di barre di colore.

.. note:: Al primo avvio, il plugin genera un'immagine RGB bitmap di barre di
          colore ed etichette corrispondenti a tutte le mappe colori
          disponibili.  Questo può richiedere alcuni secondi a seconda del
          numero di mappe colori installate.

          Le mappe colori vengono mostrate con la mappa di intensità « ramp »
          applicata.
