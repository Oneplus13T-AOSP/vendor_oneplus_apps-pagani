// SPDX-License-Identifier: Apache-2.0
package org.pixelos.pagani.compat;
/** App-local adapter to the actual Android property service. */
public final class OplusSystemProperties {
    public static String get(String key, String fallback) {
        try { return (String) Class.forName("android.os.SystemProperties").getMethod("get", String.class, String.class).invoke(null, key, fallback); }
        catch (ReflectiveOperationException | RuntimeException e) { return fallback; }
    }
    public static boolean getBoolean(String key, boolean fallback) {
        String v = get(key, "");
        if (v.isEmpty()) return fallback;
        if (v.equals("1") || v.equalsIgnoreCase("true") || v.equalsIgnoreCase("yes") || v.equalsIgnoreCase("on") || v.equalsIgnoreCase("y")) return true;
        if (v.equals("0") || v.equalsIgnoreCase("false") || v.equalsIgnoreCase("no") || v.equalsIgnoreCase("off") || v.equalsIgnoreCase("n")) return false;
        return fallback;
    }
    public static int getInt(String key, int fallback) { try { return Integer.parseInt(get(key, "")); } catch (NumberFormatException e) { return fallback; } }
    public static long getLong(String key, long fallback) { try { return Long.parseLong(get(key, "")); } catch (NumberFormatException e) { return fallback; } }
}
