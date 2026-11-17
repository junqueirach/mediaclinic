# =============================================================================
# help_es.py — the Help in Spanish                                   ### NEW v0.20.0 UI1e ###
# Generated from the English Help (help_text.py): the same 13 topics in the same order, the same markup line by
# line (help_text.py explains the markup).  The self-test checks the parity, the markup and that every app label
# the Help must name appears exactly as the app shows it in Spanish.
# Brand, format and file names, [[keys]] and XML tags stay as in English.
# =============================================================================
TAB_01 = """
# Primeros pasos

## Qué hace esta app
Metadata & MediaClinic audita y repara bibliotecas de películas de Kodi, Jellyfin, Emby y Plex. Lee las carpetas de su biblioteca, revisa cada archivo de imagen, archivo de metadatos y video, y muestra una tabla de estado con colores, para que vea de un vistazo lo que falta o está dañado. La mayoría de los problemas se pueden corregir desde la misma tabla.

## Cómo es una carpeta de película
Una carpeta = una película. Una carpeta completa contiene:
- el video, p. ej. **Movie Name (2001).mkv** (o .mp4, .avi …)
- los metadatos de Kodi, **<video>.nfo** o **movie.nfo**
- **movie.xml**, un formato antiguo (opcional): solo lo lee el plugin XML de Emby, y Media Center Master lo escribe; Kodi, Jellyfin y Plex no lo leen
- **poster.jpg** (vertical, 2:3) y **fanart.jpg** (horizontal, 16:9)
- **folder.jpg**, una copia idéntica del póster (opcional: Plex, Jellyfin, Emby e Infuse leen poster.jpg, y Kodi el nombre propio del póster)
- imágenes de fondo adicionales: **backdrop.jpg**, **backdrop1.jpg** … o las **<video>-fanart1.jpg** … de Kodi
- subtítulos externos como **Movie Name.pt.srt** (opcional)
La pestaña Servidores multimedia lista todos los nombres que leen los servidores.

## Primer uso
1. Haga clic en **Examinar…** y elija la carpeta de sus películas. Agregue más carpetas después con **Bibliotecas…**.
2. Haga clic en **Full Scan** ([[F5]]). La tabla se llena por fases: carpetas, imágenes, metadatos y luego video — con FFprobe cuando el interruptor **FFprobe** de la barra de estado está activado.
3. Cada fila muestra el estado de una película: verde = ninguna regla activada, amarillo = advertencias, rojo = errores.
4. Seleccione una película: el panel de la derecha muestra su póster, sus problemas con un botón **Corregir** cada uno, sus archivos y las acciones comunes.
5. El último scan se guarda y se restaura en el siguiente inicio.
6. En el primer inicio una ventana pregunta el idioma, la carpeta de sus películas, **¿Qué programas reproducen sus películas?** (marque todos los que usa; no marcar ninguno también vale), la exigencia (Estricto, Medio, Fácil) y FFprobe (opcional: no viene incluido ni se descarga por usted; **Elegir carpeta…** o **Página de descarga**). Solo **Empezar** guarda las respuestas; cerrar la ventana la hace volver en el siguiente inicio. Elija primero el idioma: **Reiniciar ahora** muestra la ventana otra vez en ese idioma. Quien actualiza desde una versión anterior ve solo la pregunta de los programas, una vez, con **Ahora no**. Los programas marcados definen el **modo de estado**: decide qué archivos revisa y repara MediaClinic.
- **Kodi, Plex, Jellyfin, Emby, Infuse** (solo NFO; Plex no lee el NFO, solo el arte — vea abajo): los archivos .nfo, tal como los crean tinyMediaManager, Radarr o MediaElch. movie.xml se ignora (no se lee, no se revisa, no se escribe; no hay columna .xml).
- **Uno de ellos + MediaBrowser / Media Center Master** (NFO y movie.xml): el NFO y movie.xml, todas las revisiones y correcciones de ambos.
- **Solo MediaBrowser / Media Center Master** (solo movie.xml): solo movie.xml. El NFO se ignora (no se lee, no se revisa, nunca se escribe; no hay columna .nfo). Título, año, calificación, IDs y géneros vienen de movie.xml, y las correcciones escriben movie.xml. Las colecciones, Renombrar NFO para Kodi y la corrección de **&** trabajan sobre el NFO, por eso no se ofrecen.
Cámbielo después en **Configuración → Reglas de estado → ¿Qué programas reproducen sus películas?**: marque todos los programas que usa (Kodi, Plex, Jellyfin, Emby, Infuse, MediaBrowser / Media Center Master). Las marcas definen el modo de estado, y la línea debajo muestra los archivos revisados y los nombres que escribe una corrección: un nombre que lee cada programa marcado: <video>.nfo, <video>-poster.jpg y <video>-fanart.jpg, los nombres que recomienda Kodi, que funcionan con cualquier configuración de Kodi y que leen todos los demás programas (movie.nfo y poster.jpg solo funcionan en Kodi con la opción de la fuente "Movies are in separate folders that match the movie title"). Una carpeta cuyos nombres lee cada programa marcado los conserva. Nada marcado mantiene el modo como estaba y los nombres de cada carpeta. La lectura no cambia: todo nombre que aceptan estos programas se sigue leyendo. Una biblioteca que reproducen otros programas tiene su propia elección en **Bibliotecas… → Programas…** (reemplaza la marca **Solo NFO** de esa biblioteca). Cambiar entre NFO y movie.xml ofrece un nuevo scan.
7. En el modo **NFO y movie.xml**, una biblioteca en la que ninguna película tiene movie.xml recibe una pregunta más después de su scan: **¿Biblioteca solo con NFO?** **Sí, solo NFO** desactiva las revisiones de XML solo para esa biblioteca (sin error "Falta el archivo XML", sin comparación NFO / XML; la columna XML muestra —). Cámbielo después en **Bibliotecas…** con el botón **Solo NFO**.

## Lista de inicio rápido
- **Configuración → Editor y FFmpeg**: indique la carpeta de FFmpeg (análisis de video y extracción de imágenes de fondo).
- **Configuración → Claves de API**: agregue las claves de TMDB y OMDb (calificaciones, búsqueda y revisión de IDs, imágenes); una clave de fanart.tv agrega más pósteres e imágenes de fondo.
- **Configuración → Idioma**: el idioma de destino de la columna Idioma (por defecto PT). El idioma de la propia app está en **Configuración → Interfaz → Idioma de la interfaz** (English, Português (Brasil), Español o Igual que Windows; **Reiniciar ahora** reinicia en él).
- **Configuración → Reglas de estado**: elija qué cuenta como error o como advertencia. Un **Perfil de estado** (Fácil / Medio / Estricto) las define todas a la vez; un usuario nuevo empieza con Estricto.
- Para priorizar: ordene por **Estado** (Errores primero), haga clic en el contador **Errores** o marque **Solo problemas**.

## Íconos de estado
| ⬤ | OK — presente y válido
| ◐ | advertencia — conflicto, proporciones incorrectas, un problema menor
| ○ | falta
| ✕ | error — imagen dañada, error de XML, valor ilegible
| — | no se usa — movie.xml en una biblioteca solo con NFO, o el archivo que el modo de estado no usa

## Archivos que escribe la app
| settings.json | toda la configuración (%APPDATA%\\MediaMetadataClinic)
| last_results.json | el último scan, restaurado al iniciar (misma carpeta)
| ffprobe_cache.json | resultados de FFprobe recordados (misma carpeta)
| fanarttv_cache.json | respuestas de fanart.tv, guardadas 7 días (sin la clave dentro)
| collections_cache.json | las colecciones de TMDB (nombres en todos los idiomas)
| last_ignored.json | las carpetas que el último scan no agregó como películas (el informe de carpetas ignoradas)
| not_duplicates.json | sus respuestas "No es duplicado"
| no_collection.json | las películas que marcó "fuera de toda colección"
| backup_cleanup_log.json | las copias de seguridad que eliminó la limpieza por tamaño (Copias de seguridad las lista)
| logs/app.log | el registro junto al programa; las claves de API nunca se escriben en él (**Ayuda → Abrir la carpeta de registros**)
| backup/ | las copias de seguridad automáticas (misma carpeta; movidas allí una vez desde la carpeta del programa — una actualización las conserva)
"""

