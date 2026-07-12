Il plugin ``LoaderConfig`` permette di configurare gli strumenti di apertura
file che possono essere usati per caricare vari contenuti in Ginga.

Gli strumenti di apertura registrati sono associati a tipi MIME di file, e per
un singolo tipo MIME possono esserci più strumenti di apertura.  Una priorità
associata a un abbinamento tipo MIME/strumento determina quale strumento verrà
usato per ciascun tipo: il valore di priorità più basso determinerà quale
strumento verrà usato.  Se c'è più di uno strumento con la stessa bassa
priorità, all'utente verrà chiesto quale strumento usare quando apre un file in
Ginga.  Questo plugin può essere usato per impostare le preferenze degli
strumenti di apertura e salvarle nell'area di configurazione $HOME/.ginga
dell'utente.

**Tipo di plugin: Globale**

``LoaderConfig`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Dopo aver avviato il plugin, la visualizzazione mostrerà tutti i tipi MIME
registrati e gli strumenti di apertura registrati per quei tipi, con una
priorità associata a ciascun abbinamento tipo MIME/strumento.

Seleziona una o più righe e digita una priorità per esse nella casella
etichettata « Priorità: »; premi « Imposta » (o INVIO) per impostare la priorità
di quegli elementi.

.. note:: Più basso è il numero, più alta è la priorità.  I numeri negativi
          vanno bene e la priorità predefinita di un caricatore è di solito 0.
          Quindi, ad esempio, se ci sono due caricatori disponibili per un tipo
          MIME e una priorità è impostata a -1 e l'altra a 0, verrà usato quello
          con -1 senza chiedere all'utente di scegliere.


Fai clic su « Salva » per salvare le priorità in
$HOME/.ginga/loaders.json in modo che vengano ricaricate e usate ai successivi
riavvii del programma.
