
Il plugin ``RC`` implementa un'interfaccia di controllo remoto per il
visualizzatore Ginga.

**Tipo di plugin: Globale**

``RC`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Il plugin ``RC`` (Remote Control) offre un modo per controllare Ginga da remoto
tramite l'uso di un'interfaccia XML-RPC.  Avvia il plugin dal menu « Plugins »
(invoca « Start RC ») o lancia ginga con l'opzione da riga di comando
``--modules=RC`` per avviarlo automaticamente.

Per impostazione predefinita, il plugin si avvia con il server in esecuzione
sulla porta 11771 associato all'interfaccia localhost -- questo consente
connessioni solo dall'host locale.  Se vuoi cambiare questo, imposta l'host e la
porta nel controllo « Set Addr » e premi ``Enter`` -- dovresti vedere
l'indirizzo aggiornarsi nel campo di visualizzazione « Addr: ».

Nota che la parte host (prima dei due punti) non indica *da quale* host vuoi
consentire l'accesso, ma a quale interfaccia associarsi.  Se vuoi consentire a
qualsiasi host di connettersi, lasciala vuota (ma includi i due punti e il
numero di porta) per consentire al server di associarsi a tutte le interfacce.
Premi « Restart » per riavviare quindi il server al nuovo indirizzo.

Una volta avviato il plugin, puoi usare lo script ``ggrc`` (incluso quando
``ginga`` è installato) per controllare Ginga.  Dai un'occhiata allo script se
vuoi vedere come scrivere la tua interfaccia programmatica.

Mostrare un esempio d'uso::

        $ ggrc help

Mostrare l'aiuto per un metodo Ginga specifico::

        $ ggrc help ginga <method>

Mostrare l'aiuto per un metodo di canale specifico::

        $ ggrc help channel <chname> <method>

I metodi di Ginga (shell del visualizzatore) possono essere chiamati così::

        $ ggrc ginga <method> <arg1> <arg2> ...

I metodi per canale possono essere chiamati così::

        $ ggrc channel <chname> <method> <arg1> <arg2> ...

Le chiamate possono essere fatte da un host remoto aggiungendo le opzioni::

        --host=<hostname> --port=11771

(Nella GUI del plugin, assicurati di rimuovere il prefisso « localhost »
dall'« addr », ma lascia i due punti e la porta.)

**Esempi**

Creare un nuovo canale::

        $ ggrc ginga add_channel FOO

Caricare un file::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits

Caricare un file in un canale specifico::

        $ ggrc ginga load_file /home/eric/testdata/SPCAM/SUPA01118797.fits FOO

Livelli di taglio::

        $ ggrc channel FOO cut_levels 163 1300

Livelli di taglio automatici::

        $ ggrc channel FOO auto_levels

Ingrandire a un livello specifico::

        $ ggrc -- channel FOO zoom_to -7

(Nota l'uso di ``--`` per consentirci di passare un parametro che inizia con
``-``.)

Ingrandire per adattare::

        $ ggrc channel FOO zoom_fit

Trasformare (gli argomenti sono una tripletta booleana: ``flipx`` ``flipy``
``swapxy``)::

        $ ggrc channel FOO transform 1 0 1

Ruotare::

        $ ggrc channel FOO rotate 37.5

Cambiare la mappa dei colori::

        $ ggrc channel FOO set_color_map rainbow3

Cambiare l'algoritmo di distribuzione dei colori::

        $ ggrc channel FOO set_color_algorithm log

Cambiare la mappa di intensità::

        $ ggrc channel FOO set_intensity_map neg

In alcuni casi, potresti dover ricorrere a escape di shell per poter passare
certi caratteri a Ginga.  Ad esempio, un trattino iniziale viene di solito
interpretato come un'opzione del programma.  Per passare un intero con segno,
potresti dover fare qualcosa come::

        $ ggrc -- channel FOO zoom -7

**Interfacciarsi dall'interno di Python**

È anche possibile controllare Ginga in modalità RC dall'interno di Python.
Quanto segue descrive una parte delle funzionalità.

*Connettersi*

Prima, lancia Ginga e avvia il plugin ``RC``.  Questo può essere fatto dalla
riga di comando::

        ginga --modules=RC

Dall'interno di Python, connettiti con un oggetto ``RemoteClient`` come segue::

        from ginga.util import grc
        host = 'localhost'
        port = grc.default_rc_port
        viewer = grc.RemoteClient(host, port)

Questo oggetto viewer è ora collegato a Ginga usando ``RC``.

*Caricare un'immagine*

Puoi caricare un'immagine dalla memoria in un canale a tua scelta.  Prima,
connettiti a un canale::

        ch = viewer.channel('Image')

Poi, carica un'immagine Numpy (cioè un qualsiasi ``ndarray`` 2D)::

        import numpy as np
        img = np.random.rand(500, 500) * 10000.0
        ch.load_np('Image_Name', img, 'fits', {})

L'immagine verrà visualizzata in Ginga e potrà essere manipolata come al solito.

*Sovrapporre un oggetto della tela*

È possibile aggiungere oggetti alla tela in un dato canale.  Prima, connettiti::

        canvas = viewer.canvas('Image')

Questo si connette al canale chiamato « Image ».  Puoi cancellare gli oggetti
disegnati nella tela::

        canvas.clear()

Puoi anche aggiungere qualsiasi oggetto di base della tela.  Il punto chiave da
tenere a mente è che gli oggetti in ingresso devono passare attraverso il
protocollo XMLRC.  Questo significa tipi di dati semplici (``float``, ``int``,
``list`` o ``str``); niente array.  Ecco un esempio per tracciare una linea
attraverso una serie di punti definiti da due array Numpy::

        x = np.arange(100)
        y = np.sqrt(x)
        points = list(zip(x.tolist(), y.tolist()))
        canvas.add('path', points, color='red')

Questo disegnerà una linea rossa sull'immagine.
