# MacPilot 앱 아이콘

`app-icon.png`는 앱 번들과 권한 드래그 패널에서 사용하는 1024×1024 RGBA 원본이다. `scripts/build.sh`가 표준·Retina 표현을 포함한 `MacPilot.icns`를 생성한다. Plugin에는 PNG 원본을 포함하며 일반 사용자는 첫 실행에서 검증한 배포 앱을 내려받는다. 소스 개발 시에만 앱을 로컬에서 빌드한다.

2026-10-17에 내장 `image_gen`으로 새 이미지를 생성했다. 결과는 1254×1254 RGBA였으며 macOS `sips`로 1024×1024로 축소했다. 별도 외부 이미지나 로고는 입력하지 않았다. 아래는 실제 생성 프롬프트다.

```text
Use case: logo-brand. Asset type: production macOS application icon for MacPilot, a native desktop automation utility. Create ONE centered square app icon, 1024 by 1024 canvas. Subject: a single bold, instantly legible white desktop pointer arrow integrated with a subtle compass/navigation motif, expressing precise control and a pilot. The arrow is the dominant silhouette, not a mouse device, not a paper airplane. Style: refined native macOS app icon, softly rounded square tile, restrained tactile depth and gentle highlights, simple clean geometry, polished professional utility. Tile color: deep blue transitioning slightly to teal; white pointer, very small restrained cyan navigation detail. Framing: the rounded-square tile fills about 90 percent of the square canvas, evenly centered; genuine transparent outer corners and margins. Keep the symbol within a safe inner area, large enough to read at 16 and 32 pixels. No text, letters, numerals, Apple logo, robot, face, wings, badges, tiny controls, UI screenshot, or mockup sheet. No checkerboard background. No surrounding scenery. Deliver only the finished app icon with transparent background.
```
