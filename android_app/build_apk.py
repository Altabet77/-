"""
build_apk.py — يبني APK سمير تلقائياً
يحتاج: JDK17 و Android SDK cmdline-tools محملان مسبقاً
"""
import os, subprocess, sys, shutil, time

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE = r"C:\samir_android" if os.path.exists(r"C:\samir_android") else r"d:\سمير\android_app"
JDK  = os.path.join(BASE, "jdk17", "jdk-17.0.11+9")
SDK  = os.path.join(BASE, "android_sdk")
ANDROID = os.path.join(BASE, "android")
SDKMANAGER = os.path.join(SDK, "cmdline-tools", "latest", "bin", "sdkmanager.bat")

env = os.environ.copy()
env["JAVA_HOME"] = JDK
env["PATH"] = os.path.join(JDK, "bin") + ";" + env.get("PATH", "")
env["ANDROID_HOME"] = SDK
env["ANDROID_SDK_ROOT"] = SDK

def run(cmd, cwd=None, input_text=None):
    print(f"\n>>> {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd, cwd=cwd, env=env,
        input=input_text, capture_output=False,
        text=True, shell=isinstance(cmd, str)
    )
    return result.returncode

print("=" * 60)
print("  سمير APK Builder")
print("=" * 60)

# 1) تحقق من JDK
javac = os.path.join(JDK, "bin", "javac.exe")
if not os.path.exists(javac):
    print(f"ERROR: JDK not found at {javac}")
    sys.exit(1)
print(f"OK JDK: {JDK}")

# 2) تحقق من sdkmanager
if not os.path.exists(SDKMANAGER):
    print(f"ERROR: sdkmanager not found at {SDKMANAGER}")
    sys.exit(1)
print(f"OK SDK: {SDKMANAGER}")

# 3) قبول تراخيص SDK
print("\n-- Accepting SDK licenses --")
p = subprocess.Popen(
    [SDKMANAGER, "--licenses"],
    env=env, stdin=subprocess.PIPE,
    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)
out, _ = p.communicate(input="y\ny\ny\ny\ny\ny\ny\ny\ny\ny\n")
print(out[:500] if out else "(no output)")

# 4) تثبيت Android platform + build-tools
print("\n-- Installing Android platform 34 & build-tools --")
pkgs = [
    "platforms;android-34",
    "build-tools;34.0.0",
    "platform-tools",
]
for pkg in pkgs:
    print(f"  Installing {pkg}...")
    rc = run([SDKMANAGER, "--install", pkg])
    if rc != 0:
        print(f"  WARNING: {pkg} install returned {rc}")

# 5) sync Capacitor
print("\n-- Syncing Capacitor --")
os.chdir(BASE)
run("npx cap sync android", cwd=BASE)

# Ensure local.properties uses clean ASCII path
local_prop = os.path.join(ANDROID, "local.properties")
clean_sdk_path = SDK.replace("\\", "\\\\")
with open(local_prop, "w", encoding="utf-8") as f:
    f.write(f"sdk.dir={clean_sdk_path}\n")
print(f"Wrote clean sdk.dir={clean_sdk_path} to {local_prop}")

# 6) Gradle build
print("\n-- Building APK (assembleDebug) --")
gradlew = os.path.join(ANDROID, "gradlew.bat")
rc = run([gradlew, "assembleDebug", "--stacktrace"], cwd=ANDROID)

if rc != 0:
    print(f"\nERROR: Gradle build failed (exit code {rc})")
    sys.exit(1)

# 7) نسخ APK للمجلد الرئيسي
apk_src = os.path.join(ANDROID, "app", "build", "outputs", "apk", "debug", "app-debug.apk")
apk_dst = r"d:\سمير\samir-android.apk"

if os.path.exists(apk_src):
    shutil.copy2(apk_src, apk_dst)
    size_mb = os.path.getsize(apk_dst) / (1024 * 1024)
    print(f"\n{'='*60}")
    print(f"  APK جاهز: {apk_dst}")
    print(f"  الحجم: {size_mb:.1f} MB")
    print(f"{'='*60}")
else:
    print(f"\nERROR: APK not found at {apk_src}")
    # search for it
    for root, dirs, files in os.walk(ANDROID):
        for f in files:
            if f.endswith(".apk"):
                found = os.path.join(root, f)
                print(f"Found APK at: {found}")
                shutil.copy2(found, apk_dst)
    sys.exit(1)

print("\nDone! Transfer samir-android.apk to your phone and install.")
