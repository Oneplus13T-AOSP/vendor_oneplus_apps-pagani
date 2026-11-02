// SPDX-License-Identifier: Apache-2.0
package org.pixelos.pagani.compat;
/** This ROM has no ColorOS framework API. Do not advertise an OEM API version. */
public final class OplusBuild {
    public static int getOplusOSVERSION() { return 0; }
    public static final class VERSION {
        public static final int SDK_VERSION = 0;
        public static final int SDK_SUB_VERSION = 0;
    }
}
