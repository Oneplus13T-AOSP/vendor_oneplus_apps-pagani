// SPDX-License-Identifier: Apache-2.0
package org.pixelos.pagani.compat;
import android.graphics.Path;
import android.graphics.RectF;
/** Preserve the supplied Path; use AOSP round rectangles without OEM smoothing. */
public final class PathCompat {
    private final Path path;
    public PathCompat(Path path) { this.path = path; }
    public void addSmoothRoundRect(RectF rect, float rx, float ry, Path.Direction direction) {
        path.addRoundRect(rect, rx, ry, direction);
    }
    public void addSmoothRoundRect(RectF rect, float rx, float ry, float smoothing, Path.Direction direction) {
        path.addRoundRect(rect, rx, ry, direction);
    }
    public void addSmoothRoundRect(RectF rect, float[] radii, Path.Direction direction, float smoothing) {
        path.addRoundRect(rect, radii, direction);
    }
    public void addSmoothRoundRect(float left, float top, float right, float bottom,
                                   float rx, float ry, float smoothing, Path.Direction direction) {
        path.addRoundRect(left, top, right, bottom, rx, ry, direction);
    }
}