TAB_02 = """
# La ventana y la tabla

## La ventana
- **El encabezado** (arriba): las partes **Películas** y **Series**, **Copias de seguridad / Deshacer…**, **Configuración ▾**, **Ayuda ▾** y **Acerca de**. La compatibilidad con series llega en la v0.22; la parte Series muestra lo previsto y las carpetas que el último scan no agregó.
- **La barra de herramientas de Películas**: **Bibliotecas…**, **Examinar…**, el cuadro de bibliotecas, **Full Scan**, **Quick Scan**, **Herramientas ▾**, **Exportar…** y **•••** (**Borrar todo…**, **Guardar resultados del scan…**, **Abrir resultados del scan…**).
- **La fila de orden**, el cuadro **Filtro** y la leyenda de colores, luego la tabla.
- **El panel de la película seleccionada** a la derecha de la tabla (siguiente sección).
- **La barra de estado** (abajo): los contadores (haga clic en **Errores** o **Advertencias** para mostrar solo esas filas), el número de seleccionadas, la última acción y el interruptor **FFmpeg ✓ | FFprobe**.

## El panel de la película seleccionada
Seleccione una película y el panel muestra su póster, año, géneros, calificación, biblioteca y una insignia de estado; luego **PROBLEMAS** (cada motivo de estado), **CORRECCIONES** (cada problema corregible con su botón **Corregir**), **ARCHIVOS** (NFO, XML, póster, carpeta, fanart, video: ✓ o ✕) y **ACCIONES** (**Abrir carpeta**, **Editar NFO**, **Obtener póster/carpeta…**, **Buscar fuentes**, **Actualizar**). **Todas las acciones ▾** abre el menú completo del clic derecho.
- Varias películas seleccionadas: "N películas seleccionadas", las acciones que funcionan con varias y las correcciones con cuántas películas tienen cada problema.
- Una fila de colección (vista agrupada) muestra el panel de la colección (pestaña Colecciones).
- **Ocultar ›** o [[Ctrl+B]] oculta el panel; la franja fina **‹** del borde derecho lo muestra de nuevo. Arrastre el divisor para cambiar su ancho; un doble clic en el divisor lo restablece. Ambos se recuerdan.

## Columnas
| Película | NFO <title>, luego XML <LocalTitle>, los títulos originales, el nombre de la carpeta. Al pasar el puntero: la carpeta, su biblioteca, la fecha de ingreso y cada motivo de estado. El doble clic abre la carpeta. Una película en varias partes (Pelicula-CD1.mkv + Pelicula-CD2.mkv) se muestra como "Nombre — Parte 1 + Parte 2"; solo cambia lo que se ve, no los archivos.
| Año | NFO <year> o XML <ProductionYear>.
| Géneros | etiquetas <genre> del NFO; si el NFO no tiene ninguna, <Genres> del XML (la descripción emergente indica la fuente).
| Calificación | NFO <rating> (o el bloque <ratings> de Kodi), XML <IMDBrating> / <Rating>. Al pasar el puntero: valor, votos, fuente.
| Votos | NFO <votes>, XML <Votes> / <VoteCount>.
| Fuente | los IDs de IMDb y TMDB de cada etiqueta: ⬤ todos coinciden, ◐ parcial o en conflicto, ○ faltan, ✕ algunas etiquetas llenas y otras vacías. Al pasar el puntero se ve el último resultado de Verificar IDs; el doble clic abre IMDb o TMDB.
| Póster, Carpeta, Fanart | estado y nivel de calidad de cada imagen (pestaña Imágenes).
| Fondos | el número de imágenes de fondo; al pasar el puntero: su tamaño promedio.
| .nfo / .xml | el estado del archivo de metadatos. Al pasar el puntero se listan los errores con la línea y los nombres de etiqueta (los 5 primeros); el doble clic abre el archivo en su editor. El modo de estado oculta la columna del archivo que no usa (.xml para Kodi, Jellyfin, Emby…; .nfo para solo movie.xml); — significa que no se usa (una biblioteca solo con NFO).
| Idioma | el <Language> de nivel superior de movie.xml: el idioma para descargar metadatos. Sin movie.xml: el <language> de nivel superior del NFO (el mismo significado); si no, el idioma de la primera pista de audio. La descripción emergente indica la fuente. Vacío es normal.
| Video, Tamaño, Calidad | contenedor, tamaño y clase de resolución.
| Audio | pistas de audio de FFprobe, p. ej. EN (5.1), PT (2.0).
| ¿Idioma OK? | S / N: el idioma de destino en el audio o los subtítulos (el encabezado muestra el código, p. ej. "¿PT OK?").
| Subtítulos | pistas integradas (FFprobe) y archivos externos.
| Biblioteca | la biblioteca (carpeta raíz). Oculta por defecto.
| Colección | la colección de la película (NFO <set>). Oculta por defecto.
**Herramientas → Elegir columnas…** muestra u oculta columnas; la elección se guarda. Arrastre el borde de un encabezado para cambiar el ancho de una columna, haga doble clic en un encabezado para ajustarla, o use **↔ Ajustar columnas**. **↺ Anchos iniciales** devuelve cada columna a su ancho original cuando un cambio de ancho salió mal. En la vista agrupada la columna Año se ensancha para los años de una colección ("1979–1986") y recupera su ancho cuando desagrupa. Los anchos y los tamaños y posiciones de las ventanas se recuerdan.

## Filtro
Escriba en el cuadro **Filtro** ([[Ctrl+F]]) para conservar las películas cuyo nombre, año, género, idioma, calidad, estado, motivo de estado o colección coincide — "fondo" lista todos los problemas de imágenes de fondo. [[Esc]] lo borra.
- **Solo problemas** oculta las filas verdes.
- El cuadro de bibliotecas junto a **Bibliotecas…** muestra una biblioteca o todas.
- "n de m mostradas" cuenta las películas que conserva el filtro.

## Ordenar
La fila de orden dice "Ordenar por [columna] [dirección]"; **+ luego por** agrega hasta dos niveles más (✕ quita uno). La dirección se dice en palabras — A → Z, Más nuevas primero, Mayor → menor, Peores primero, Errores primero … — haga clic en ella para invertirla.
- Se puede usar cualquier columna, además de **Estado** y **Número de problemas** (las dos primeras entradas) y **Fecha de ingreso** (NFO <dateadded>, XML <DateAdded>; si no, la fecha de creación del video o de la carpeta).
- Haga clic en el encabezado de una columna para ordenar por ella (otra vez = al revés); Shift+clic la agrega como siguiente nivel. ▲1 / ▼2 en los encabezados muestran los niveles.
- Los valores vacíos (sin calificación, sin póster, sin fecha) van al final, salvo que un nivel pida los vacíos primero (el ajuste Metadatos faltantes lo hace); los valores iguales quedan en el orden de Película.
- **★ Ajustes guardados ▾**: Problemas primero, Peores imágenes primero, Metadatos faltantes, Mejor calificadas, Archivos más grandes, Por biblioteca, Por nombre de colección (colección A → Z, luego año, luego nombre de la película; las películas sin colección al final), y los suyos (**Guardar el orden actual…**; renómbrelos o elimínelos en el mismo menú). [[Ctrl+1]] … [[Ctrl+9]] aplican los ajustes 1 a 9.
- **↺ Actualizar vista** vuelve a ordenar y filtrar, para que las películas que acaba de corregir pasen a su lugar.
- El orden se conserva después de un scan y de un reinicio.

## Duplicados
Las películas que comparten un ID de IMDb, un ID de TMDB o título + año son un "Posible duplicado" (el mismo título + año con dos IDs de IMDb distintos no lo son: una nueva versión o una homónima). Clic derecho → **✔ No es duplicado…** guarda su respuesta en not_duplicates.json, para que la advertencia no vuelva; una tercera copia nueva se sigue detectando. **↺ Deshacer 'no es duplicado'** lo revierte; **Herramientas → Administrar marcas 'No es duplicado'…** lista cada par. **Herramientas → Informe de películas duplicadas** las lista todas.
"""

TAB_03 = """
# Scans y bibliotecas

## Scans
| Full Scan | vuelve a leer todas las películas de las bibliotecas incluidas ([[F5]]).
| Quick Scan | lee solo las películas agregadas, quitadas o cambiadas desde el último scan (cuenta un NFO, una imagen, un subtítulo o una carpeta de disco cambiados).
| Interruptor FFprobe | en la barra de estado: activado, los scans también leen la resolución del video, las pistas de audio y los subtítulos integrados. Un scan sin FFprobe conserva los datos de FFprobe anteriores.
| Cancelar / Esc | detiene un scan en curso; se conservan las películas leídas hasta ese momento.
Un scan nunca escribe en sus archivos. Mientras se ejecuta, las acciones que cambian archivos lo esperan (la barra de estado lo indica).

## Bibliotecas
Puede hacer el scan de varias carpetas raíz. **Examinar…** agrega una carpeta; **Bibliotecas…** las agrega, quita y ordena. Cuando la lista cambia, la app ofrece Full Scan, Quick Scan o Ahora no. **Activa / apagada** apaga una biblioteca sin quitarla: no se hace su scan (su disco no se toca) y sus películas salen de la tabla y de los contadores, pero se conservan; activada otra vez, vuelven al instante (un Quick Scan las actualiza). La parte de la carpeta de colecciones fija la carpeta de la que Kodi lee el arte de las colecciones: **Elegir…**, **Crear…** (crea "Sets" junto a la primera biblioteca, tras un sí) o **Quitar**. Los scans nunca la listan como película ni como carpeta ignorada.
- Todas las bibliotecas comparten una tabla; la columna **Biblioteca** y la descripción emergente de Película muestran dónde está una película.
- El cuadro de bibliotecas elige qué muestra la tabla y qué cubren los scans ("Todas las bibliotecas" o una de ellas).
- Una biblioteca a la que no se puede acceder (una carpeta de red desconectada) conserva su último scan, los scans la omiten y se muestra como "(sin conexión)". Una carpeta de película que no se puede leer por un momento conserva su fila, marcada "(no leído)".
- Los duplicados se buscan entre bibliotecas.
- Las películas pueden estar más adentro: se busca en una carpeta que solo contiene otras carpetas (Single Movies / HD / <movie>, Boxsets / <saga> / <movie>), hasta 5 niveles por debajo de la biblioteca. Cada película conserva su biblioteca en la columna Biblioteca.

## Carpetas ignoradas
Un scan agrega una fila solo para carpetas de películas. Estas no se agregan:
- Series de TV: tvshow.nfo, carpetas Season o archivos de episodios (S01E02, 1x02). La compatibilidad con series llega en la v0.22.
- Carpetas de carpetas 5 niveles por debajo de la biblioteca: sus películas estarían más adentro de lo que mira el scan (5 niveles). La fila indica qué tan profunda está la carpeta; agréguela como biblioteca para incluir sus películas.
- Carpetas con varios videos separados: dé a cada película su propia carpeta.
- Carpetas sin video, NFO ni XML, carpetas del sistema ($RECYCLE.BIN, @eaDir …) y carpetas que no se pudieron leer.
Una carpeta con metadatos de película es siempre una película, y también lo es una carpeta con un video y sin NFO. Después de un scan se abre la ventana **Carpetas ignoradas en el último scan…** cuando algo quedó fuera (filtrar, ordenar, doble clic para abrir, **Exportar a TXT…**, **Copiar todo**); desactívela con "Mostrar esta ventana después de un scan". **Herramientas → Carpetas ignoradas en el último scan…** la abre en cualquier momento.

## Actualizar películas sueltas
Clic derecho → **Actualizar (sin FFprobe)** ([[Ctrl+R]]) vuelve a leer la película o la selección; **Actualizar (con FFprobe)** ([[Ctrl+Shift+R]]) también analiza el video (una película: una línea de estado; varias: una ventana de progreso con Cancelar). Después de cada reparación, sincronización, descarga o eliminación, las filas afectadas se actualizan solas.

## Películas que desaparecen
Cuando se eliminó una carpeta de película, Actualizar o la actualización automática quita su fila. Clic derecho → **Quitar de la lista** quita filas sin tocar ningún archivo; el siguiente scan devuelve las películas que aún existen.

## Guardar y cargar scans
- El último scan se guarda en last_results.json y se carga en segundo plano al iniciar ("⏳ Cargando el último scan…"); las reglas de estado se aplican de nuevo, así que las reglas cambiadas nunca dejan motivos antiguos.
- **••• → Guardar resultados del scan…** / **Abrir resultados del scan…** escriben un scan en un archivo o cargan uno.
- **••• → Borrar todo…** ([[Ctrl+L]]) vacía la tabla (pregunta antes). Ningún archivo de película cambia; el último scan guardado también se vacía, así que las filas no vuelven en el siguiente inicio.
"""

