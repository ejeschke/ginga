Das Plugin ``SAMP`` implementiert eine SAMP-Schnittstelle für den
Ginga-Referenzbetrachter.

.. note:: Um dieses Plugin auszuführen, müssen Sie ``astropy`` mit dem
          Modul ``samp`` installieren.

**Plugin-Typ: Global**

``SAMP`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Ginga enthält ein Plugin zur Aktivierung der Unterstützung von SAMP (Simple
Applications Messaging Protocol).  Mit SAMP-Unterstützung kann Ginga gesteuert
werden und mit anderen astronomischen Desktop-Anwendungen zusammenarbeiten.

Das Modul ``SAMP`` wird standardmäßig nicht gestartet.  Um es beim Start von
Ginga zu starten, geben Sie die Befehlszeilenoption an::

        --modules=SAMP

Andernfalls starten Sie es über „SAMP starten“ im Menü „Plugins“.

Derzeit ist die SAMP-Unterstützung auf ``image.load.fits``-Nachrichten
beschränkt, das heißt, Ginga lädt eine FITS-Datei, wenn es eine dieser
Nachrichten empfängt.

Gingas Plugin ``SAMP`` verwendet das Modul ``astropy.samp``, daher müssen Sie
``astropy`` installiert haben, um das Plugin zu verwenden.  Standardmäßig
versucht Gingas ``SAMP``-Plugin, einen SAMP-Hub zu starten, falls keiner läuft.
