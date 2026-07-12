Un plugin per rappresentare graficamente i valori dei pixel lungo una linea
retta che biseca un cubo.

**Tipo di plugin: Locale**

``LineProfile`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

.. warning::

   Non ci sono restrizioni su quali assi possono essere scelti.
   Di conseguenza, il grafico può essere privo di significato.

Il plugin ``LineProfile`` è usato per immagini multidimensionali (cioè 3D o
superiori).  Rappresenta i valori dei pixel alla posizione attuale del cursore
lungo l'asse selezionato; oppure, se è selezionata una regione, rappresenta la
media in ciascun fotogramma.  Questo può essere usato per creare normali profili
di riga spettrali.  Un marcatore viene posto al punto dati del fotogramma
attualmente visualizzato.

L'asse X visualizzato è costruito usando le parole chiave ``CRVAL*``,
``CDELT*``, ``CRPIX*``, ``CTYPE*`` e ``CUNIT*`` dell'intestazione FITS.  Se una
delle parole chiave non è disponibile, l'asse ripiega sui valori ``NAXIS*``.

L'asse Y visualizzato è costruito usando ``BTYPE`` e ``BUNIT``.  Se non sono
disponibili, etichetta semplicemente i valori dei pixel come « Signal ».

Per usare questo plugin:

1. Seleziona un asse.
2. Scegli un punto o disegna una regione con il cursore.
3. Usa ``MultiDim`` per cambiare i valori di passo degli assi, se applicabile.
