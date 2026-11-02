# SPDX-License-Identifier: Apache-2.0
# Inherited by device/oneplus/pagani/device.mk:
# $(call inherit-product, vendor/oneplus/apps-pagani/apps.mk)
TARGET_ENABLE_PAGANI_APPS ?= true
TARGET_ENABLE_PAGANI_DOCUMENTS ?= true
TARGET_ENABLE_PAGANI_SCANNER ?= true
TARGET_ENABLE_PAGANI_IRREMOTE ?= true
TARGET_ENABLE_SONY_MUSIC ?= true

ifeq ($(TARGET_ENABLE_PAGANI_APPS),true)
$(call inherit-product, vendor/oneplus/apps-pagani/apps-pagani-vendor.mk)
ifeq ($(TARGET_ENABLE_PAGANI_DOCUMENTS),true)
PRODUCT_PACKAGES += OplusDocumentsReader
endif
ifeq ($(TARGET_ENABLE_PAGANI_SCANNER),true)
PRODUCT_PACKAGES += OcrScanner
endif
ifeq ($(TARGET_ENABLE_PAGANI_IRREMOTE),true)
PRODUCT_PACKAGES += ConsumerIRApp
endif
ifeq ($(TARGET_ENABLE_SONY_MUSIC),true)
PRODUCT_PACKAGES += SemcMusicApp
endif
endif