TAB_04 = """
# Estado y corrección de problemas

## Cómo funciona el estado
Cada condición que puede poner una fila en rojo (errores) o en amarillo (advertencias) es una regla en **Configuración → Reglas de estado**, con una casilla y a veces un nivel o un umbral. **Herramientas → Recalcular el estado (sin nuevo scan)** aplica de inmediato las reglas cambiadas (también se hace en cada inicio).
- Pase el puntero sobre Película para ver cada motivo de una película; el panel de la película seleccionada también los lista.
- **Herramientas → Informe de estado — Todas las películas** los escribe todos, con los problemas más comunes primero y las películas cuya colección no se revisó en línea.
- **Herramientas → Revisar mejoras — Todas las películas…** lista metadatos que podrían ser mejores (pares de etiquetas de **Configuración → NFO / XML**, tamaños de archivo).
- **Herramientas → Estadísticas de la biblioteca**: estado, calidad, géneros, décadas, bibliotecas.

## Corregir problemas
El menú del clic derecho empieza con el nombre de la película (o "N películas seleccionadas") y su número de problemas, luego **⚠ Corregir problemas**: los problemas reales de la selección, cada uno vinculado a la acción que lo corrige — con varias películas, cuántas películas tienen cada problema (la acción se ejecuta solo en esas). El panel de la película seleccionada tiene la misma lista como botones **Corregir**.
| Falta póster / folder.jpg | Obtener póster/carpeta…
| Falta fanart | Obtener fanart…
| Pocas imágenes de fondo / pequeñas | Obtener imágenes de fondo…
| Proporciones / tamaño de imagen | Corregir proporciones / tamaño de imagen…
| folder.jpg difiere del póster | Copiar poster.jpg → folder.jpg
| Errores en el NFO / XML | mostrar los errores (cada error con su línea)
| El título local difiere (NFO ↔ XML) | Igualar los títulos…
| Colección faltante / diferente | Corregir colección… (pestaña Colecciones)
| Falta la carpeta / las imágenes de la colección | Imágenes de la colección… (una colección) o Crear carpeta de colección… (varias)
| Posible duplicado | No es duplicado…
| Calidad de video por debajo del mínimo | necesita una mejor copia del video (sin corrección automática)
| NFO con el nombre de la carpeta | Renombrar NFO para Kodi…
| Falta ID de IMDb / TMDB | Buscar fuentes…
| IDs en un solo archivo / en conflicto | Normalizar fuentes
| IDs no verificados / película equivocada | Verificar IDs de IMDb/TMDB
| Calificación / votos faltantes o incorrectos | Sincronizar calificaciones
| Pista / idioma de audio | Subtítulos…
| Falta el idioma de subtítulos | Subtítulos incrustados en la imagen…
| La Reparación automática puede corregir más | Reparación automática

## El menú del clic derecho
También [[Shift+F10]] o la tecla Menú, en la fila seleccionada. Una acción que no aplica queda en su lugar, en gris, con el motivo ("falta", "solo una película" …).
- **Repetir**: la última acción de nuevo en la selección actual (Configuración → Interfaz puede ocultar esta línea).
- **Abrir carpeta** ([[Ctrl+O]]), **Reproducir video**, **Editar NFO** ([[Ctrl+E]]).
- **Imágenes**: abrir las imágenes — la entrada nombra el archivo encontrado, p. ej. **Abrir poster.jpg**, **Abrir folder.jpg**, **Abrir fanart.jpg** (**Abrir póster** en gris cuando no hay ninguno o hay varias películas seleccionadas); **Obtener póster/carpeta**, **Obtener fanart**, **Obtener imágenes de fondo**, **Reemplazar todas las imágenes de fondo**, **Extraer imagen(es) de fondo**, **Copiar poster.jpg → folder.jpg**, **Corregir proporciones / tamaño de imagen…**.
- **Metadatos**: **Abrir .nfo**, **Abrir movie.xml**, **[!] Errores en el NFO** / **[!] Errores en el XML**, **Igualar los títulos (NFO ↔ XML)…**, **Renombrar NFO para Kodi…**, **Colección ▸**, **Sincronizar calificaciones de IMDb / TMDB**, **Normalizar géneros**, **Comparar géneros con TMDB…**, **Quitar los enlaces de arte en línea del NFO…**, **Agregar género(s) personalizado(s) a la configuración**.
- **IDs y fuentes**: **Buscar fuentes**, **Verificar IDs de IMDb/TMDB**, **Normalizar fuentes**, **Copiar el nombre de la película**.
- **Video y subtítulos**: **Subtítulos…**, **Subtítulos incrustados en la imagen…**.
- **Abrir en línea**: **Abrir en IMDb**, **Abrir en TMDB**, **Abrir en Fanart.tv**, **Abrir en OpenSubtitles.org**, **Abrir en el scraper**.
- **Revisar y reparar**: **Informe de estado**, **Revisar mejoras**, **Reparación automática**.
- **Actualizar**: **Actualizar (sin FFprobe)**, **Actualizar (con FFprobe)**; **Quitar de la lista**.
Varias películas: seleccione con Ctrl+clic, Shift+clic, Shift+flechas o Shift+PageUp / PageDown / Home / End. El mismo menú ejecuta las versiones por lotes; las ejecuciones largas muestran una ventana de progreso con Cancelar.

## Doble clic
| Película | la carpeta de la película
| Géneros, Calificación, Votos | el archivo .nfo en su editor
| Fuente | elegir la página de IMDb o TMDB
| Póster, Carpeta, Fanart | la imagen en su visor
| Fondos | la primera imagen de fondo
| .nfo / .xml | el archivo en su editor (también cuando tiene errores)
| Idioma | el archivo del que vino el valor (movie.xml o el NFO) en su editor
| Video, Calidad | reproduce el video
| Subtítulos | las pistas de subtítulos
| Biblioteca | la carpeta de la biblioteca
| Colección | el archivo .nfo en su editor

## Reglas de estado que conviene conocer
- "Falta la imagen de carpeta" está desactivada cuando el modo de estado es solo NFO (todos los servidores muestran poster.jpg sin folder.jpg); todos los perfiles la activan en los modos con movie.xml. "Póster e imagen de carpeta diferentes" está desactivada por defecto.
- "Falta el logo (clear logo) / el arte del disco" (clearlogo.png, logo.png, disc.png, discart.png, cdart.png, también como <video>-clearlogo.png …) solo está activada en el perfil Estricto: el skin propio de Kodi casi no los usa, algunos otros skins sí. MediaClinic todavía no los descarga.
- "No lo lee Infuse: movie.nfo (necesita <video>.nfo)" — con programas marcados arriba en las Reglas de estado, un aviso cuando el NFO, el póster o el fanart tiene un nombre que uno de ellos no lee (Infuse, comprobado en un Apple TV con las opciones "Preferir arte local" y "Preferir metadatos locales" activadas, lee <video>.nfo, nunca movie.nfo; de arte lee <video>-poster.jpg, <video>.jpg, poster.jpg, folder.jpg, <video>-fanart.jpg y fanart.jpg, y sin ninguna de ellas muestra cualquier otra imagen de la carpeta como póster). Emby se comprobó en un servidor real: lee <video>.nfo y movie.nfo, la colección del NFO y todos los nombres habituales de póster y fanart, así que una carpeta al estilo de Kodi funciona en Emby tal como está. Jellyfin también se comprobó y lee lo mismo; crea colecciones a partir del NFO solo cuando la opción de la biblioteca "Automatically add to collection" está activada (Dashboard → Libraries → Manage library; desactivada por defecto) y dos o más películas comparten el nombre de la colección. Plex se comprobó en un servidor real: lee todos los nombres habituales de póster y fanart (poster, folder, cover, <video>, <video>-poster, fanart, backdrop, background, .jpg o .png), pero ningún NFO ni ninguna colección de él; con solo Plex marcado, una ventana pregunta una vez si se desactivan las revisiones del NFO y de las colecciones (cámbielo después con la casilla debajo de los programas). Las marcas también desactivan lo que esos programas no usan: solo Infuse no tiene revisiones de folder.jpg, backdrops extra ni colecciones, y las revisiones de NFO solo de Kodi se hacen solo cuando Kodi está marcado. Obtener escribe el arte nuevo con el nombre que lee cada programa marcado; cuando no hay ninguno, escribe un archivo para cada uno.
- **Renombrar archivos para mis programas…** (clic derecho, ⚠ Corregir problemas, o Herramientas → **Renombrar archivos para mis programas — Todas las películas…**) es la corrección de ese aviso: da al NFO, al póster y al fanart los nombres que lee cada programa marcado (p. ej. movie.nfo → <video>.nfo para Infuse). Una vista previa lista cada cambio antes; primero se hace una copia y el Historial de copias puede deshacerlo. El video nunca se renombra, un archivo existente nunca se sobrescribe, y una carpeta con dos NFO, una carpeta de DVD / Blu-ray o un par de programas sin nombre en común se lista y se deja como está.
- **Convertir movie.xml → NFO…** (clic derecho en una película que tiene movie.xml y no tiene NFO, o Herramientas → **Convertir movie.xml → NFO — Todas las películas sin NFO…**) es para una biblioteca que pasa de MediaBrowser / Media Center Master a Kodi, Plex, Jellyfin, Emby o Infuse: crea un NFO a partir de cada movie.xml (títulos, año, fecha de estreno, duración, sinopsis, calificación y votos, IDs, géneros, estudios, director, guionistas, actores, colección) con el nombre que leen los programas marcados (<video>.nfo cuando hay un programa marcado; movie.nfo cuando no hay ninguno, o para una carpeta de DVD / Blu-ray, una película en varias partes o una carpeta sin vídeo). movie.xml no se cambia; primero hay una vista previa y el Historial de copias puede deshacerlo (quita los NFO nuevos).
- "El NFO tiene enlaces de arte en línea" está desactivada en todos los perfiles. **Quitar los enlaces de arte en línea del NFO…** (clic derecho → la parte del NFO, o Herramientas → … — Todas las películas…) quita los enlaces web (<thumb> / <fanart><thumb>) solo del arte que la carpeta tiene como archivo; antes los cuenta, hace una copia de seguridad de cada NFO y conserva las imágenes de actores, el arte de colecciones y todas las demás etiquetas.
- "El NFO tiene un '&' sin escapar": Kodi lee ese NFO, pero Jellyfin puede ignorar todo el archivo. La Reparación automática escribe '&amp;'. Un ID de IMDb / TMDB solo en <imdbid> / <tmdbid> también es una advertencia: Kodi lee <uniqueid>, así que la Reparación automática lo agrega (y conserva las demás etiquetas); una fecha en <premiered> cuenta como el año. En movie.xml, un ID o los votos solo en <IMDB_ID> / <TMDB> / <Votes> también son una advertencia: los programas antiguos leen <IMDbId> / <TMDbId> / <VoteCount>, y la Reparación automática los agrega. "Etiquetas de ID escritas en el NFO" (en estas reglas del NFO) elige cómo se escribe un ID de IMDb / TMDB: todos los estilos de etiqueta (<id>, <uniqueid>, <imdbid>, <id moviedb>, para que todo programa lo encuentre; el valor por defecto) o solo <uniqueid> (Kodi, Jellyfin y Emby lo leen). Con solo <uniqueid>, las etiquetas de ID que el NFO ya tiene se siguen corrigiendo, no se agrega ninguna otra etiqueta de ID ni etiquetas vacías; movie.xml no cambia.
- Revisiones de contenido: IDs no válidos, un año fuera de rango, una duración o unos votos que no son un número, una calificación mayor que 10, una etiqueta escrita dos veces, un <title> / <plot> vacío (activado solo en el perfil Estricto).
- "El título difiere entre NFO y XML" nombra ambos títulos locales; "Cuando la Reparación automática no sabe cuál es el título local correcto" elige qué hace entonces la Reparación automática.
- Un ID faltante: "Película con UNA sola fuente" y "Película SIN fuente" pueden ser cada una un error, una advertencia o estar desactivadas.
"""

