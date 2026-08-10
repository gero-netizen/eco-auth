allprojects {
    repositories {
        google()
        mavenCentral()
    }
}

val newBuildDir: Directory =
    rootProject.layout.buildDirectory
        .dir("../../build")
        .get()
rootProject.layout.buildDirectory.value(newBuildDir)

subprojects {
    val newSubprojectBuildDir: Directory = newBuildDir.dir(project.name)
    project.layout.buildDirectory.value(newSubprojectBuildDir)
}

// CameraX 1.6 references CallbackToFutureAdapter in its public API, but the
// current Flutter camera plugin does not expose that artifact on its Java
// compile classpath when built with AGP 9. Add the missing AndroidX dependency
// only to the affected plugin until upstream includes it directly.
subprojects {
    afterEvaluate {
        if (name == "camera_android_camerax") {
            dependencies.add(
                "implementation",
                "androidx.concurrent:concurrent-futures:1.3.0",
            )
        }
    }
}

subprojects {
    project.evaluationDependsOn(":app")
}

tasks.register<Delete>("clean") {
    delete(rootProject.layout.buildDirectory)
}
