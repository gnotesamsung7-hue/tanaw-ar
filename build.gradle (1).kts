plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

// ---- Change these two lines to point at your hosted AR web platform ----
val arHost = "gnotesamsung7-hue.github.io"
val arPathPrefix = "/tanaw-ar/"
// ------------------------------------------------------------------------

android {
    namespace = "app.tanaw.ar"
    compileSdk = 36

    defaultConfig {
        applicationId = "app.tanaw.ar" // change before publishing, it can't be changed later
        minSdk = 26
        targetSdk = 36
        versionCode = 1
        versionName = "1.0"
        buildConfigField("String", "AR_HOST", "\"$arHost\"")
        buildConfigField("String", "AR_PATH_PREFIX", "\"$arPathPrefix\"")
    }

    buildTypes {
        release {
            isMinifyEnabled = true
            proguardFiles(getDefaultProguardFile("proguard-android-optimize.txt"), "proguard-rules.pro")
        }
    }
    buildFeatures {
        viewBinding = true
        buildConfig = true
    }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
}

dependencies {
    val camerax = "1.4.2"
    implementation("androidx.camera:camera-camera2:$camerax")
    implementation("androidx.camera:camera-lifecycle:$camerax")
    implementation("androidx.camera:camera-view:$camerax")
    implementation("com.google.mlkit:barcode-scanning:17.3.0")
    implementation("androidx.browser:browser:1.8.0")
    implementation("androidx.core:core-ktx:1.16.0")
    implementation("androidx.appcompat:appcompat:1.7.1")
    implementation("androidx.activity:activity-ktx:1.10.1")
    implementation("com.google.android.material:material:1.12.0")
    testImplementation("junit:junit:4.13.2")
}