TAB_05 = """
# Imágenes

## Póster, carpeta y fanart
**Obtener póster/carpeta…** muestra su imagen junto a los pósteres de TMDB (y fanart.tv); **Usar esta** descarga el tamaño completo al póster (y a folder.jpg cuando la carpeta usa uno) tras una copia de seguridad. **Obtener fanart…** hace lo mismo con el fanart. **Copiar poster.jpg → folder.jpg** corrige las carpetas cuyo folder.jpg difiere; **Herramientas → Copiar poster.jpg → folder.jpg — Todas las películas con diferencias…** muestra antes una vista previa.
- Una descarga se revisa antes de reemplazar algo: una página que no es una imagen, o una imagen cortada, nunca reemplaza un archivo bueno.
- Las ventanas Obtener se cierran con **Listo** (o [[Esc]]); las imágenes aplicadas antes se conservan. Mientras corre una descarga, Listo muestra "Finalizando…".

## Niveles de calidad
| Póster / Carpeta (2:3) | 4K 2000×3000 · 1440p 1500×2250 · 1080p 1000×1500 · 720p 666×1000 · 540p 540×810 · 480p 480×720 · 360p
| Fanart (16:9) | 4K 3840×2160 · 1440p 2560×1440 · 1080p 1920×1080 · 720p 1280×720 · 540p 960×540 · 480p 854×480 · 360p
Tolerancia de ±5 %. El nivel mínimo es una sola opción (Configuración → Reglas de estado y Configuración → Tamaños de imagen); las imágenes por debajo de él son advertencias. Proporciones: póster y carpeta 2:3 (3:4 opcional), fanart 16:9 (3:2 opcional). "Dañada" (✕) significa que el scan encontró un encabezado o un final de archivo incorrectos. Un archivo dañado en el medio puede pasar el scan; Corregir imagen o Copiar póster dicen entonces que no se puede leer. Un PNG llamado poster.jpg se lee y recibe una advertencia "la extensión no coincide".

## Imágenes de fondo
| Extraer imagen(es) de fondo | cuadros de FFmpeg repartidos a lo largo de la película
| Obtener imágenes de fondo | elegir imágenes de fondo de TMDB / fanart.tv; reemplazar un archivo o guardar uno nuevo
| Reemplazar todas las imágenes de fondo | elegir la fuente y cuántas (empieza en el número que tiene); primero la resolución más alta, una descarga fallida se reemplaza por la imagen siguiente; antes, una copia de seguridad
**Herramientas → Eliminar subcarpetas extrafanart — Todas las películas…** elimina las carpetas extrafanart (antes, una copia de seguridad). Jellyfin y Emby las usan como imágenes de fondo adicionales; Kodi y Plex no las leen. Las reglas de estado señalan las imágenes de fondo demasiado pocas y las muy pequeñas.

## Cuadros de la película
Obtener fanart y Obtener imágenes de fondo tienen un botón **🎞 Cuadros de la película** (con FFmpeg configurado y un video en la carpeta).
- 10 cuadros del 10 % al 90 % de la duración; los cuadros negros o planos se reemplazan por un momento cercano. **Más cuadros** da un conjunto nuevo.
- Los cuadros conservan la resolución del video y se marcan cuando están por debajo del mínimo del fanart. Son archivos temporales, que se eliminan al cerrar la ventana.
- No hace falta un ID de TMDB: sin él, Obtener fanart y Obtener imágenes de fondo abren con los cuadros de la película (o fanart.tv por el ID de IMDb).

## fanart.tv
Con una clave de fanart.tv (Configuración → Claves de API) las ventanas Obtener y Reemplazar todas las imágenes de fondo tienen una opción **Fuente**: TMDB, fanart.tv o Ambos.
- Pósteres: primero el idioma de su biblioteca, luego imágenes sin texto, luego inglés.
- Imágenes de fondo: fondos de fanart.tv (1920×1080); marque "incluir miniaturas horizontales" para las de 1000×562.
- fanart.tv no informa el tamaño en píxeles: "~1920×1080" es su tamaño habitual; el tamaño real se revisa después de la descarga. Las respuestas se guardan 7 días.

## Corregir proporciones y tamaño
Clic derecho → Imágenes → **Corregir proporciones / tamaño de imagen…** corrige un póster, una imagen de carpeta o un fanart con proporciones incorrectas o baja resolución, con una vista antes / después.
- **Método**: Relleno con desenfoque conserva toda la imagen y llena las bandas vacías con una copia desenfocada (pósteres); Recorte inteligente conserva la parte con más detalle (fanart); Recorte central; Relleno sólido. Hasta un 3 % simplemente se estira.
- **Tamaño**: el nivel más cercano a la imagen, con su factor y una marca — ✓ recomendado, ⚠ suave, ✕ demasiado lejos (no se ofrece). "Mantener el tamaño actual" corrige solo las proporciones. Para una imagen mucho más grande use **Buscar una mejor en línea**.
- **Ampliar con IA** (opcional): **Descargar el ampliador (unos 45 MB)…** instala Real-ESRGAN (verificado con su SHA-256) y lo prueba una vez; necesita una tarjeta gráfica con Vulkan. Se recomienda ×2, se permite hasta ×4 — revise la vista previa: la IA puede inventar detalles.
- "Copiar también el resultado a folder.jpg" se marca cuando folder.jpg es la misma imagen que el póster; cuando es otra imagen, aparece "Corregir también folder.jpg (otra imagen: se corrige aparte, no se reemplaza)". Antes se hace una copia de seguridad de cada archivo.
- Varias películas, o **Herramientas → Corregir proporciones / tamaño de imagen — Todas las películas con advertencias de imagen…**: una vista previa lista cada imagen y su corrección; solo se usan los tamaños ✓. Puede minimizar la ventana mientras se ejecuta; **■ Detener** la detiene.
"""

