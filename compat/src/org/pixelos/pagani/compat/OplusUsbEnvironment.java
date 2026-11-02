// SPDX-License-Identifier: Apache-2.0
package org.pixelos.pagani.compat;
import android.content.Context;
import android.os.Environment;
import android.os.storage.StorageManager;
import android.os.storage.StorageVolume;
import java.io.File;
import java.util.ArrayList;
import java.util.List;
/** pagani storage adapter: real primary shared storage and mounted removable volumes. */
public final class OplusUsbEnvironment {
    public static String getInternalPath(Context context) {
        return Environment.getExternalStorageDirectory().getAbsolutePath();
    }
    // OnePlus 13T has no built-in SD-card slot; USB volumes are exposed separately.
    public static String getExternalPath(Context context) { return null; }
    public static List<String> getOtgPath(Context context) {
        List<String> result = new ArrayList<>();
        if (context == null) return result;
        StorageManager manager = context.getSystemService(StorageManager.class);
        if (manager == null) return result;
        for (StorageVolume volume : manager.getStorageVolumes()) {
            File directory = volume.getDirectory();
            if (!volume.isPrimary() && volume.isRemovable() && directory != null
                    && Environment.MEDIA_MOUNTED.equals(volume.getState())) {
                result.add(directory.getAbsolutePath());
            }
        }
        return result;
    }
}
