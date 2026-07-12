Ein Plugin zur Anzeige eines einfachen Diagramms für zwei beliebige ausgewählte
Spalten einer Tabelle.

**Plugin-Typ: Lokal**

``PlotTable`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Es ist kein Singleton, das heißt, für jeden Kanal können mehrere Instanzen
geöffnet werden.

**Verwendung**

``PlotTable`` ist ein Plugin, das zwei beliebige ausgewählte Spalten eines
gegebenen FITS-Tabellen-HDU darstellt (erreichbar über ``MultiDim``).
Bei maskierten Spalten werden maskierte Daten nicht angezeigt (auch wenn nur
einer der Werte des Paares ``(X, Y)`` maskiert ist).
Es ist als Möglichkeit gedacht, Tabellendaten schnell zu betrachten, und nicht
für eine detaillierte wissenschaftliche Analyse.