TAB_06 = """
# Calificaciones, géneros e IDs

## Calificaciones
**Sincronizar calificaciones** obtiene la calificación y los votos de TMDB y / u OMDb (datos de IMDb) y los escribe en el NFO (<rating>, <votes>, <ratings> de Kodi) y en el XML (<IMDBrating>, <Rating>, <Votes>, <VoteCount>).
- El diálogo muestra ambas fuentes lado a lado. Una calificación de 0 o 0 votos cuenta como sin datos.
- Varias películas: "Aplicar esta opción a todas las películas restantes" o "Usar la fuente con más votos" (votos iguales → promedio); **Herramientas → Sincronizar calificaciones en línea — Todas las películas…** obtiene primero y luego muestra actual → nuevo para cada película.
- Cuando ninguna fuente tiene datos, un segundo diálogo pide una vez valores escritos u Omitir.
- Cuando no se puede acceder a TMDB u OMDb, la película se omite y se lista al final — nunca se trata como "sin calificación".
Los valores por defecto de las casillas: Configuración → Calificaciones.
| ⬤ | encontrada, NFO y XML coinciden
| ◐ | NFO y XML difieren
| ○ | no se encontró ninguna etiqueta
| ✕ | la etiqueta no es un número

## Géneros
**Normalizar géneros** corrige los géneros en ambos archivos: mayúsculas, sinónimos ("Sci-Fi" → "Science Fiction"), traducciones (PT, DE, FR, ES, IT, RU, ZH, AR), duplicados y etiquetas unidas ("Family/Fantasy"). Copia los géneros al archivo que no tiene ninguno y convierte <Genres>/<Genre> de un NFO en etiquetas <genre> de Kodi. Las películas sin géneros los reciben de TMDB (luego OMDb), con una vista previa antes. Los géneros que no están en Configuración → Géneros son "personalizados": consérvelos o elimínelos, o Clic derecho → **Agregar género(s) personalizado(s) a la configuración**. **Herramientas → Normalizar géneros — Todas las películas…** muestra una vista previa de cada cambio.
**Comparar géneros con TMDB…** (clic derecho, o Herramientas → … — Todas las películas…) busca en TMDB las películas que ya tienen géneros y un ID, y muestra solo aquellas cuyos géneros son distintos (archivo → TMDB). Nada viene marcado: cada archivo conserva sus géneros, salvo que usted marque la película; las marcadas reciben los géneros de TMDB (antes una copia de seguridad, Deshacer). Necesita una clave de la API de TMDB.

## IDs de IMDb y TMDB
- **Normalizar fuentes** completa las etiquetas faltantes, le permite elegir entre IDs en conflicto (títulos buscados en TMDB) y pide un ID donde no hay ninguno. Cuando solo se conoce un ID, cada escritura de ID deja etiquetas VACÍAS para la otra fuente (p. ej. <tmdbid></tmdbid>), listas para completar a mano (no con **solo <uniqueid>**, Configuración → Reglas de estado → NFO). Los valores existentes nunca se borran.
- **Buscar fuentes** busca la película en TMDB por título + año (en inglés, en el idioma de su biblioteca y con el título original). Cada película muestra los IDs que tienen ahora sus archivos y, primero, la película que corresponde a ese ID. **Escribir ID…** le permite escribir un ID de IMDb (tt…) o de TMDB, muestra título, año y póster, y luego escribe ambos IDs. También acepta la dirección de una página de IMDb o de TMDB, o un número de IMDb sin tt; un valor erróneo en IMDb junto a un ID de TMDB válido se deja fuera (la ventana lo dice) y se usa el ID de IMDb que indica TMDB.
- Películas en IMDb pero no en TMDB: la primera fila dice "IMDb tt… — no está en TMDB"; **Confirmar IMDb** escribe el ID de IMDb y marca la película "OK (IMDb only — not on TMDB)", así Verificar IDs y la Reparación automática dejan de buscarla.
- **Verificar IDs de IMDb/TMDB** comprueba en TMDB que los IDs pertenecen a la película (título en cualquier idioma, año ±1): OK, IMDb y TMDB apuntan a películas distintas, el ID pertenece a otra película, el ID no existe, NFO y XML no coinciden, sin IDs. El informe se ordena por cualquier columna y se guarda en .txt o .csv; no se escribe nada hasta que pulse **Corregir…**. También guarda la colección de TMDB de la película (pestaña Colecciones). Una etiqueta con algo que no es un ID (p. ej. el número de TMDB 7840 en una etiqueta de IMDb) da "Falta el ID de IMDb (la etiqueta contiene '7840', que no es un ID válido)", o "Conflicto de ID de IMDb entre etiquetas: '7840' no es un ID válido" junto a uno bueno; la Reparación automática lo completa, comprobando primero el ID que la película ya tiene (título + año) antes de buscar por título. En **Elija la entrada de TMDB**, haga clic en cualquier parte de la fila de una película para elegirla (borde verde); un doble clic la aplica.
- **Copiar el nombre de la película** copia el título (pregunta cuando los archivos tienen varios).

## Títulos locales
Cuando NFO <title> y XML <LocalTitle> difieren, Clic derecho → Metadatos → **Igualar los títulos (NFO ↔ XML)…** le permite elegir; la Reparación automática da al lado que es el título original (o que no coincide con la carpeta) el título del otro.

## Audio, subtítulos e idioma
- **Audio**: pistas de FFprobe como IDIOMA (CANALES); pase el puntero para ver el códec y el bitrate. Una pista que FFprobe informa como UND toma el idioma del NFO o del XML cuando corresponde ("POR — from NFO"). No se escribe nada.
- **Subtítulos**: pistas integradas y archivos externos (p. ej. Movie.pt.srt, también en una carpeta Subs; se leen las marcas forced y SDH). Clic derecho → **Subtítulos…** se abre para cualquier película; **🌐 Abrir en OpenSubtitles.org** lo busca allí.
- **Subtítulos incrustados en la imagen…** marca los subtítulos grabados en la imagen (no se pueden detectar): marque el/los idioma(s) o escriba un código ISO 639-2. La app escribe <tag>Hardsub POR</tag> en el NFO y <Tags><Tag>Hardsub POR</Tag></Tags> en el XML; la columna muestra "Hard: POR".
- La columna **¿Idioma OK?** es S cuando el idioma de destino (Configuración → Idioma) está en una pista de audio o en un subtítulo: leído por FFprobe, un archivo de subtítulos, una marca de incrustados, o un stream escrito en el NFO (streamdetails) o en movie.xml (MediaInfo). NFO <language> y XML <Language> / <LanguageCode> de nivel superior no cuentan: son el idioma para descargar metadatos.
"""

