# mac-cu app icon

- Generator: built-in `image_gen.imagegen`, `transparent_background: true`. No external CLI/API generation.
- Asset: `assets/mac-cu-icon.png` (1024 × 1024 RGBA PNG). The rounded blue tile contains a Mac display and a pointer/touch mark; the canvas corners are transparent.
- The built-in output was 1254 × 1254; macOS `sips` normalized it to the canonical 1024 × 1024 source without changing the composition. `setup.py` derives the icon sizes with `sips` and packages `Resources/AppIcon.icns` with `iconutil` during the build.

## Final prompt

```text
Use case: logo-brand
Asset type: one original macOS application icon for mac-cu, 1024 by 1024 pixels.
Primary request: Create a premium macOS app icon that clearly represents controlling a Mac screen with a touch or pointer. One single centered icon, no alternate variants and no presentation mockup.
Subject: a bold simple white Mac display silhouette with a compact dark-blue screen and one crisp white cursor/touch symbol, placed on a deep sapphire blue rounded-square squircle tile. Use very few large shapes so the icon remains recognizable at 16 and 32 pixels. A small restrained cyan highlight may provide depth. The display and input symbol should form one coherent mark rather than several separate objects.
Style: polished native macOS app icon, tactile but restrained, smooth surfaces, carefully balanced optical weight, subtle soft lighting and clean edges.
Composition: front-facing, centered, large simple symbol with generous edge clearance. The rounded-square tile fits within the 1024 square with natural macOS icon margins. The tile itself is opaque. Everything outside its rounded silhouette must be genuinely transparent alpha, including the outer canvas corners; do not simulate transparency with a checkerboard or a painted background.
Constraints: original artwork only; no text, letters, numbers, brand logos, watermark, robots, hands, decorative props, multiple panels, busy texture or small details.
```
