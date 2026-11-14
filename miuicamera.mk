#
# SPDX-FileCopyrightText: 2026 Firenza
# SPDX-License-Identifier: Apache-2.0
#
# MIUI Camera for chopin. Inherited by device/xiaomi/chopin/device.mk when
# TARGET_SHIPS_MIUICAMERA is true (the default); set it to false to fall back
# to Aperture.
#

PRODUCT_SOONG_NAMESPACES += \
    vendor/xiaomi/miuicamera-chopin

PRODUCT_PACKAGES += \
    MiuiCamera

# System-side deps of libcamera_ispinterface_jni.xiaomi that EvoX does not
# install on /system (libmedia and libxml2 already are; libhidltransport is
# only installed for vendor). libhidltransport is built from source
# (system/libhidl); the two below are stock prebuilts.
PRODUCT_PACKAGES += \
    libhidltransport \
    libmtkisp_metadata_sys \
    vendor.mediatek.hardware.camera.isphal@1.0-system

# Properties read by the app.
#  - persist.vendor.camera.privapp.list: EvoX's framework/cameraserver patches
#    skip the stream-size check for these packages (custom 64MP/QCFA sizes).
#  - ro.product.mod_device: "_global" makes the app's IS_INTERNATIONAL_BUILD
#    true (POCO global feature set). Nothing else in our tree reads it from a
#    domain that can see it.
#  - ro.miui.notch: Display.isNotchDevice / miuix AlertController layout.
PRODUCT_SYSTEM_EXT_PROPERTIES += \
    persist.vendor.camera.privapp.list=com.android.camera \
    ro.miui.notch=1 \
    ro.product.mod_device=chopin_global
