plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

android {
    namespace = "com.githubai.tradingagents"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.githubai.tradingagents"
        minSdk = 26
        targetSdk = 35
        versionCode = 3
        versionName = "0.3.0"
    }

    // Keep Java and Kotlin bytecode targets aligned to avoid
    // "Inconsistent JVM-target compatibility" during assembleDebug.
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}
