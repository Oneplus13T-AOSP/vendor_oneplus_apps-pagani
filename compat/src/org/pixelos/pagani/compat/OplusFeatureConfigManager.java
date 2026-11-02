// SPDX-License-Identifier: Apache-2.0
package org.pixelos.pagani.compat;
import org.pixelos.pagani.compat.OplusSystemProperties;
/** Only map hardware facts. Unsupported ColorOS services stay unsupported. */
public final class OplusFeatureConfigManager {
    private static final OplusFeatureConfigManager INSTANCE = new OplusFeatureConfigManager();
    public static OplusFeatureConfigManager getInstance() { return INSTANCE; }
    public boolean hasFeature(String key) {
        if ("oplus.hardware.type.tablet".equals(key)) {
            for (String part : OplusSystemProperties.get("ro.build.characteristics", "").split(",")) {
                if ("tablet".equals(part.trim())) return true;
            }
        }
        return false;
    }
    public boolean hasFeatureIPC(String key) { return hasFeature(key); }
}
