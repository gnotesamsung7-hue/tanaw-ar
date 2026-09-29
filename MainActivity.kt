package app.tanaw.ar

import android.Manifest
import android.content.ActivityNotFoundException
import android.content.ClipData
import android.content.ClipboardManager
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build
import android.os.Bundle
import android.os.VibrationEffect
import android.os.Vibrator
import android.provider.Settings
import android.view.View
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.browser.customtabs.CustomTabColorSchemeParams
import androidx.browser.customtabs.CustomTabsIntent
import androidx.camera.core.Camera
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import app.tanaw.ar.databinding.ActivityMainBinding
import com.google.android.material.dialog.MaterialAlertDialogBuilder
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors
import java.util.concurrent.atomic.AtomicBoolean

class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding
    private lateinit var cameraExecutor: ExecutorService
    private var analyzer: QrAnalyzer? = null
    private var camera: Camera? = null
    private var torchOn = false

    /** True while we are handling a code, so one QR doesn't fire 30 times a second. */
    private val busy = AtomicBoolean(false)
    private val policy = LinkPolicy(BuildConfig.AR_HOST, BuildConfig.AR_PATH_PREFIX)

    private val askCamera = registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) startCamera() else showPermissionHelp()
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)
        cameraExecutor = Executors.newSingleThreadExecutor()

        binding.torch.setOnClickListener {
            torchOn = !torchOn
            camera?.cameraControl?.enableTorch(torchOn)
            binding.torch.setText(if (torchOn) R.string.torch_off else R.string.torch_on)
        }
        binding.grantButton.setOnClickListener {
            startActivity(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.fromParts("package", packageName, null)))
        }
    }

    override fun onResume() {
        super.onResume()
        busy.set(false) // back from the AR page: ready to scan again
        if (hasCamera()) startCamera() else askCamera.launch(Manifest.permission.CAMERA)
    }

    private fun hasCamera() =
        ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED

    private fun showPermissionHelp() {
        binding.permissionPanel.visibility = View.VISIBLE
        binding.hint.visibility = View.GONE
    }

    private fun startCamera() {
        binding.permissionPanel.visibility = View.GONE
        binding.hint.visibility = View.VISIBLE
        val future = ProcessCameraProvider.getInstance(this)
        future.addListener({
            val provider = future.get()
            val preview = Preview.Builder().build().also {
                it.setSurfaceProvider(binding.preview.surfaceProvider)
            }
            analyzer?.close()
            analyzer = QrAnalyzer { value -> runOnUiThread { onCode(value) } }
            val analysis = ImageAnalysis.Builder()
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .build()
                .also { it.setAnalyzer(cameraExecutor, analyzer!!) }
            provider.unbindAll()
            camera = provider.bindToLifecycle(this, CameraSelector.DEFAULT_BACK_CAMERA, preview, analysis)
            binding.torch.visibility =
                if (camera?.cameraInfo?.hasFlashUnit() == true) View.VISIBLE else View.GONE
        }, ContextCompat.getMainExecutor(this))
    }

    private fun onCode(value: String) {
        if (!busy.compareAndSet(false, true)) return
        buzz()
        when (val action = policy.classify(value)) {
            is ScanAction.OpenAr -> openInCustomTab(action.url)
            is ScanAction.ConfirmExternal -> MaterialAlertDialogBuilder(this)
                .setTitle(R.string.external_title)
                .setMessage(getString(R.string.external_message, action.host, action.url))
                .setPositiveButton(R.string.open) { _, _ -> openInCustomTab(action.url) }
                .setNegativeButton(R.string.cancel) { _, _ -> busy.set(false) }
                .setOnCancelListener { busy.set(false) }
                .show()
            is ScanAction.ShowText -> MaterialAlertDialogBuilder(this)
                .setTitle(R.string.text_title)
                .setMessage(action.text)
                .setPositiveButton(R.string.copy) { _, _ ->
                    getSystemService(ClipboardManager::class.java)
                        .setPrimaryClip(ClipData.newPlainText("QR", action.text))
                    busy.set(false)
                }
                .setNegativeButton(R.string.done) { _, _ -> busy.set(false) }
                .setOnCancelListener { busy.set(false) }
                .show()
        }
    }

    /**
     * Opens the AR page in a Chrome Custom Tab. Custom Tabs run on the phone's real Chrome,
     * so WebXR and Google Scene Viewer work, which a plain WebView does not support.
     */
    private fun openInCustomTab(url: String) {
        val colors = CustomTabColorSchemeParams.Builder()
            .setToolbarColor(ContextCompat.getColor(this, R.color.ink))
            .build()
        val tab = CustomTabsIntent.Builder()
            .setDefaultColorSchemeParams(colors)
            .setShowTitle(true)
            .build()
        try {
            tab.launchUrl(this, Uri.parse(url))
        } catch (e: ActivityNotFoundException) {
            Toast.makeText(this, R.string.no_browser, Toast.LENGTH_LONG).show()
            busy.set(false)
        }
    }

    private fun buzz() {
        val v = getSystemService(Vibrator::class.java) ?: return
        if (Build.VERSION.SDK_INT >= 26) v.vibrate(VibrationEffect.createOneShot(40, VibrationEffect.DEFAULT_AMPLITUDE))
        else @Suppress("DEPRECATION") v.vibrate(40)
    }

    override fun onDestroy() {
        super.onDestroy()
        analyzer?.close()
        cameraExecutor.shutdown()
    }
}
