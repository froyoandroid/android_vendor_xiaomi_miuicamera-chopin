# vendor/xiaomi/miuicamera-chopin

MIUI Camera (`com.android.camera` 4.5.002940.0) for the POCO X3 GT (chopin) on
Evolution X `cnb` (Android 17). Source: chopin xiaomi.eu V14.0.7.0.TKPCNXM
(Android 13), pulled from the phone. Enable/disable from the device tree with
`TARGET_SHIPS_MIUICAMERA` (default `true`).

| Path | What | Install |
|---|---|---|
| `proprietary/system_ext/priv-app/MiuiCamera/MiuiCamera.apk` | stock APK with A17 smali fixes (`apkpatch/`), re-signed with `platform` at build, overrides Aperture | `/system_ext/priv-app/MiuiCamera` |
| `proprietary/system_ext/lib64/libcamera_{algoup,mianode,ispinterface}_jni.xiaomi.so` | stock JNI libs, **pre-patched** by `patch-blobs.py` | `/system_ext/lib64` |
| `proprietary/system_ext/lib64/libmtkisp_metadata_sys.so` | stock A13 `/system/lib64` copy (ispinterface dep) | `/system_ext/lib64` |
| `proprietary/system_ext/lib64/vendor.mediatek.hardware.camera.isphal@1.0.so` | stock A13 `/system/lib64` HIDL client (ispinterface dep) | `/system_ext/lib64` |
| `configs/privapp-permissions-miuicamera.xml` | stock privapp allowlist for the app | `/system_ext/etc/permissions` |
| `miuicamera.mk` | packages + props | inherited by `device/xiaomi/chopin` |

## Surface vtable patch
Each JNI lib makes one virtual call on `android::Surface` that targeted the
A13 `connect(int, sp<IProducerListener>[, bool])` slot (0x158 / 0x150). On A17
those slots are `detachNextBuffer` and `connect(int, sp<SurfaceListener>&, ...)`.
All three are retargeted to `connect(int api)` (slot 0xb8):

| lib | offset | stock | patched |
|---|---|---|---|
| libcamera_algoup_jni.xiaomi.so | 0x6278 | `08ad40f9` ldr x8,[x8,#0x158] | `085d40f9` ldr x8,[x8,#0xb8] |
| libcamera_mianode_jni.xiaomi.so | 0xf878 | `08ad40f9` ldr x8,[x8,#0x158] | `085d40f9` ldr x8,[x8,#0xb8] |
| libcamera_ispinterface_jni.xiaomi.so | 0xafac | `08a940f9` ldr x8,[x8,#0x150] | `085d40f9` ldr x8,[x8,#0xb8] |

`python3 patch-blobs.py --verify` checks the committed libs;
`python3 patch-blobs.py <stock lib64 dir>` re-creates them (refuses unless the
inputs are the exact stock files); `--check-header <Surface.h>` re-derives the
slot of `connect(int)` and fails if it is no longer 0xb8. Re-check whenever
`frameworks/native/libs/gui/include/gui/Surface.h` changes.

Do **not** use the 0x158 -> 0x150 variant some ports use: on A17 slot 0x150
calls `listener->needsDeathNotify()` (SurfaceListener vtable +0x38) on the MIUI
`IProducerListener` object, which is a different class.

## Placement
`/system_ext/priv-app` (bundled) rather than `/product/priv-app`: on A15+ product
is always treblelized, so a product app gets an isolated `product-clns`
namespace and only reaches extended/vendor public libraries listed in its
`<uses-native-library>`. This APK targets SDK 31 and declares none (its
`<uses-library>` entries are not native-library declarations), so a
`public.libraries-xiaomi.txt` would be filtered out to nothing. A bundled app's
namespace is shared with the system default namespace (`/system/lib64`,
`/system_ext/lib64`), which matches how the stock app loaded these libs.

Vendor side (in device/xiaomi/mt6893-common): `same_process_hal_file` labels for
the in-app MIA engine (`libmialgoengine*`, plugins, deps), `/vendor/etc/public.libraries.txt`
(libOpenCL), `ro.camera.atms_factor.enabled`. Cameraserver ATMs hook:
`patches/frameworks/av/0002-*`.

## APK smali fixes
`apkpatch/patch-apk.sh <stock MiuiCamera.apk>` rebuilds the committed APK with
`CHOPIN_FINAL=1 CHOPIN_ROM=1` (p.py is the source of truth): A17
StreamConfigurationMap and TotalCaptureResult ctors, MtkBoostFramework /
ProcessManager / HapticFeedbackUtil stubs. The module-only all-intra I-frame
override is skipped: frameworks/av accepts fractional I-frame intervals.

## Sepolicy
`BoardConfigVendor.mk` (included by device/xiaomi/chopin) adds
`sepolicy/vendor`: /dev/apusys for platform_app(_36), hal_mtk_bgs client,
app_data_file execute (qigsaw splits), libneuron_adapter as
same_process_hal_file, cl_apu_status as proc_thermal, and a dedicated prop type
for vendor.debug.appcontrol.name.
