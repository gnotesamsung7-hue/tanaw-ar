package app.tanaw.ar

import java.net.URI

/** What the scanner should do with a decoded QR payload. */
sealed class ScanAction {
    /** A link to our own AR platform: open it straight away. */
    data class OpenAr(val url: String) : ScanAction()
    /** Some other web link: ask the user before opening it. */
    data class ConfirmExternal(val url: String, val host: String) : ScanAction()
    /** Not a web link (plain text, Wi-Fi config, etc.): just show it. */
    data class ShowText(val text: String) : ScanAction()
}

/**
 * Decides how to treat a scanned code. Kept free of Android classes so it can be unit tested.
 *
 * Only https links on [arHost] under [arPathPrefix] are trusted and opened without asking,
 * which stops a sticker placed over your QR code from silently sending people to another site.
 */
class LinkPolicy(private val arHost: String, private val arPathPrefix: String) {

    fun classify(raw: String): ScanAction {
        val text = raw.trim()
        val uri = try { URI(text) } catch (e: Exception) { null }
        val scheme = uri?.scheme?.lowercase()
        val host = uri?.host?.lowercase()

        if (uri == null || host.isNullOrEmpty() || (scheme != "https" && scheme != "http")) {
            return ScanAction.ShowText(text)
        }
        val path = uri.rawPath ?: "/"
        val trusted = scheme == "https" &&
            host == arHost.lowercase() &&
            uri.port.let { it == -1 || it == 443 } &&
            uri.userInfo == null &&
            (path + "/").startsWith(arPathPrefix)
        return if (trusted) ScanAction.OpenAr(text) else ScanAction.ConfirmExternal(text, host)
    }
}
