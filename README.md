# Tanaw AR

Scan a QR code with the Android app → it opens your own AR web platform → the viewer places a 3D model in the room.

```
QR code  ──►  Tanaw AR app (CameraX + ML Kit)  ──►  Chrome Custom Tab
             checks the link is yours               https://you.github.io/tanaw-ar/view.html?id=astronaut
                                                     └─ model-viewer → WebXR / Scene Viewer (Android), Quick Look (iPhone)
```

The web platform also works without the app: any phone camera can scan the QR and open the same page. The app gives you a branded scanner, faster scanning and a check that blocks links to other sites.

## Folder layout

| Path | What it is |
|---|---|
| `web/view.html` | AR viewer. Reads `?id=` and loads that experience. |
| `web/experiences.json` | Your catalog of experiences (title, model, placement, button). |
| `web/index.html` | Lists every experience with a printable QR code. |
| `web/models/` | Put your own `.glb` / `.usdz` files here. |
| `android/` | Android Studio project for the scanner app. |

## 1. Host the web platform (free, about 10 minutes)

AR and the camera only work over HTTPS, so the page needs a real web host. GitHub Pages is free:

1. Create a GitHub repo called `tanaw-ar` and upload the contents of `web/`.
2. Repo **Settings → Pages → Deploy from branch → main / root**.
3. After a minute it's live at `https://YOUR-USERNAME.github.io/tanaw-ar/`.
4. Open that address on a computer to see the QR code for each experience.

Netlify or Cloudflare Pages also work: drag the `web` folder onto their dashboard.

## 2. Build the Android app

1. Open the `android` folder in Android Studio (Narwhal or newer). Let it sync. If it asks to set up the Gradle wrapper or upgrade the Android Gradle Plugin, accept.
2. In `app/build.gradle.kts`, set:
   ```kotlin
   val arHost = "YOUR-USERNAME.github.io"
   val arPathPrefix = "/tanaw-ar/"
   ```
3. Plug in an Android phone with USB debugging on, then press **Run**.
4. Scan a code from `index.html`. It opens straight into the viewer. Tap **View in your space**.

Run the link-safety tests with **Gradle → app → verification → testDebugUnitTest**, or `./gradlew test`.

## 3. Add your own experience

1. Export your model as `.glb` (Blender: File → Export → glTF 2.0). Units are meters.
2. Put it in `web/models/`.
3. Add an entry to `experiences.json`:
   ```json
   {
     "id": "psu-demo",
     "title": "Power supply demo",
     "description": "Place the unit on your desk to check its size.",
     "model": "models/psu-demo.glb",
     "iosModel": "models/psu-demo.usdz",
     "placement": "floor",
     "scale": "fixed",
     "cta": { "label": "Datasheet", "url": "https://..." }
   }
   ```
   `placement`: `floor` or `wall`. `scale`: `fixed` keeps real size; `auto` lets people pinch to resize.
4. Push to GitHub. The new QR code appears on `index.html`.

## How the scanner decides what to do

| Scanned code | App behaviour |
|---|---|
| `https://` link on your host, under your path | Opens the AR viewer immediately |
| Any other web link (including `http://` or lookalike domains) | Asks before opening and shows the domain |
| Plain text, Wi-Fi codes, serial numbers | Shows the text with a Copy button |

It opens links in a Chrome Custom Tab rather than a WebView, because a WebView can't run WebXR or hand off to Google's Scene Viewer.

## Device support

- **Android:** needs a phone that supports Google Play Services for AR (most mid-range and up since 2019). Without it, the viewer still shows the 3D model and people can rotate it, but not place it in the room.
- **iPhone:** the web page works in Safari through Quick Look. Add a `.usdz` file for best results.

## Before publishing to Play Store

- Change `applicationId` from `app.tanaw.ar` to your own permanent ID.
- Replace the launcher icon if you want your own branding.
- Play Console needs: a privacy policy URL (camera is used on-device only, no images uploaded), the data-safety form, a 512×512 icon, a feature graphic and screenshots.
- Build a signed bundle: **Build → Generate Signed App Bundle**.
- New personal developer accounts must run a closed test with at least 12 testers for 14 days before production.

## XP Power 3D logo

`web/models/xp-logo.glb` is built from the official horizontal logo with `tools/build_xp_logo.py`, following the XP Power Brand Guidelines (OMS, 2024): not recoloured, skewed or re-proportioned, using XP Black, XP Bright White and XP Light Grey only. It stands 60 cm wide on a small foot. In AR, pinch to resize and drag to move it.

To rebuild from a higher-resolution logo from the brand library:
```
pip install trimesh shapely mapbox-earcut pillow scikit-image numpy
python tools/build_xp_logo.py xp-logo.png web/models/xp-logo.glb
```
