# IPTV-LATINO-LEGAL

Generador inicial de listas M3U para contenido cuya redistribución está autorizada. Diseñado para Windows 11 y publicación estática en GitHub Pages.

## Principios
- No descarga ni aloja películas; solo organiza URLs directas autorizadas.
- No infiere idioma por el título. Exige `audio_language: "es-419"` y `audio_verified: true`.
- No publica elementos sin `rights_verified: true`, licencia y evidencia.
- La comprobación HTTP solo comprueba accesibilidad básica; **no demuestra que el video sea reproducible ni que tenga audio latino**.
- La revisión de licencia y audio es humana. Para verificar la pista real se recomienda inspeccionar el archivo con MediaInfo o FFprobe.

## Windows 11: instalación
1. Instala Python 3.11 o superior desde https://www.python.org/downloads/windows/ y marca **Add Python to PATH**.
2. Descomprime el ZIP en `C:\IPTV-LATINO-LEGAL`.
3. Abre Terminal o PowerShell en esa carpeta.
4. Ejecuta:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Si PowerShell bloquea la activación, usa:
```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
O ejecuta directamente `.\.venv\Scripts\python.exe main.py`.

## Añadir contenido
Edita `database/catalog.json`. Cada elemento debe incluir:
- `type`: `movie` o `episode`
- `category`: `movies`, `series`, `anime` o `cartoons`
- `url`: URL directa HTTP(S) del archivo o stream autorizado
- `audio_language`: `es-419`
- `audio_verified`: `true` solo después de escuchar/verificar la pista
- `audio_verification_method`: evidencia, por ejemplo `MediaInfo: pista AAC Spanish (Latin America), escuchada`
- `license`, `license_url`, `rights_verified`, `rights_notes`
- Para episodios: `season`, `episode`, `series_name`

No marques `rights_verified: true` hasta comprobar que la licencia o autorización permite la redistribución del enlace/obra. La licencia del código del repositorio no concede derechos sobre los videos.

## Generar listas localmente
Con el entorno virtual activado:
```powershell
python main.py
```
Prueba sin consultar los enlaces:
```powershell
python main.py --no-network
```

Se crean:
- `playlists/movies.m3u`
- `playlists/series.m3u`
- `playlists/anime.m3u`
- `playlists/cartoons.m3u`
- `playlists/all.m3u`
- `reports/validation_report.json`

Los elementos que no pasan todos los controles se excluyen de las listas.

## Publicar en GitHub Pages
1. Crea un repositorio GitHub vacío llamado `IPTV-LATINO-LEGAL`.
2. Copia el contenido de esta carpeta al repositorio y haz `git push` a la rama `main`.
3. En GitHub, abre **Settings → Actions → General** y permite Actions.
4. En **Settings → Pages**, configura publicación desde la rama `gh-pages` y carpeta `/ (root)` si Pages no se activa automáticamente.
5. Ejecuta el workflow **Actions → Build authorized playlists → Run workflow**.
6. Tras completarse, las listas estarán en:
   `https://TU-USUARIO.github.io/IPTV-LATINO-LEGAL/movies.m3u`
   `https://TU-USUARIO.github.io/IPTV-LATINO-LEGAL/series.m3u`
   `https://TU-USUARIO.github.io/IPTV-LATINO-LEGAL/anime.m3u`
   `https://TU-USUARIO.github.io/IPTV-LATINO-LEGAL/cartoons.m3u`
   `https://TU-USUARIO.github.io/IPTV-LATINO-LEGAL/all.m3u`

GitHub Pages publica el índice M3U, no los archivos audiovisuales. Los servidores de origen deben permitir el acceso desde el reproductor y autorizar la distribución.

## Limitaciones de esta versión
- La comprobación de enlaces usa HEAD y, si es necesario, una petición GET con rango. Algunos servidores bloquean ambas aunque el reproductor pueda acceder.
- No hace reconocimiento automático de voz ni certifica audio latino. Se requiere comprobación de pista y escucha.
- M3U estándar no garantiza agrupación de temporadas en IPTV Smarters. Para la siguiente fase se añadirá una API Xtream compatible, con categorías y episodios.
- TMDB aporta metadatos, no derechos de reproducción. Respeta sus condiciones y configura tu propia API key si se añade integración.

## Seguridad
No publiques tokens, contraseñas, claves privadas ni listas de acceso restringido en el repositorio. Usa GitHub Secrets para credenciales de servicios.