TAB_07 = """
# Herramientas y Reparación automática

## El menú Herramientas
| Exportar lista de películas… | CSV, TSV, texto, Excel o una página HTML ([[Ctrl+Shift+E]], también el botón **Exportar…**)
| Elegir columnas… | mostrar u ocultar columnas
| Carpetas ignoradas en el último scan… | las carpetas que el último scan no agregó
| Estadísticas de la biblioteca | estado, calidad, géneros, décadas, bibliotecas
| Informe de películas duplicadas | el mismo ID, o título + año, en otro lugar
| Administrar marcas 'No es duplicado'… | sus respuestas, con Quitar
| Recalcular el estado (sin nuevo scan) | las reglas de nuevo, sin leer archivos
| Guardar / abrir resultados del scan… | un scan a un archivo o desde un archivo (**Guardar resultados del scan…**, **Abrir resultados del scan…**)
| Copias de seguridad / Deshacer… | cada ejecución que cambió archivos (pestaña Copias de seguridad y deshacer)
| Actualizar íconos — Todas las películas | vuelve a dibujar todas las filas ([[Ctrl+I]])
Las entradas "— Todas las películas": **Sincronizar calificaciones en línea — Todas las películas…**, **Normalizar fuentes — Todas las películas…**, **Buscar fuentes — Todas las películas…**, **Verificar IDs de IMDb/TMDB — Todas las películas…**, **Verificar colecciones en línea — Todas las películas…**, **Corregir colecciones — Todas las películas…**, **Crear carpetas de colección — Todas…**, **Reparación automática — Todas las películas…**, **Normalizar géneros — Todas las películas…**, **Comparar géneros con TMDB — Todas las películas…**, **Revisar mejoras — Todas las películas…**, **Informe de estado — Todas las películas**, **Copiar poster.jpg → folder.jpg — Todas las películas con diferencias…**, **Corregir proporciones / tamaño de imagen — Todas las películas con advertencias de imagen…**, **Renombrar NFO para Kodi — Todas las películas con un NFO con el nombre de la carpeta…**, **Quitar los enlaces de arte en línea de los NFO — Todas las películas…**, **Eliminar subcarpetas extrafanart — Todas las películas…**. Siempre cubren todas las películas de todas las bibliotecas; cuando un filtro oculta filas, la vista previa dice "todas las N películas de todas las bibliotecas (el filtro muestra M)".

## Vista previa antes de escribir
Las herramientas masivas primero muestran lo que va a cambiar; cerrar la vista previa no escribe nada, el botón **▶** (con el nombre de la propia acción) escribe. Cada ejecución crea una carpeta de copia de seguridad, se puede cancelar ("Cancelado después de k de n; m quedaron fuera") y termina con un resumen que remite a **Copias de seguridad / Deshacer**.

## Reparación automática
Aplica todas las correcciones seguras de una vez. Las imágenes nunca se tocan. Primero una copia de seguridad; el resumen lista las películas corregidas, omitidas y las que siguen fallando; **Reparación automática — Todas las películas…** ofrece una vista previa sin cambios. Los pasos, en este orden:
1. Escapar '&' en el NFO (& → &amp;; Jellyfin ignora un NFO con un '&' sin escapar)
2. Resolver IDs de IMDb/TMDB en conflicto con TMDB
3. Buscar IDs de IMDb/TMDB en TMDB (título + año exactos se aplica solo; si no, pregunta)
4. Copiar el ID de IMDb/TMDB al otro archivo; Agregar <uniqueid> para los IDs que Kodi no lee (conserva <imdbid> / <tmdbid>); Agregar las etiquetas de movie.xml que leen los programas antiguos (<IMDbId>, <TMDbId>, <VoteCount>)
5. Sincronizar calificación y votos en línea (TMDB/OMDb)
6. Normalizar géneros y sincronizarlos entre NFO y XML (se conservan los géneros personalizados)
7. Completar géneros desde TMDB (requiere ID de TMDB verificado)
8. Completar el año desde TMDB (requiere ID de TMDB verificado)
9. Copiar el título entre NFO <title> y XML <LocalTitle>
10. Igualar el título local en NFO <title> y XML <LocalTitle>
12. Recortar IDs como 'tt0133093/' y quitar etiquetas duplicadas idénticas (NFO / XML)
13. Escribir la colección que TMDB indica para la película (NFO <set>; se conservan sus propias colecciones)
14. Renombrar el NFO con el nombre de la carpeta para que Kodi lo lea (<video>.nfo; movie.nfo para discos, varias partes, versiones)

## Exportar lista de películas
- Columnas: Básico, Identificar (enlaces + resumen), Estándar, Todo o su propia selección (también la columna Colección).
- Filas: todas las películas o la vista filtrada actual (en la vista agrupada: las películas, nunca las filas de colección).
- Formatos: CSV separado por comas, CSV separado por punto y coma (Excel en CH / DE / PT / FR), separado por tabulaciones, lista simple, Excel .xlsx, página HTML. Un archivo guardado ofrece "¿Abrirlo ahora?".
- Página HTML: un archivo que se abre en cualquier navegador, con las columnas elegidas, un cuadro de filtro y orden con un clic en el título de la columna; clara u oscura como el sistema. **Incluir miniaturas de los pósteres** pone una copia pequeña de cada póster dentro del archivo (archivo más grande; los pósteres se leen con una ventana de progreso y Cancelar).
"""

TAB_08 = """
# Colecciones

## Qué es una colección
Una colección (Kodi la llama conjunto de películas, movie set) agrupa las películas de una saga — "Harry Potter Collection", "The Matrix Collection". El NFO la guarda como <set><name>…</name></set>; Kodi agrupa las películas por ese **nombre**, así que dos formas de escribirlo crean dos conjuntos. Jellyfin también lee el ID de colección de TMDB (<set tmdbcolid="…">). movie.xml guarda la misma colección (TMDbCollectionId, CollectionName); MediaClinic lee y escribe ambos archivos.

## La columna Colección y la vista agrupada
- La columna **Colección** (oculta por defecto, Herramientas → Elegir columnas…) muestra el nombre; el cuadro Filtro la encuentra.
- **Agrupar por colección** (junto a los botones de orden, o Configuración → NFO / XML → Colecciones; desactivado por defecto) muestra cada colección como una fila — "Harry Potter Collection (8)", el rango de años, el peor color de estado — con sus películas debajo. Las películas sin colección quedan solas, en su orden.
- Dónde queda una fila de colección: bajo una columna de texto (Película, Géneros…) se ordena por el nombre de la colección; bajo cualquier otra columna queda donde está su primera película.
- Un clic selecciona una fila de colección; su flecha ▸, un doble clic o [[+]] / [[-]] la abren o la cierran; las colecciones abiertas siguen abiertas mientras la app está en ejecución. **Todas las acciones ▾** del panel de la colección muestra el menú de la fila.
- Seleccionar una fila de colección equivale a seleccionar sus películas para cualquier acción ("8 películas seleccionadas"); [[Ctrl+A]] selecciona todas las películas, también dentro de colecciones cerradas.
- Clic derecho en una fila de colección: **Expandir / Contraer**, **Seleccionar sus películas**, **Corregir colección…**, **Renombrar / unir colección…** (elija una colección en uso para unirse a ella: sus películas reciben su nombre y su ID de TMDB), **Crear carpeta de colección…**, **Imágenes de la colección…**, **Abrir la carpeta de la colección**, **Abrir la colección en TMDB** (**Buscar la colección en TMDB** cuando no se conoce el ID de TMDB de la colección), **Verificar colección en línea**, **Expandir todas / Contraer todas**. El panel muestra la colección: su póster (de la carpeta de la colección), ID de TMDB, años, carpeta, imágenes, sinopsis, sus películas y las correcciones, con **Imágenes…**, **Abrir póster**, **Abrir fanart**, **Abrir carpeta** y **TMDB** (la página de la colección con sus películas, o una búsqueda del nombre en TMDB).
- Una colección, un nombre: Kodi muestra un conjunto por nombre, así que una colección de TMDB recibe UN nombre para todas sus películas — en inglés, salvo que MÁS DE LA MITAD de sus películas tengan su título local en otro idioma (NFO <title>; XML <LocalTitle> cuando el NFO no lo tiene) — entonces en ese idioma. **Configuración → NFO / XML → Colecciones → Idioma del nombre de la colección** puede fijar en su lugar un idioma para todas las colecciones (el nombre de TMDB en ese idioma; si no, en inglés). Un título que la app no puede asociar a un título de TMDB cuenta como inglés. El idioma de la biblioteca nunca se usa para el nombre; cuando TMDB todavía no dio el nombre en inglés, se conserva el nombre de sus NFO y **Verificar colecciones en línea** lo obtiene. Cuando NFO <title> y XML <LocalTitle> difieren, la película muestra **El título difiere entre NFO y XML** y su corrección pregunta qué título conservar. La advertencia, **Corregir colección…** y la Reparación automática usan el mismo nombre, y **Corregir colección…** lo escribe en todas las películas de la colección (la vista previa las lista). Cuando su propia colección está escrita de dos formas, Corregir escribe el nombre que usa la mayoría de sus películas. Después de cualquier cambio se revisa de nuevo la tabla, así que una advertencia corregida desaparece.

## Verificar colecciones en línea
**Herramientas → Verificar colecciones en línea — Todas las películas…** (o Clic derecho → Metadatos → Colección ▸ → **Verificar colección en línea**) pregunta a TMDB a qué colección pertenece cada película — una consulta por película, dos por colección, y de nuevo solo después de 30 días. **Verificar IDs de IMDb/TMDB** guarda los mismos datos sin costo adicional. Las películas sin ID de TMDB, o cuyo ID marcó Verificar IDs, se omiten y se cuentan. Los scans y Recalcular el estado nunca se conectan a internet.

## Las reglas de colección
Tres reglas en Configuración → Reglas de estado, activadas en el perfil Estricto (desactivadas en Fácil y Medio), todas advertencias:
- **Falta la colección o difiere de TMDB**: TMDB indica una colección que el NFO no tiene, el NFO nombra otra, o una colección está escrita de dos formas en su biblioteca ("written as X here and as Y in 3 other movies — Kodi shows two sets").
- **Imágenes de la colección**: falta la carpeta de la colección, su póster o su fanart (solo mientras haya una carpeta de colecciones definida).
Sus propias colecciones ("Disney", "Ganadores del Óscar") nunca reciben advertencias y nunca se quitan. Un nombre sin ID de TMDB que no coincide con ninguno de los nombres de TMDB cuenta como suyo, también cuando TMDB pone la película en una colección; solo **Corregir colección…** en esa película, a pedido suyo, lo reemplaza. Una película no revisada en línea no recibe la advertencia "falta / difiere de TMDB" (su texto emergente lo indica); una colección escrita de dos formas y un movie.xml que difiere del NFO se detectan en cada scan.

## Corregir colecciones
Clic derecho → Metadatos → **Colección ▸**:
- **Corregir colección…** escribe la colección que indica TMDB, con el nombre único de la colección (vea "Una colección, un nombre" arriba), con su sinopsis cuando el NFO no la tiene. Varias películas: primero una vista previa. También **Herramientas → Corregir colecciones — Todas las películas…** y el paso de la Reparación automática.
- **Definir colección…** pone las películas seleccionadas en una colección: una en uso, un nombre propio, o una colección de TMDB encontrada con **Buscar en TMDB** (se escriben su ID de TMDB y su nombre). Con la casilla marcada, luego crea la carpeta de la colección y abre **Imágenes de la colección…**. **Quitar de la colección…** (pregunta antes) es la única acción que quita un <set>: indica que las películas están **fuera de toda colección**. MediaClinic lo recuerda (no_collection.json), así que la colección de TMDB ya no se sugiere para ellas mientras su NFO no tenga <set>; también sirve para una película que TMDB pone en una colección que usted no quiere. **Definir colección…** vuelve a poner una película en una colección.
- Una colección que TMDB ya no tiene: cuando un NFO enlaza una colección de TMDB (tmdbcolid) que TMDB ya no indica para la película, o que ya no existe, **Verificar colecciones en línea** da la advertencia "Collection: '…' no longer exists on TMDB" (o "is not listed by TMDB for this movie"); **Corregir** ejecuta **Quitar de la colección…**.
- **Actualizar** vuelve a leer el NFO: una película cuyo <set> usted cambió pasa a su nueva colección en la vista agrupada. movie.xml: cada acción de colección escribe la misma colección en movie.xml (TMDbCollectionId y CollectionNumber = el ID de colección de TMDB, o 0 si no hay; CollectionName); Quitar de la colección… pone los IDs en 0 y quita el nombre. Un bloque <set> al estilo NFO dentro de movie.xml no corresponde ahí y se quita. Cuando movie.xml y el NFO indican colecciones distintas, la advertencia "Collection: movie.xml says …" se corrige con **Sincronizar colección (NFO ↔ movie.xml)…** (la colección del NFO pasa a movie.xml; un NFO sin colección toma la de movie.xml). <JSONDump> nunca se cambia.
Antes se hace una copia de seguridad de cada NFO; **Copias de seguridad / Deshacer** lo restaura. Todos los demás bytes del archivo quedan como estaban.

## La carpeta de colecciones (imágenes de la colección)
Kodi lee las imágenes de las colecciones de UNA carpeta que usted elige en Kodi: Settings → Media → Videos → **Movie set information folder**. Defina la misma carpeta en **Bibliotecas…** → **Carpeta de colecciones** (Configuración → NFO / XML → Colecciones la muestra; marcar **Agrupar por colección** sin ella pide una) (el mismo recurso compartido, p. ej. \\\\NAS\\Movies\\Sets o Z:\\Sets).
- Cada colección tiene una carpeta con el nombre de la colección, con / \\ ? : * " < > | escritos como _ (regla de Kodi), que contiene poster.jpg y fanart.jpg.
- **Crear carpeta de colección…** (Clic derecho, una fila de colección, o **Herramientas → Crear carpetas de colección — Todas…**) muestra una vista previa, crea la carpeta y descarga de TMDB el póster (primero en el idioma de la biblioteca) y el fanart. Un archivo existente nunca se reemplaza. La falta de clave de API de TMDB, o una colección sin póster o fanart en TMDB, se indica en el resultado. Sus propias colecciones reciben la carpeta: elija sus imágenes con **Imágenes de la colección…**. Deshacer quita lo que creó la ejecución.
- **Imágenes de la colección…** (Clic derecho en una película o en una fila de colección, **Imágenes…** del panel, o **Corregir** en "Collection artwork: … missing" para una colección) muestra los pósteres y las imágenes de fanart de la colección de TMDB, o de **Las películas de esta colección** (su propio póster / fanart). Sin una colección de TMDB conocida, **Buscar en TMDB** encuentra una por nombre. Los pósteres vienen de 12 por página (4 por fila) y las imágenes de fanart de 9 por página (3 por fila): **Siguiente ›** y **‹ Anterior** muestran las otras páginas, y una imagen elegida sigue elegida. La ventana conserva el tamaño que usted le da. Haga clic en un póster y en una imagen de fanart, luego en **Guardar en la carpeta**: la carpeta se crea si falta; una imagen existente solo se reemplaza después de una copia de seguridad, así que **Copias de seguridad / Deshacer** puede revertirlo.
- Una carpeta que difiere solo en mayúsculas y minúsculas se encuentra (Windows, SMB); una que difiere en acentos no es la misma carpeta para Kodi, y la advertencia la nombra.
- Cuando una colección recibe un nombre nuevo (**Corregir colección…**, **Definir colección…**, **Renombrar / unir colección…**, Reparación automática), su carpeta la acompaña: los archivos de la carpeta antigua pasan a la carpeta del nombre nuevo, y la carpeta antigua vacía se quita. Cuando ambas carpetas tienen un póster (o fanart), se conserva la imagen de la carpeta antigua y la otra va a replaced\\ dentro de la carpeta — no se elimina nada. La carpeta queda donde está mientras otra película siga usando el nombre antiguo. Copias de seguridad / Deshacer restaura todo.
- Una carpeta que quedó con otro nombre de TMDB de la colección (de antes) muestra **Collection folder: images left in '…'**; su corrección **Mover a la carpeta de la colección** mueve los archivos de la misma forma.
"""

