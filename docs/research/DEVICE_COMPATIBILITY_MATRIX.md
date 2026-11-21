
# GhostOS Device Compatibility Matrix

Document ID: GOS-RESEARCH-001
Device: POCO X4 Pro 5G (India)
Model: 2201116PI
Device codename: peux
Reported board: veux
SoC: Qualcomm SM6375 (Snapdragon 695)
Architecture: ARM64
Current Android version: Android 13
Current kernel: 5.4.274-qgki

Status: RESEARCH IN PROGRESS
Last reviewed: 2026-11-11

## 1. Purpose

Evaluate the feasibility of running GhostOS on the exact Indian
POCO X4 Pro 5G variant without modifying the phone during this phase.

## 2. Verified Device Identity

| Property | Value | Evidence |
|---|---|---|
| Model | 2201116PI | Device inspection |
| Device codename | peux | Device inspection |
| Board property | veux | Device inspection |
| SoC | Qualcomm SM6375 | Device inspection |
| Architecture | ARM64 | Device inspection |
| Android | 13 | Device inspection |
| Kernel | 5.4.274-qgki | Device inspection |

Important: peux and veux must not be treated as interchangeable
without checking their hardware and firmware differences.

## 3. Candidate Software Foundations

| Foundation | Current assessment | Status |
|---|---|---|
| Mainline Linux | Hardware support unverified | Investigate |
| postmarketOS | No verified peux port established | Investigate |
| Droidian | Requires device-specific porting assessment | Investigate |
| Ubuntu Touch | No verified peux port established | Investigate |
| Android-derived kernel with Linux userspace | Potentially practical | Investigate |

## 4. Existing Community Resources

| Resource | Purpose | Limitation |
|---|---|---|
| sm6375-devs/android_device_xiaomi_veux | Android device tree | Android-specific |
| sm6375-devs/android_kernel_xiaomi_sm6375 | Kernel source | Repository marked discontinued |
| dev-sm6375/kernel_xiaomi_sm6375 | Kernel 5.4 source | Identified as veux |
| Xiaomi SM6375 common device tree | Shared Android configuration | Does not prove native Linux support |

References:
- https://github.com/xiaomi-sm6375-devs/android_device_xiaomi_veux
- https://github.com/xiaomi-sm6375-devs/android_device_xiaomi_sm6375-common
- https://github.com/sm6375-devs/android_kernel_xiaomi_sm6375
- https://github.com/dev-sm6375/kernel_xiaomi_sm6375

## 5. Hardware Compatibility Checklist

| Component | Required investigation | Status |
|---|---|---|
| Boot chain | Boot image, vendor boot, verified boot | Pending |
| Display | Panel, DRM/KMS, framebuffer | Pending |
| Touchscreen | Touch controller and input driver | Pending |
| GPU | Adreno 619 and graphics stack | Pending |
| Wi-Fi | Qualcomm WLAN driver and firmware | Pending |
| Bluetooth | Controller, firmware and userspace | Pending |
| Audio | Codec, DSP and audio routing | Pending |
| Cellular modem | Modem firmware and interface | Pending |
| Camera | Sensors, ISP and camera stack | Pending |
| Sensors | Accelerometer, proximity, gyroscope | Pending |
| Battery | Charging, fuel gauge and thermal controls | Pending |
| USB | USB controller and gadget support | Pending |
| Storage | UFS, partition layout and encryption | Pending |
| Suspend/resume | Power management and wake sources | Pending |
| Fingerprint | Sensor and authentication integration | Pending |

## 6. Security and Recovery Constraints

- Do not unlock the bootloader during this research phase.
- Do not flash boot, vendor_boot, vbmeta or super partitions.
- Do not modify userdata or encryption metadata.
- Do not assume LUKS2 can replace Android file-based encryption.
- Preserve the original Android recovery path.
- Require a documented recovery procedure before any device experiment.
- Never use proprietary firmware without recording its source and licence.

## 7. Required Research Before Foundation Selection

1. Confirm the exact peux versus veux hardware differences.
2. Identify the correct kernel source and branch for 2201116PI.
3. Determine whether the kernel can boot a non-Android Linux userspace.
4. Investigate the Android vendor interface and required proprietary blobs.
5. Evaluate display, touch, Wi-Fi, audio, modem and GPU support.
6. Check whether a maintained mobile shell can run on the target stack.
7. Assess encryption, verified boot and recovery constraints.
8. Build a test plan using emulation and host-side development first.

## 8. Current Conclusion

The device has community Android development resources and an
existing Android-derived kernel ecosystem.

A functional native mobile Linux port has not yet been demonstrated
for the exact 2201116PI Indian variant.

GhostOS foundation selection remains OPEN.

No device modification is authorized by this document.
