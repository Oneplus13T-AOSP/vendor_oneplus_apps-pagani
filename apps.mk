# SPDX-License-Identifier: Apache-2.0
# Inherited by device/oneplus/pagani/device.mk.
TARGET_ENABLE_PAGANI_APPS ?= true
TARGET_ENABLE_SONY_MUSIC ?= true

ifeq ($(TARGET_ENABLE_PAGANI_APPS),true)
$(call inherit-product, vendor/oneplus/apps-pagani/apps-pagani-vendor.mk)
ifeq ($(TARGET_ENABLE_SONY_MUSIC),true)
PRODUCT_PACKAGES += SemcMusicApp
endif
endif