TAB_09 = """
# Copias de seguridad y deshacer

## Copias de seguridad automáticas
Antes de que la app cambie un archivo .nfo, .xml o de imagen, copia el original a backup\\backup_<Movie>_<date>_<time>\\ en %APPDATA%\\MediaMetadataClinic (junto con la configuración, así que una actualización los conserva). Una ejecución (un lote, o una acción en una película) es una carpeta de copia de seguridad con un manifest.json (de dónde vino cada archivo, qué acción lo creó). Cada escritura de NFO / XML es atómica: una escritura fallida nunca deja un archivo a medio escribir, y se conservan la codificación, el BOM y los finales de línea del archivo.
> Si no se puede hacer la copia de seguridad, el cambio no se realiza — la película se informa como fallida.

## Copias de seguridad / Deshacer
**Copias de seguridad / Deshacer…** (en el encabezado y en Herramientas) lista las ejecuciones, las más recientes primero. **Restaurar esta ejecución** devuelve los archivos:
- antes se hace una copia de seguridad de sus archivos actuales, así que un deshacer se puede deshacer;
- los archivos cambiados después de la ejecución se listan y se pueden omitir;
- un NFO renombrado recupera su nombre anterior, y los archivos que creó una ejecución (imágenes de colección) se quitan;
- las filas se actualizan.
Las ejecuciones quitadas por la limpieza de tamaño siguen en la lista como "eliminada por la limpieza por tamaño".

## Límite de tamaño
Configuración → Copia de seguridad: el tamaño máximo de la carpeta de copias de seguridad y "Eliminar automáticamente las copias más antiguas cuando la carpeta supere este tamaño" (activado por defecto). Las ejecuciones de esta sesión y de los últimos 14 días nunca se eliminan automáticamente; la limpieza se escribe en un registro. Una ejecución más grande que el límite se avisa antes de empezar. **Eliminar todas las copias** vacía la carpeta.
"""

TAB_10 = """
# Servidores multimedia

## Kodi
MediaClinic lee todos los nombres que usa Kodi y muestra el archivo que Kodi elegiría, en el orden de Kodi:
| Póster | <video>-poster.jpg/.png, poster.jpg/.png, <video>.tbn, movie.tbn, <pila>-poster.jpg (película en varias partes: Pelicula-poster.jpg para Pelicula-CD1.mkv)
| Fanart | <video>-fanart.jpg/.png, fanart.jpg/.png, <pila>-fanart.jpg
| NFO | movie.nfo, <video>.nfo, <pila>.nfo para una película en varias partes (Pelicula.nfo para Pelicula-CD1.mkv + Pelicula-CD2.mkv; Jellyfin lee movie.nfo), y el único NFO de la carpeta, con cualquier nombre, cuando contiene <movie> (un .nfo de información del release se ignora)
| Fanart extra | fanart1.jpg…, <video>-fanart1.jpg… (la carpeta extrafanart es para Jellyfin y Emby)
<video> es el nombre del archivo de video sin su extensión. Los textos emergentes indican qué archivo se encontró. Obtener póster/carpeta, Obtener fanart y Copiar póster → carpeta escriben con el estilo que ya usa la carpeta: una carpeta de Kodi recibe <video>-poster.jpg. Copiar póster → carpeta también crea un folder.jpg en una carpeta que no lo tiene. Las imágenes de fondo nuevas siguen la misma regla.
- **Renombrar NFO para Kodi…**: Kodi lee "<video>.nfo" o "movie.nfo", no un NFO con el nombre de la carpeta (salvo si es el único NFO). Ofrece ambos nombres (con el recomendado seleccionado); **Herramientas → Renombrar NFO para Kodi — Todas las películas con un NFO con el nombre de la carpeta…** muestra una vista previa. Un nombre que ya existe nunca se sobrescribe; Deshacer restaura el nombre anterior.
- Carpetas de DVD y Blu-ray: una estructura VIDEO_TS o BDMV es la película; también se leen VIDEO_TS-poster.jpg, VIDEO_TS.nfo, index-poster.jpg e index.nfo. FFprobe y los cuadros usan el archivo .VOB / .m2ts más grande.
- Colecciones: la carpeta de información de colecciones (movie set information folder) de Kodi — pestaña Colecciones.

## Jellyfin, Emby y Plex
Los nombres que leen los otros servidores también se encuentran, después de los de Kodi:
| Póster | <video>.jpg, cover, default, movie, <video>-cover…
| Fanart | backdrop, background, art
| Imágenes de fondo extra | backdrop-1, fanart-1, background-1, art-1
| Imágenes | .jpg, .png, .jpeg, .webp, .gif, .bmp
- Los textos emergentes de póster, carpeta y fanart indican qué servidores leen el archivo encontrado. folder.jpg por sí solo cuenta como póster (Plex, Jellyfin, Emby e Infuse lo usan; Kodi no).
- NFO: Plex no lee NFO; Kodi lee primero movie.nfo cuando "Movies are in separate folders" está activado. Dos NFO que los servidores leen (p. ej. movie.nfo y <video>.nfo) son una advertencia: elimine el que no necesita. mymovies.xml se muestra en el texto emergente de XML: ningún servidor actual lo lee.
- Otros videos no cuentan como "Varios archivos de video en la misma carpeta": tráileres (-trailer), muestras (samples), extras (-featurette, -deleted …), las partes de una película dividida (cd1, part2) y las versiones ("Movie - 1080p"). El texto emergente de Video los lista.
"""

