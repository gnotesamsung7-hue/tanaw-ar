package app.tanaw.ar

import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Test

class LinkPolicyTest {
    private val policy = LinkPolicy("mark.github.io", "/tanaw-ar/")

    @Test fun ourArLinkOpensDirectly() {
        val url = "https://mark.github.io/tanaw-ar/view.html?id=astronaut"
        assertEquals(ScanAction.OpenAr(url), policy.classify(url))
    }

    @Test fun hostMatchIgnoresCase() {
        assertTrue(policy.classify("https://Mark.GitHub.io/tanaw-ar/view.html?id=x") is ScanAction.OpenAr)
    }

    @Test fun plainHttpIsNotTrusted() {
        assertTrue(policy.classify("http://mark.github.io/tanaw-ar/view.html") is ScanAction.ConfirmExternal)
    }

    @Test fun lookalikeHostIsNotTrusted() {
        assertTrue(policy.classify("https://mark.github.io.evil.com/tanaw-ar/") is ScanAction.ConfirmExternal)
        assertTrue(policy.classify("https://mark.github.io@evil.com/tanaw-ar/") is ScanAction.ConfirmExternal)
    }

    @Test fun otherPathOnSameHostAsks() {
        assertTrue(policy.classify("https://mark.github.io/other-project/") is ScanAction.ConfirmExternal)
    }

    @Test fun nonLinksAreShownAsText() {
        assertTrue(policy.classify("PSU-450W SN 24-08813") is ScanAction.ShowText)
        assertTrue(policy.classify("WIFI:S:Office;T:WPA;P:secret;;") is ScanAction.ShowText)
    }
}
