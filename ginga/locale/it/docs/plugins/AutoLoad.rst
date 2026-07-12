``AutoLoad`` è un semplice plugin per monitorare una cartella alla ricerca di
nuovi file e caricarli automaticamente in un canale quando compaiono.

**Tipo di plugin: Locale**

``AutoLoad`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

.. note:: Per usare questo plugin è necessario installare il pacchetto Python
          « watchdog ».

**Uso**

* Per impostare una cartella da monitorare, digita il percorso di una cartella
  (directory) nel campo « Cartella monitorata » e premi INVIO o fai clic su
  « Imposta ».
* Se devi distinguere tra i file che verranno aggiunti a questa cartella, puoi
  digitare un'espressione regolare Python nella casella « Espressione regolare »
  e fare clic su « Imposta ».  Verranno considerati solo i file i cui nomi
  corrispondono al modello.  Nota che l'espressione regolare vale solo per il
  nome del file, non per una parte del percorso della cartella.
* Se in qualsiasi momento vuoi mettere in pausa il caricamento automatico, puoi
  selezionare la casella « Sospendi caricamento automatico »; questo fermerà
  ogni caricamento automatico.  Nota che se successivamente deselezioni la
  casella, i file arrivati nel frattempo non verranno caricati.

.. note:: Il monitoraggio di cartelle che risiedono su unità di rete potrebbe
          funzionare o meno.

**Configurazione utente**