TAB_11 = """
# Configuración

**Configuración ▾** en el encabezado abre **Toda la configuración…** o una de las pestañas; [[Ctrl+S]] abre la ventana de Configuración y [[F10]] el menú Configuración ▾. **Guardar y aplicar** escribe settings.json; si un campo no es válido, se indica cuál y no se guarda nada. Los cambios en las reglas de estado y en los tamaños de imagen se aplican de inmediato; los cambios en Idioma, Géneros o en las etiquetas NFO / XML ofrecen un scan de actualización.
| Editor y FFmpeg | editor de texto, carpeta de FFmpeg (**Probar FFmpeg**; se encuentra sola cuando está en el PATH o en una carpeta de instalación habitual), cantidad de cuadros para imágenes de fondo, scan en paralelo (workers; procesos FFprobe), scraper opcional, "Recordar los resultados de FFprobe" (cada video se analiza una vez; un video cambiado se analiza de nuevo)
| Claves de API | claves de TMDB, OMDb y fanart.tv con botones **Validar** y enlaces para obtenerlas; las claves nunca se escriben en el registro
| Navegador | el navegador para los enlaces web
| Idioma | el código ISO 639-1 de la columna ¿Idioma OK? (predeterminado PT)
| Mejoras | las revisiones del informe de mejoras y los tamaños máximos de NFO / XML
| Tamaños de imagen | nivel mínimo de calidad (el mismo valor que en Reglas de estado), aceptación de 3:4 y 3:2, tamaños mínimos de archivo
| Calificaciones | los valores predeterminados de las casillas de Sincronizar calificaciones
| Géneros | la lista estándar de géneros, uno por línea
| NFO / XML | los pares de etiquetas que revisa el informe de mejoras; **Colecciones**: la carpeta de colecciones (se muestra aquí, se define en **Bibliotecas…**) y **Agrupar la tabla de películas por colección**
| Interfaz | **Idioma de la interfaz** (English, Português (Brasil), Español o Igual que Windows; **Reiniciar ahora** reinicia en él), colores alternos en las filas, sugerencias en los encabezados de columna, modo compacto, la línea Repetir, la ventana de carpetas ignoradas después de un scan, barras de título oscuras, "Buscar actualizaciones al iniciar"
| Reglas de estado | **Perfil de estado** (Fácil / Medio / Estricto define todas las reglas a la vez; Personalizado después de sus propios cambios; un usuario nuevo empieza con Estricto, y elegir un perfil después de sus cambios pregunta antes), **Modo de estado** (qué programa reproduce sus películas: el NFO, NFO + movie.xml o solo movie.xml; cambiarlo ofrece un nuevo scan); las reglas en cuatro secciones — **Reglas generales**, **NFO**, **movie.xml** y **Comparaciones NFO ↔ movie.xml** — cada regla con su casilla, umbral y nivel (error / advertencia). Las secciones que el modo de estado no usa siguen visibles, pero en gris y no se pueden cambiar; su configuración se conserva para cuando vuelva a cambiar de modo. **Restablecer valores**
| Copia de seguridad | el límite de tamaño, la eliminación automática de las copias más antiguas, **Eliminar todas las copias**
"""

TAB_12 = """
# Atajos

## Teclado
| [[F1]], [[Ctrl+H]] | Ayuda
| [[F5]] | Full Scan
| [[Esc]] | cancelar un scan; vaciar el cuadro Filtro; cerrar una ventana (Configuración pregunta antes si cambió algo)
| [[Ctrl+F]] | ir al cuadro Filtro
| [[Ctrl+L]] | Borrar todo…
| [[Ctrl+S]] | Configuración (todas las pestañas)
| [[F10]] | el menú Configuración ▾
| [[Ctrl+B]] | ocultar / mostrar el panel de la película seleccionada
| [[Ctrl+O]] | abrir la carpeta de la película seleccionada
| [[Ctrl+E]] | abrir el .nfo de la película seleccionada (la barra de estado avisa si no hay)
| [[Ctrl+R]] | Actualizar la(s) película(s) seleccionada(s) (sin FFprobe)
| [[Ctrl+Shift+R]] | Actualizar la(s) película(s) seleccionada(s) (con FFprobe)
| [[Ctrl+I]] | Actualizar íconos — Todas las películas
| [[Ctrl+Shift+E]] | Exportar lista de películas…
| [[Ctrl+1]] … [[Ctrl+9]] | ajustes de orden 1 a 9
| [[Alt+S]], [[Alt+T]], [[Alt+H]] | los menús Configuración, Herramientas y Ayuda
Los atajos de la tabla de películas funcionan mientras se muestra la parte Películas.

## Selección y desplazamiento
| A–Z, 0–9 | saltar a la siguiente película con esa letra (repita para recorrerlas)
| [[PageUp]], [[PageDown]] | una página; [[Home]] / [[End]]: primera / última fila
| [[Shift+Up]], [[Shift+Down]] | ampliar o reducir la selección
| [[Shift+PageUp]], [[Shift+PageDown]] | ampliar una página
| [[Shift+Home]], [[Shift+End]] | ampliar hasta la primera / última fila
| [[Ctrl+A]] | seleccionar todas las películas mostradas (en el cuadro Filtro: el texto)
| [[+]], [[-]] | abrir / cerrar una fila de colección (vista agrupada)
| Doble clic | la acción de la columna (pestaña Estado y corrección de problemas)
| Clic derecho, [[Shift+F10]], tecla Menú | el menú de la(s) película(s) seleccionada(s)
Con más de una película seleccionada, la barra de estado muestra "N seleccionadas".
"""

TAB_13 = """
# Solución de problemas

## Preguntas frecuentes
### La columna Audio está vacía
Active FFprobe y ejecute Actualizar (con FFprobe).
### Un motivo de estado ya no aplica
Herramientas → Recalcular el estado (sin nuevo scan) — también se hace en cada inicio.
### Fuente muestra ✕ aunque la película tiene un ID
Algunas etiquetas están vacías (p. ej. <TMDB></TMDB>) mientras otras contienen el ID; Normalizar fuentes las completa.
### La extracción de imágenes de fondo no crea archivos
Revise FFmpeg en Configuración → Editor y FFmpeg (**Probar FFmpeg**) y aumente **Tiempo límite por cuadro** en la ventana Extraer imagen(es) de fondo.
### Excel abre el CSV en una sola columna
Exporte con "CSV — separado por punto y coma" o como .xlsx.
### Las colecciones no muestran ninguna advertencia
Ejecute primero **Herramientas → Verificar colecciones en línea — Todas las películas…** (las reglas necesitan los datos de colecciones de TMDB); la regla de imágenes de la colección necesita la carpeta de colecciones (Bibliotecas…).

## Cuando TMDB u OMDb no responden
Nunca se consulta IMDb directamente: las calificaciones de IMDb llegan a través de OMDb, los IDs de IMDb a través de TMDB. El mensaje indica la causa y qué hacer.
- TMDB "demasiadas solicitudes": espere alrededor de un minuto.
- Límite diario de OMDb (1.000 solicitudes con una clave gratuita): intente de nuevo en unas horas; TMDB sigue funcionando.
- Clave rechazada: Configuración → Claves de API → Validar. Sin conexión: revise la conexión a internet e intente de nuevo.
- En un lote, el mensaje aparece una sola vez, con "Pausar esta ejecución", "Continuar con …" (la otra fuente) y "Cancelar". Un servicio en pausa muestra "⚠ … en pausa" en la barra de estado (haga clic para ver por qué o para terminar la pausa); la siguiente acción pregunta "¿Intentar de todos modos?".
- Un error de red detiene una ejecución y conserva lo que se hizo; un archivo que no se puede escribir (bloqueado, de solo lectura) hace fallar solo esa película; un archivo de solo lectura se nombra y la app ofrece quitar el solo lectura (una película: luego lo intenta otra vez; un lote: una pregunta, luego ejecútelo de nuevo).

## Registros
**Ayuda → Abrir la carpeta de registros** abre logs\\ con app.log seleccionado. Todo error inesperado se escribe ahí (nunca las claves de API): adjúntelo a un informe de error.

## Actualizaciones
**Ayuda → Buscar actualizaciones…** (o el botón en Acerca de) consulta a GitHub la versión más reciente; no se envía nada más. Una versión nueva se puede abrir en GitHub u omitir. El programa de Windows también puede descargarla e instalarla (una versión para Linux solo abre la página de descarga): el paquete se comprueba con su SHA-256 y se descomprime junto a la versión actual, que nunca se cambia. Su configuración, resultados y copias de seguridad se conservan (están en %APPDATA%). Configuración → Interfaz → "Buscar actualizaciones al iniciar" (desactivado por defecto) busca una vez al día y solo muestra un enlace en la barra de estado.

## Una sola ventana
MediaClinic se ejecuta una sola vez: si lo inicia de nuevo, la ventana abierta pasa al frente.
"""

# (menu / tab label, text) in the order of help_text.HELP_TABS
HELP_TABS = [
    ('🚀  Primeros pasos', TAB_01),
    ('📊  La ventana y la tabla', TAB_02),
    ('🔄  Scans y bibliotecas', TAB_03),
    ('🩺  Estado y corrección de problemas', TAB_04),
    ('🖼  Imágenes', TAB_05),
    ('⭐  Calificaciones, géneros e IDs', TAB_06),
    ('🛠  Herramientas y Reparación automática', TAB_07),
    ('🗂  Colecciones', TAB_08),
    ('🕘  Copias de seguridad y deshacer', TAB_09),
    ('📺  Servidores multimedia', TAB_10),
    ('⚙️  Configuración', TAB_11),
    ('⌨  Atajos', TAB_12),
    ('🧰  Solución de problemas', TAB_13),
]
ABOUT_LABEL = 'ℹ️  Acerca de'
