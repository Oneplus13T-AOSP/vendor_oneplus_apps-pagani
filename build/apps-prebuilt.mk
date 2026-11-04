# SPDX-License-Identifier: Apache-2.0

# Keep native libraries private to each normal product app. Do not publish ELF
# files through PRODUCT_COPY_FILES or install them to a global lib64 directory.
define pagani-native-app-prebuilt
include $$(CLEAR_VARS)
LOCAL_MODULE := $(1)
LOCAL_MODULE_CLASS := APPS
LOCAL_MODULE_SUFFIX := $$(COMMON_ANDROID_PACKAGE_SUFFIX)
LOCAL_MODULE_TAGS := optional
LOCAL_PRODUCT_MODULE := true
LOCAL_MODULE_TARGET_ARCH := arm64
LOCAL_MULTILIB := 64
LOCAL_CERTIFICATE := platform
LOCAL_DEX_PREOPT := false
LOCAL_ENFORCE_USES_LIBRARIES := true
LOCAL_OPTIONAL_USES_LIBRARIES := $(2)
LOCAL_SRC_FILES := proprietary/product/app/$(1)/$(1).apk
LOCAL_PREBUILT_JNI_LIBS := $$(patsubst $$(LOCAL_PATH)/%,%,$$(wildcard $$(LOCAL_PATH)/proprietary/native/$(1)/*.so))
ifeq ($$(strip $$(LOCAL_PREBUILT_JNI_LIBS)),)
$$(error $(1): missing JNI payload; run extract-files.py as documented)
endif
include $$(BUILD_PREBUILT)
endef

ifeq ($(TARGET_ENABLE_PAGANI_APPS),true)
ifeq ($(TARGET_ENABLE_SONY_MUSIC),true)
$(eval $(call pagani-native-app-prebuilt,SemcMusicApp,org.apache.http.legacy androidx.window.extensions androidx.window.sidecar android.ext.adservices))
endif
endif
