// SPDX-License-Identifier: Apache-2.0
package org.pixelos.pagani.compat;

import android.app.Activity;
import android.content.Context;
import android.graphics.RenderEffect;
import android.os.Bundle;
import android.view.View;

/** App-local fallback: ColorOS compositor effects are unavailable on AOSP. */
public final class UiCompat {
    private UiCompat() {}
    public static final int USER_SYSTEM = 0;
    public static int myUserId() { return android.os.Process.myUid() / 100000; }
    // Callers pass their TextView's already scaled pixel size.
    public static float getSuitableFontSize(float size, float scale, int level) { return size; }
    public static RenderEffect createGradientBlurEffect(float a, float b, boolean c, float d) { return RenderEffect.createOffsetEffect(0f, 0f); }
    public static RenderEffect createGradientBlurEffect(float a, float b, boolean c, float d,
                                                       int e, int f, int g) { return RenderEffect.createOffsetEffect(0f, 0f); }
    public static RenderEffect createGradientBlurEffect(float a, float b, boolean c, float d,
                                                       int e, int f, int g, RenderEffect input) { return RenderEffect.createOffsetEffect(0f, 0f); }
    // Applying a normal View RenderEffect would blur the document itself rather
    // than the backdrop. Keep the existing flat background instead.
    public static void setBackgroundRenderEffect(RenderEffect effect, View view) {}
    // False selects the callers' ordinary startActivity/launcher fallback.
    public static boolean setSeamlessView(View view, Context context, Bundle options,
                                        AnimationCallback callback) { return false; }
    public static void setSkipViewSeamless(Activity activity) {}
    public static boolean finishCurrentAnimation() { return false; }
    public static class AnimationCallback {
        public AnimationCallback() {}
        public void onAnimationStart(boolean value) {}
        public void onAnimationEnd(boolean value) {}
    }
}
