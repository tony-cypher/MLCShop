"""One-time helper: download a small, commercially-licensed photo for every
seeded product from the Openverse API (https://api.openverse.org) and save it to
``frontend/public/img/products/<slug>.<ext>``.

Idempotent — existing files are skipped, so it can be re-run safely.

Usage::

    cd backend
    python scripts/fetch_product_images.py
"""

from __future__ import annotations

import time
from pathlib import Path

import httpx

OUT_DIR = Path(__file__).resolve().parents[2] / "frontend" / "public" / "img" / "products"

API = "https://api.openverse.org/v1/images/"
PACE_SECONDS = 3.4  # stay under the anonymous burst limit (20/min)
UA = "MLC-Shop-Demo/1.0 (local development; image seeding)"
HEADERS = {"User-Agent": UA}

# slug => search query (brand-neutral for better hits)
QUERIES: dict[str, str] = {
    "smart-watch-wh22-6-fitness-tracker": "smartwatch",
    "tennis-rackets-for-beginners": "tennis racket",
    "premium-boxing-gloves-for-pro-training": "boxing gloves",
    "club-kit-1-recurve-archery-bow": "archery bow",
    "lightweight-white-nike-training-shoes": "running shoes",
    "pro-grip-badminton-shuttlecocks-12-pack": "badminton shuttlecock",
    "adidas-training-duffel-bag": "sports bag",
    "asics-gel-quantum-running-shoes": "trainers shoes",
    "adjustable-dumbbell-set-20-kg": "dumbbells",
    "nike-white-thermo-fit-pullover-training-hoodie": "hoodie",
    "columbia-rapid-shield-windbreaker": "jacket",
    "adidas-originals-graphic-tee": "t-shirt",
    "new-balance-574-classic-sneakers": "sneakers",
    "asics-sportstyle-running-cap": "cap hat",
    "columbia-steens-fleece-pullover": "wool sweater",
    "xiaomi-mi-smart-body-scale": "bathroom scale",
    "aroma-mist-diffuser-lamp": "aroma diffuser",
    "resistance-bands-set-5-pieces": "resistance band",
    "insulated-steel-water-bottle-750ml": "water bottle",
    "minimalist-led-desk-lamp": "desk lamp",
    "ceramic-nonstick-cookware-set-5-pc": "pots and pans",
    "cozy-knit-throw-blanket": "knitted blanket",
    "botanical-scented-candle-trio": "scented candle",
    "wireless-studio-headphones-pro": "wireless headphones",
    "acoustic-guitar-starter-kit": "acoustic guitar",
    "portable-bluetooth-speaker-splashproof": "bluetooth speaker",
    "rgb-mechanical-gaming-keyboard": "computer keyboard",
    "pro-wireless-controller-gamepad": "game controller",
    "ultralight-gaming-mouse-8k": "computer mouse",
    "watercolor-paint-set-36-colors": "watercolor paint",
    "adjustable-wooden-canvas-easel": "easel painting",
    "secure-element-hardware-wallet": "usb flash drive",
    "crypto-trader-enamel-mug": "mug cup",
}

EXTENSIONS = (".jpg", ".jpeg", ".png", ".webp")


def extension_for(content_type: str | None) -> str:
    if content_type and "png" in content_type:
        return ".png"
    if content_type and "webp" in content_type:
        return ".webp"
    return ".jpg"


def get_with_retry(client: httpx.Client, url: str, tries: int = 3) -> httpx.Response:
    for attempt in range(1, tries + 1):
        try:
            response = client.get(url, headers=HEADERS, follow_redirects=True)
            if response.status_code == 429:
                print("   rate limited, waiting 30s…")
                time.sleep(30)
                continue
            response.raise_for_status()
            return response
        except httpx.HTTPError:
            if attempt == tries:
                raise
            time.sleep(2 * attempt)
    raise RuntimeError("unreachable")


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    failures: list[str] = []
    total = len(QUERIES)

    with httpx.Client(timeout=30.0) as client:
        for done, (slug, query) in enumerate(QUERIES.items(), start=1):
            print(f"[{done}/{total}] {slug} — \"{query}\"")

            # Existing files (any extension) are kept.
            if any((OUT_DIR / f"{slug}{ext}").exists() for ext in EXTENSIONS):
                print("   already downloaded, skipping")
                continue

            saved = None
            try:
                search_url = str(
                    httpx.URL(
                        API,
                        params={
                            "q": query,
                            "license_type": "commercial",
                            "size": "small",
                            "page_size": 8,
                        },
                    )
                )
                response = get_with_retry(client, search_url)
                time.sleep(PACE_SECONDS)

                for candidate in response.json().get("results", [])[:5]:
                    thumbnail = candidate.get("thumbnail")
                    if not thumbnail:
                        continue
                    try:
                        thumb = get_with_retry(client, thumbnail)
                        content = thumb.content
                        if len(content) < 1024:
                            raise ValueError("suspiciously small file")

                        ext = extension_for(thumb.headers.get("content-type"))
                        (OUT_DIR / f"{slug}{ext}").write_bytes(content)
                        saved = f"{slug}{ext}"
                        license_name = (candidate.get("license") or "unknown").upper()
                        title = candidate.get("title") or "untitled"
                        print(f"   saved {saved}  ({license_name}, {title})")
                        time.sleep(PACE_SECONDS)
                        break
                    except Exception as error:  # noqa: BLE001 - keep going per candidate
                        print(f"   candidate failed: {error}")
                        time.sleep(PACE_SECONDS)
            except Exception as error:  # noqa: BLE001 - keep going per product
                print(f"   search failed: {error}")

            if not saved:
                failures.append(slug)
                print("   !! no usable image")

    print("")
    if failures:
        print(f"Failed ({len(failures)}): {', '.join(failures)}")
        print("Re-run the script to retry just the failures.")
    else:
        print("All product images downloaded.")


if __name__ == "__main__":
    main()
