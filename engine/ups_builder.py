import os
import json
import re
import time
import urllib.request
import urllib.parse
import urllib.error  # [PEDOMAN LANGKAH 1] wajib untuk menangkap HTTPError 429
from datetime import datetime, timezone

# ==========================================
# ENVIRONMENT CONFIGURATION
# ==========================================
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
SITE_BASE_URL = os.environ.get("SITE_BASE_URL", "https://hanifsalman11.github.io/ups-runtime-index").rstrip("/")
INDEXNOW_KEY = os.environ.get("INDEXNOW_KEY", "f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7").strip()
CUSTOM_UPS = os.environ.get("CUSTOM_UPS", "").strip()
PAGES_PER_RUN = int(os.environ.get("PAGES_PER_RUN", "3"))

DOCS_DIR = "docs"
DATA_DIR = "data"
PUBLISHED_FILE = os.path.join(DATA_DIR, "published_ups.json")
MONETIZATION_FILE = os.path.join(DATA_DIR, "monetization.json")

# Format: (UPS Model / Scenario Name, Rated VA, Rated Watts, Power Factor, Internal Battery Config, Total VAh, Topology)
SEED_UPS = [
    ("CyberPower CP1500PFCLCD PFC Sinewave 1500VA/1000W", 1500, 1000, 0.67, "2x 12V 9Ah (24V Series)", 216, "Line-Interactive Pure Sine"),
    ("APC Back-UPS Pro BX1500M 1500VA/900W Compact Tower", 1500, 900, 0.60, "2x 12V 9Ah (RBC175)", 216, "Line-Interactive Stepped"),
    ("APC Smart-UPS 1500VA SMT1500C / SMT1500RM2U", 1500, 1000, 0.67, "4x 12V 7Ah / 2x 12V 18Ah", 432, "Enterprise Pure Sine"),
    ("CyberPower PR1500LCD / PR1500RT2U Smart App Sinewave", 1500, 1500, 1.00, "4x 12V 9Ah (48V Bus)", 432, "1.0 PF Rack/Tower Pure Sine"),
    ("Eaton 5PX 1500RTN (5PX1500RTN) 1500VA/1350W 2U", 1500, 1350, 0.90, "4x 12V 9Ah ABM Bank", 432, "Enterprise Line-Interactive"),
    ("Eaton 9PX 2000RT (9PX2000RT) Online Double-Conversion", 2000, 1800, 0.90, "4x 12V 9Ah (48V Online)", 432, "Online Double-Conversion"),
    ("APC Smart-UPS 2200VA SMT2200C / SMT2200RM2U", 2200, 1980, 0.90, "8x 12V 5Ah (RBC43/55)", 480, "Enterprise Pure Sine"),
    ("APC Smart-UPS 3000VA SMT3000RM2U (NEMA L5-30P)", 3000, 2700, 0.90, "8x 12V 5.5Ah (RBC43)", 528, "30A Rackmount Pure Sine"),
    ("CyberPower OR1500LCDRM1U 1500VA/900W 1U Rackmount", 1500, 900, 0.60, "4x 6V 9Ah Slim Pack", 216, "1U Short-Depth Rack UPS"),
    ("CyberPower CP1000PFCLCD PFC Sinewave 1000VA/600W", 1000, 600, 0.60, "1x 12V 9Ah / 2x 12V 7Ah", 168, "Line-Interactive Pure Sine"),
    ("CyberPower CP1350PFCLCD PFC Sinewave 1350VA/810W", 1350, 810, 0.60, "2x 12V 7Ah (24V Series)", 168, "Line-Interactive Pure Sine"),
    ("APC Back-UPS Pro BR1500MS2 Pure Sine Wave 1500VA/900W", 1500, 900, 0.60, "2x 12V 9Ah (APCRBC163)", 216, "Line-Interactive Pure Sine"),
    ("APC Smart-UPS 1000VA SMT1000C / SMT1000RM2U", 1000, 700, 0.70, "2x 12V 12Ah (RBC6)", 288, "Enterprise Pure Sine"),
    ("APC Smart-UPS Ultra 3000VA SRTL3KRM1UWNC Lithium-Ion", 3000, 3000, 1.00, "48V LiFePO4 / Li-Ion Pack", 600, "1U Lithium Double-Conversion"),
    ("Tripp Lite SMART1500LCDXL 1500VA/900W Rack/Tower", 1500, 900, 0.60, "2x 12V 9Ah + EBM Port", 216, "Line-Interactive Extended"),
    ("Tripp Lite SMART2200RM2U 2200VA/1920W 2U Rack UPS", 2200, 1920, 0.87, "4x 12V 9Ah (RBC94-2U)", 432, "Enterprise Rack Pure Sine"),
    ("Vertiv Liebert PSI5-1500RT120 1500VA/1350W 2U", 1500, 1350, 0.90, "4x 12V 9Ah Hot-Swap", 432, "Pure Sine Line-Interactive"),
    ("Vertiv Liebert GXT5-2000LVRT2UXL 2000VA/1800W Online", 2000, 1800, 0.90, "4x 12V 9Ah Online Bus", 432, "Online Double-Conversion"),
    ("GoldenMate 1000VA/800W LiFePO4 Lithium UPS Backup", 1000, 800, 0.80, "25.6V 9Ah LiFePO4 Pack", 230, "10-Year LiFePO4 UPS"),
    ("Ecoflow River 3 Plus / Delta 3 <10ms UPS Workstation", 1800, 1800, 1.00, "1024Wh LFP Battery Bank", 1024, "LFP Portable Power Station UPS"),
    ("850W RTX 4080/4090 Gaming PC + Dual 4K Monitor UPS", 1500, 1000, 0.67, "2x 12V 9Ah (216 VAh)", 216, "Active PFC Pure Sine Required"),
    ("1000W RTX 5090 Workstation + OLED Monitor UPS Sizing", 2200, 1980, 0.90, "4x 12V 9Ah (432 VAh)", 432, "Active PFC Pure Sine Required"),
    ("Synology DiskStation 4-Bay/8-Bay NAS + UniFi Rack UPS", 1000, 600, 0.60, "2x 12V 9Ah (216 VAh)", 216, "USB HID Auto-Shutdown UPS"),
    ("Proxmox / Unraid 12-Bay HomeLab Server Rack UPS", 1500, 1350, 0.90, "4x 12V 9Ah (432 VAh)", 432, "2U Rackmount Pure Sine"),
    ("Starlink Gen 3 Dish + Wi-Fi 7 Router 8-Hour Outage UPS", 1500, 900, 0.60, "4x 12V 9Ah (432 VAh)", 432, "Extended Low-Draw Runtime"),
    ("CPAP / BiPAP Heated Humidifier Overnight Battery UPS", 1000, 600, 0.60, "2x 12V 12Ah (288 VAh)", 288, "Zero-Noise Pure Sine"),
    ("Ubiquiti UniFi Dream Machine Pro + 24-Port PoE Switch UPS", 1500, 1000, 0.67, "4x 12V 9Ah (432 VAh)", 432, "2U Rackmount Pure Sine"),
    ("3D Printer Farm (Bambu Lab X1C / Prusa) Print-Save UPS", 1500, 1000, 0.67, "4x 12V 9Ah (432 VAh)", 432, "Pure Sine Bed-Heater Buffer"),
    ("Reef Aquarium Return Pump, Heater & Wavemaker UPS", 1500, 1000, 0.67, "4x 12V 9Ah (432 VAh)", 432, "Pure Sine Motor-Safe"),
    ("NEMA 5-15P (15A) vs NEMA 5-20P (20A) UPS Circuit Sizing", 2200, 1920, 0.87, "4x 12V 9Ah (432 VAh)", 432, "NEC 80% Branch Circuit Rule")
]


def load_json(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not parse {filepath}: {e}")
    return default


def save_json(filepath, data):
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def slugify(text):
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    return re.sub(r"[\s-]+", "-", text).strip("-")


def safe_float(val, default=1500.0):
    try:
        cleaned = re.sub(r"[^0-9.]", "", str(val))
        return float(cleaned) if cleaned else float(default)
    except Exception:
        return float(default)


def build_amazon_url(search_keywords, mon_cfg):
    domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")
    encoded_q = urllib.parse.quote_plus(search_keywords)
    return f"https://{domain}/s?k={encoded_q}&tag={tag}"


def discover_google_ups_queries():
    discovered = []
    seeds = [
        "what size ups for ",
        "cyberpower ups ",
        "apc smart ups ",
        "ups runtime calculator for "
    ]
    for seed in seeds:
        try:
            url = f"http://suggestqueries.google.com/complete/search?client=firefox&hl=en&gl=us&q={urllib.parse.quote(seed)}"
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                for suggestion in data[1]:
                    cleaned = suggestion.lower()
                    for pref in seeds:
                        if "what size" in pref or "calculator" in pref:
                            cleaned = cleaned.replace(pref, "")
                    cleaned = re.sub(
                        r"\b(calculator|size|sizing|runtime|chart|manual|review|reddit|for)\b",
                        "",
                        cleaned
                    ).strip()
                    if 5 <= len(cleaned) <= 42:
                        va_m = re.search(r"(\d{4})\s*va", cleaned)
                        va_v = int(va_m.group(1)) if va_m else 1500
                        w_v = int(round(va_v * 0.67, -1))
                        vah_v = 216 if va_v <= 1500 else 432
                        discovered.append((cleaned.title(), va_v, w_v, 0.67, "2x 12V 9Ah SLA/LiFePO4", vah_v, "Line-Interactive Pure Sine"))
        except Exception as e:
            print(f"[WARN] Google Suggest notice: {e}")
    return discovered


def build_deterministic_ups_data(ups_tuple):
    """Mesin Fisika Daya Semu (VA/PF) & Kurva Peukert Baterai UPS (100% bebas gagal)."""
    model_name, rated_va, rated_w, pf, batt_cfg, total_vah, topology = ups_tuple

    # Safe 80% Continuous Load Ceiling (agar inverter UPS tidak overload saat komponen PC/Server spike)
    safe_80pct_w = int(round(rated_w * 0.80, -1))
    half_load_w = int(round(rated_w * 0.50, -1))
    quarter_load_w = int(round(rated_w * 0.25, -1))

    # Rumus Runtime UPS (Menit) dengan Efisiensi Inverter 86% & Faktor Peukert SLA (0.68 pada beban tinggi, 0.78 pada beban rendah):
    runtime_100pct_min = max(2, int(round(((total_vah * 0.86 * 0.62) / max(50.0, float(rated_w))) * 60.0)))
    runtime_50pct_min = max(5, int(round(((total_vah * 0.86 * 0.72) / max(50.0, float(half_load_w))) * 60.0)))
    runtime_25pct_min = max(12, int(round(((total_vah * 0.86 * 0.82) / max(30.0, float(quarter_load_w))) * 60.0)))

    plug_type = "NEMA 5-15P (15A 120V)" if rated_va <= 1500 else ("NEMA 5-20P (20A 120V)" if rated_va <= 2200 else "NEMA L5-30P (30A Twist-Lock)")

    return {
        "ups_name": model_name,
        "topology": topology,
        "seo_title": f"{model_name} Runtime (Minutes), VA-to-Watts & Battery Calculator (2026)",
        "meta_description": f"Calculate exact backup runtime ({runtime_50pct_min} min @ {half_load_w}W / {runtime_25pct_min} min @ {quarter_load_w}W), {pf:.2f} Power Factor watts ({rated_w}W), and {batt_cfg} replacement battery specs for {model_name}.",
        "specs": {
            "rated_va": rated_va,
            "rated_watts": rated_w,
            "power_factor": pf,
            "safe_80pct_watts": safe_80pct_w,
            "battery_config": batt_cfg,
            "total_battery_vah": total_vah,
            "runtime_100pct_min": runtime_100pct_min,
            "runtime_50pct_min": runtime_50pct_min,
            "runtime_25pct_min": runtime_25pct_min,
            "input_plug_spec": plug_type,
            "topology": topology
        },
        "power_verdict": f"Rated at {rated_va:,} VA and {rated_w:,} True Watts ({pf:.2f} Power Factor, {topology}), the {model_name} houses a {total_vah} VAh internal battery array ({batt_cfg}). Due to Peukert's Law discharge curves on high-rate UPS cells, it provides ~{runtime_100pct_min} minutes at full {rated_w:,}W load, ~{runtime_50pct_min} minutes at 50% load ({half_load_w:,}W), and ~{runtime_25pct_min} minutes at 25% load ({quarter_load_w:,}W). For rock-solid stability without nuisance overload alarms, keep continuous load at or below {safe_80pct_w:,}W (80% ceiling).",
        "hardware_bundle": [
            {
                "badge": f"{rated_va}VA / {rated_w}W UPS",
                "title": f"{model_name} ({topology} Battery Backup)",
                "price_range": "$219 - $1,299",
                "amazon_query": f"{model_name} Pure Sine Wave UPS",
                "ups_note": f"Delivers {rated_w:,}W Active-PFC compatible pure sine wave output with Automatic Voltage Regulation (AVR)."
            },
            {
                "badge": f"{total_vah} VAh RBC Battery Kit",
                "title": f"High-Rate Replacement UPS Battery Cartridge ({batt_cfg} — F2 0.250\" Faston Terminals)",
                "price_range": "$49 - $179",
                "amazon_query": f"12V 9Ah F2 Terminal UPS Replacement Battery Pack RBC {batt_cfg.split()[0]}",
                "ups_note": "Factory VRLA AGM cells degrade after 3–4 years; swapping fresh high-rate F2-terminal batteries restores 100% factory runtime."
            },
            {
                "badge": "1U Rack PDU & Surge",
                "title": f"1U Rackmount Metered Power Distribution Unit (PDU) + Network RJ45/Coax Surge Suppressor",
                "price_range": "$59 - $199",
                "amazon_query": "1U Rackmount Metered PDU Power Strip Surge Protector UPS",
                "ups_note": f"Expands {plug_type} UPS battery-backed outlets across your server rack or workstation desk."
            },
            {
                "badge": "LiFePO4 Drop-In Upgrade",
                "title": "12V 9Ah / 10Ah High-Rate LiFePO4 UPS Replacement Batteries (30A BMS, 3,000+ Cycles)",
                "price_range": "$69 - $189",
                "amazon_query": "12V 9Ah 10Ah LiFePO4 F2 Terminal Battery UPS Replacement",
                "ups_note": "Eliminates Peukert capacity sag—doubling usable runtime at 50%+ loads and lasting 8–10 years vs. 3 years for lead-acid."
            }
        ],
        "it_checklist": [
            f"Always choose a Pure Sine Wave UPS ({topology}) for modern Gaming PCs and Servers equipped with Active PFC (Power Factor Corrected) power supplies; cheap 'Simulated/Stepped Sine Wave' units cause Active PFC PSUs to buzz and abruptly shut off during transfer.",
            f"Size your UPS by True Watts ({rated_w:,}W) as well as VA ({rated_va:,}VA), and keep continuous draw below {safe_80pct_w:,}W (80% of rated capacity) so GPU transient spikes never trigger an overload fault.",
            "Never plug a Laser Printer, Space Heater, or Paper Shredder into the 'Battery + Surge' outlets; a laser printer fuser roller draws 1,200W–1,500W instantaneously and will trip the UPS inverter.",
            "Connect the UPS USB-HID or SNMP management port to your NAS (Synology/Unraid) or PC so the operating system executes a clean, automated disk-cache flush and shutdown when 5 minutes of battery remain."
        ],
        "faqs": [
            {
                "q": f"How long will the {model_name} run my PC, NAS, or network rack?",
                "a": f"With {total_vah} VAh of battery capacity ({batt_cfg}), runtime scales non-linearly by Peukert's Law: ~{runtime_100pct_min} minutes at 100% load ({rated_w}W), ~{runtime_50pct_min} minutes at 50% load ({half_load_w}W), ~{runtime_25pct_min} minutes at 25% load ({quarter_load_w}W), and over {int(round((total_vah * 0.85 * 0.85 / 65.0) * 60))} minutes for a 65W Starlink + Wi-Fi router load."
            },
            {
                "q": f"Why is {rated_va:,} VA only rated for {rated_w:,} Watts on the {model_name}?",
                "a": f"VA (Volt-Amps) measures Apparent Power, while Watts measures Real Power. The ratio between them is the Power Factor ($\text{{PF}} = {rated_w} \\div {rated_va} = {pf:.2f}$). You must never exceed EITHER the {rated_va:,} VA ceiling or the {rated_w:,} Watt ceiling."
            },
            {
                "q": f"What replacement battery does the {model_name} take?",
                "a": f"It uses {batt_cfg} high-rate discharge Sealed Lead-Acid (SLA) batteries with 0.250-inch (F2) quick-disconnect spade terminals (totaling {total_vah} VAh). You can replace them every 3–4 years in under 10 minutes using your existing wiring harness."
            }
        ]
    }


# [PEDOMAN LANGKAH 2] Fungsi pencari model otomatis (versi baru + caching + skoring tier)
_CACHED_MODELS = None

def get_active_gemini_model(api_key):
    """Mendeteksi model Gemini Flash STABIL terbaru secara otomatis & menyimpannya di cache."""
    global _CACHED_MODELS
    if _CACHED_MODELS is not None:
        return _CACHED_MODELS

    list_url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
    try:
        req = urllib.request.Request(list_url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            scored_models = []

            for m in data.get("models", []):
                name = m.get("name", "").replace("models/", "")
                methods = m.get("supportedGenerationMethods", [])

                if "generateContent" not in methods or "flash" not in name.lower():
                    continue

                if any(bad in name.lower() for bad in [
                    "preview", "exp", "thinking", "image", "tts", "audio", "vision", "8b"
                ]):
                    continue

                ver_match = re.search(r"gemini-(\d+(?:\.\d+)?)-flash", name.lower())
                if ver_match:
                    ver_num = float(ver_match.group(1))
                    if name.lower() == f"gemini-{ver_match.group(1)}-flash":
                        tier_score = 2
                    elif name.lower() == f"gemini-{ver_match.group(1)}-flash-lite":
                        tier_score = 1
                    else:
                        tier_score = 0
                    scored_models.append((ver_num, tier_score, name))
                elif name.lower() == "gemini-flash-latest":
                    scored_models.append((0.1, 0, name))

            if scored_models:
                scored_models.sort(key=lambda x: (x[0], x[1]), reverse=True)
                _CACHED_MODELS = [item[2] for item in scored_models[:2]]
                print(f"[GEMINI] Future-proof active models locked: {_CACHED_MODELS}")
                return _CACHED_MODELS
    except Exception as e:
        print(f"[WARN] Dynamic model discovery notice: {e}")

    _CACHED_MODELS = ["gemini-flash-latest"]
    return _CACHED_MODELS


def generate_ups_data(ups_tuple):
    if not GEMINI_API_KEY:
        return build_deterministic_ups_data(ups_tuple)

    model_name, rated_va, rated_w, pf, batt_cfg, total_vah, topology = ups_tuple
    det_fallback = build_deterministic_ups_data(ups_tuple)
    sp = det_fallback["specs"]

    prompt = f"""
You are a Senior Data Center Critical Power Engineer & IT Infrastructure Architect. Create an accurate 2026 UPS VA-to-Watts Power Factor, Peukert battery runtime (minutes), and RBC replacement battery guide for: "{model_name}".
Baseline specs: Rating={rated_va}VA / {rated_w}W ({pf} Power Factor, 80% Safe Ceiling={sp['safe_80pct_watts']}W), Battery={batt_cfg} ({total_vah} VAh), Runtime @ 100%={sp['runtime_100pct_min']} min, Runtime @ 50%={sp['runtime_50pct_min']} min, Runtime @ 25%={sp['runtime_25pct_min']} min, Topology={topology}.
Return ONLY a valid JSON object matching this exact schema:
{{
  "ups_name": "{model_name}",
  "topology": "{topology}",
  "seo_title": "{model_name} Runtime (Minutes), VA-to-Watts & Battery Calculator (2026)",
  "meta_description": "Calculate exact UPS battery backup runtime in minutes, VA-to-Watts Power Factor, and RBC replacement battery specs for {model_name}.",
  "specs": {{
    "rated_va": {rated_va},
    "rated_watts": {rated_w},
    "power_factor": {pf},
    "safe_80pct_watts": {sp['safe_80pct_watts']},
    "battery_config": "{batt_cfg}",
    "total_battery_vah": {total_vah},
    "runtime_100pct_min": {sp['runtime_100pct_min']},
    "runtime_50pct_min": {sp['runtime_50pct_min']},
    "runtime_25pct_min": {sp['runtime_25pct_min']},
    "input_plug_spec": "{sp['input_plug_spec']}",
    "topology": "{topology}"
  }},
  "power_verdict": "3-sentence technical summary stating VA, True Watts, Power Factor, internal battery VAh, and exact runtime minutes at 100%, 50%, and 25% loads.",
  "hardware_bundle": [
    {{
      "badge": "{rated_va}VA / {rated_w}W UPS",
      "title": "{model_name}",
      "price_range": "$219 - $1,299",
      "amazon_query": "{model_name} Pure Sine Wave UPS",
      "ups_note": "1-sentence Active PFC compatibility and AVR note"
    }},
    {{
      "badge": "Replacement RBC Battery",
      "title": "High-Rate UPS Replacement Battery Pack ({batt_cfg} F2 Terminal)",
      "price_range": "$49 - $179",
      "amazon_query": "12V 9Ah F2 UPS Replacement Battery Pack RBC",
      "ups_note": "1-sentence 3-to-4 year SLA refresh note"
    }},
    {{
      "badge": "Rackmount Metered PDU",
      "title": "1U Rackmount Metered PDU Power Strip & Network Surge Suppressor",
      "price_range": "$59 - $199",
      "amazon_query": "1U Rackmount Metered PDU Power Strip UPS",
      "ups_note": "1-sentence outlet distribution and load monitoring note"
    }},
    {{
      "badge": "LiFePO4 UPS Battery Upgrade",
      "title": "12V 9Ah/10Ah High-Rate LiFePO4 UPS Replacement Batteries (F2 Terminal)",
      "price_range": "$69 - $189",
      "amazon_query": "12V 9Ah LiFePO4 F2 Battery UPS Replacement",
      "ups_note": "1-sentence Peukert elimination and 10-year lifespan note"
    }}
  ],
  "it_checklist": [
    "Step 1 regarding Pure Sine Wave requirement for Active PFC power supplies",
    "Step 2 regarding 80% continuous Watt/VA ceiling for GPU transient spikes",
    "Step 3 regarding keeping laser printers and space heaters off battery outlets",
    "Step 4 regarding USB-HID / NUT auto-shutdown configuration for NAS and servers"
  ],
  "faqs": [
    {{"q": "How long will the {model_name} run my gaming PC or NAS?", "a": "Exact runtime minutes at 100%, 50%, 25%, and 65W network loads."}},
    {{"q": "What is the difference between {rated_va} VA and {rated_w} Watts?", "a": "Direct Power Factor explanation and why both limits matter."}},
    {{"q": "What replacement battery cartridge fits the {model_name}?", "a": "Exact 12V Ah configuration, F2 terminal size, and VAh total."}}
  ]
}}
"""

    # [PEDOMAN LANGKAH 3] Blok pemanggilan API baru dengan retry 429 + auto model discovery
    for model_id in get_active_gemini_model(GEMINI_API_KEY):
        for attempt in range(2):
            try:
                endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={GEMINI_API_KEY}"
                payload = {
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {
                        "temperature": 0.2,
                        "responseMimeType": "application/json"
                    }
                }
                req = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=40) as resp:
                    result = json.loads(resp.read().decode("utf-8"))
                    raw_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
                    raw_text = re.sub(r"^```(?:json)?\s*", "", raw_text)
                    raw_text = re.sub(r"\s*```$", "", raw_text)
                    parsed = json.loads(raw_text)
                    if "specs" in parsed and "hardware_bundle" in parsed:
                        time.sleep(6)
                        return parsed
            except urllib.error.HTTPError as he:
                if he.code == 429:
                    print(f"[RATE-LIMIT] HTTP 429 on {model_id} (attempt {attempt + 1}). Cooling down 20s...")
                    time.sleep(20)
                else:
                    print(f"[WARN] HTTP {he.code} on {model_id}: {he}")
                    break
            except Exception as e:
                print(f"[WARN] Gemini ({model_id}) notice: {e}")
                break

    return det_fallback


def build_ups_html_page(data, slug, mon_cfg):
    ups_name = data.get("ups_name", "Pure Sine Wave UPS")
    sp = data.get("specs", {})
    rated_va = int(safe_float(sp.get("rated_va", 1500), 1500))
    rated_w = int(safe_float(sp.get("rated_watts", 1000), 1000))
    pf = round(safe_float(sp.get("power_factor", 0.67), 0.67), 2)
    safe_80_w = int(safe_float(sp.get("safe_80pct_watts", int(rated_w * 0.8)), 800))
    batt_cfg = sp.get("battery_config", "2x 12V 9Ah (24V Series)")
    total_vah = int(safe_float(sp.get("total_battery_vah", 216), 216))
    min_100 = int(safe_float(sp.get("runtime_100pct_min", 7), 7))
    min_50 = int(safe_float(sp.get("runtime_50pct_min", 16), 16))
    min_25 = int(safe_float(sp.get("runtime_25pct_min", 38), 38))
    plug_s = sp.get("input_plug_spec", "NEMA 5-15P (15A 120V)")

    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Pure+Sine+Wave+UPS+Battery+Backup+1500VA"), mon_cfg)

    schema_graph = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "SoftwareApplication",
                "name": f"{ups_name} Runtime & VA-to-Watts Calculator",
                "applicationCategory": "UtilitiesApplication",
                "operatingSystem": "Web Browser",
                "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"}
            },
            {
                "@type": "FAQPage",
                "mainEntity": [
                    {
                        "@type": "Question",
                        "name": f.get("q", ""),
                        "acceptedAnswer": {"@type": "Answer", "text": f.get("a", "")}
                    } for f in data.get("faqs", [])
                ]
            }
        ]
    }

    bundle_html = ""
    for item in data.get("hardware_bundle", []):
        amz_url = build_amazon_url(item.get("amazon_query", item.get("title", "Pure Sine Wave UPS")), mon_cfg)
        bundle_html += f"""
        <div class="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col justify-between hover:border-indigo-500/60 transition">
          <div>
            <div class="flex items-center justify-between gap-2 mb-2">
              <span class="text-xs font-bold uppercase tracking-wider bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 px-2.5 py-0.5 rounded">{item.get('badge', 'Critical Power')}</span>
              <span class="text-sm font-bold text-emerald-400">{item.get('price_range', '$59+')}</span>
            </div>
            <h3 class="text-base font-bold text-white mt-2">{item.get('title', '')}</h3>
            <p class="text-xs text-slate-400 mt-2 leading-relaxed">⚡ {item.get('ups_note', '')}</p>
          </div>
          <a href="{amz_url}" target="_blank" rel="nofollow sponsored" class="mt-5 block text-center bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold py-2.5 px-4 rounded-lg text-sm transition shadow-lg">
            Check Price on Amazon →
          </a>
        </div>"""

    # Build Load Wattage vs Runtime Curve Matrix Table (65W, 180W, 350W, 500W, 750W, 1000W)
    matrix_rows_html = ""
    for load_w, dev_label in [
        (65, "65W (Starlink Dish + Wi-Fi 7 Router)"),
        (160, "160W (4-Bay Synology NAS + PoE Switch)"),
        (320, "320W (HomeLab Server + Firewall + NAS)"),
        (500, "500W (Mid-Range Gaming PC + Monitor)"),
        (750, "750W (RTX 4080/4090 Gaming Rig Full Load)"),
        (950, "950W (Workstation / Dual-Server Rack)")
    ]:
        peukert_eff = 0.84 if load_w <= 200 else (0.74 if load_w <= 550 else 0.64)
        sla_mins = int(round(((total_vah * 0.86 * peukert_eff) / float(load_w)) * 60.0))
        lfp_mins = int(round(((total_vah * 0.90 * 0.92) / float(load_w)) * 60.0))
        status_txt = f"{sla_mins} min SLA / {lfp_mins} min LiFePO4" if load_w <= rated_w else "⚠️ Exceeds UPS Watt Rating"
        matrix_rows_html += f"""
        <tr class="border-b border-slate-800 hover:bg-slate-800/40">
          <td class="py-3 px-4 font-bold text-white">{dev_label}</td>
          <td class="py-3 px-4 text-slate-300">{int(round(load_w / pf))} VA Required</td>
          <td class="py-3 px-4 font-bold text-indigo-400">{sla_mins} Minutes (SLA)</td>
          <td class="py-3 px-4 font-bold text-emerald-400">{status_txt}</td>
        </tr>"""

    checklist_html = ""
    for idx, step_text in enumerate(data.get("it_checklist", []), start=1):
        checklist_html += f"""
        <label class="flex items-start gap-3.5 bg-slate-900 border border-slate-800 rounded-xl p-4 cursor-pointer hover:border-slate-700 transition">
          <input type="checkbox" class="mt-1 w-5 h-5 accent-indigo-500 rounded cursor-pointer ups-check">
          <span class="text-sm text-slate-200 leading-relaxed"><strong>IT Power Step {idx}:</strong> {step_text}</span>
        </label>"""

    faqs_html = "".join([
        f"<div class='bg-slate-900 border border-slate-800 rounded-xl p-5'><h3 class='font-bold text-white text-base mb-2'>{f.get('q', '')}</h3><p class='text-sm text-slate-300 leading-relaxed'>{f.get('a', '')}</p></div>"
        for f in data.get("faqs", [])
    ])

    canonical_url = f"{SITE_BASE_URL}/{slug}.html"
    amz_domain = mon_cfg.get("marketplace_domain", "www.amazon.com")
    amz_tag = mon_cfg.get("amazon_associate_tag", "YOUR_AMAZON_TAG-20")

    html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{data.get('seo_title', ups_name)}</title>
  <meta name="description" content="{data.get('meta_description', '')}">
  <link rel="canonical" href="{canonical_url}">
  <meta property="og:title" content="{data.get('seo_title', ups_name)}">
  <meta property="og:description" content="{data.get('meta_description', '')}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="{canonical_url}">
  <script src="https://cdn.tailwindcss.com"></script>
  <script type="application/ld+json">{json.dumps(schema_graph)}</script>
</head>
<body class="bg-slate-950 text-slate-100 antialiased min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur sticky top-0 z-30">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <a href="index.html" class="text-lg font-black tracking-tight text-white flex items-center gap-2">
        <span class="bg-indigo-500 text-white px-2 py-0.5 rounded font-black">UPS</span>RuntimeIndex
      </a>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Pure Sine Wave UPS Systems →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-10 flex-1 w-full">
    <div class="mb-8">
      <div class="flex flex-wrap items-center gap-2.5 mb-3">
        <span class="text-xs font-extrabold uppercase tracking-widest bg-indigo-500 text-white px-3 py-1 rounded-full">{rated_va:,} VA / {rated_w:,}W ({pf:.2f} PF)</span>
        <span class="text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-3 py-1 rounded-full">Battery: {batt_cfg} ({total_vah} VAh)</span>
        <span class="text-xs font-semibold bg-slate-800 text-slate-300 px-3 py-1 rounded-full">50% Load: ~{min_50} Min | {plug_s}</span>
      </div>
      <h1 class="text-3xl sm:text-4xl font-black text-white leading-tight">{data.get('seo_title', ups_name)}</h1>
      <div class="mt-4 bg-slate-900 border-l-4 border-indigo-500 p-4 rounded-r-xl text-sm text-slate-200 leading-relaxed">
        <strong>Critical Power & Peukert Runtime Verdict:</strong> {data.get('power_verdict', '')}
      </div>
    </div>

    <!-- INTERACTIVE UPS RUNTIME, VA-TO-WATTS & BATTERY CAPACITY CALCULATOR -->
    <section class="bg-slate-900 border border-slate-800 rounded-2xl p-6 sm:p-8 mb-12 shadow-2xl">
      <h2 class="text-xl font-extrabold text-white mb-2">Interactive {ups_name} Runtime & VA Sizing Calculator</h2>
      <p class="text-xs text-slate-400 mb-6">Adjust your active equipment load (Watts), internal battery pack configuration (VAh), and battery chemistry (SLA vs. LiFePO4) to compute exact outage runtime in minutes and required UPS VA rating.</p>

      <div class="grid md:grid-cols-2 gap-8 items-center">
        <div class="space-y-5">
          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="loadSlider" class="text-slate-300">Active Equipment Power Draw (Watts)</label>
              <span class="text-indigo-400 font-bold"><span id="loadVal">{int(round(rated_w * 0.5))}</span> Watts</span>
            </div>
            <input id="loadSlider" type="range" min="40" max="2400" step="20" value="{int(round(rated_w * 0.5))}" class="w-full accent-indigo-500 cursor-pointer">
          </div>

          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="vahSelect" class="block text-xs font-medium text-slate-400 mb-1">Internal Battery Bank (VAh)</label>
              <select id="vahSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500">
                <option value="108" {"selected" if total_vah <= 120 else ""}>1x 12V 9Ah (108 VAh — 850VA)</option>
                <option value="216" {"selected" if 120 < total_vah <= 250 else ""}>2x 12V 9Ah (216 VAh — 1500VA)</option>
                <option value="432" {"selected" if 250 < total_vah <= 460 else ""}>4x 12V 9Ah (432 VAh — 2U/Pro)</option>
                <option value="648" {"selected" if total_vah > 460 else ""}>6x 12V 9Ah (648 VAh — Extended)</option>
              </select>
            </div>
            <div>
              <label for="chemSelect" class="block text-xs font-medium text-slate-400 mb-1">Battery Cell Chemistry</label>
              <select id="chemSelect" class="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-indigo-500">
                <option value="sla" selected>Standard Lead-Acid (VRLA AGM)</option>
                <option value="lfp">Drop-In LiFePO4 Upgrade (+35% Run)</option>
              </select>
            </div>
          </div>

          <div>
            <div class="flex justify-between text-sm font-medium mb-1.5">
              <label for="pfSlider" class="text-slate-300">Target UPS Power Factor (Standard = 0.67, Enterprise = 0.90)</label>
              <span class="text-indigo-400 font-bold"><span id="pfVal">{pf:.2f}</span> PF</span>
            </div>
            <input id="pfSlider" type="range" min="0.60" max="1.00" step="0.05" value="{pf}" class="w-full accent-indigo-500 cursor-pointer">
          </div>
        </div>

        <div class="grid grid-cols-2 gap-4">
          <div class="bg-slate-950 border border-indigo-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-indigo-400 font-bold">Estimated Backup Time</span>
            <div class="text-2xl sm:text-3xl font-black text-white mt-1"><span id="minOut">{min_50}</span> <span class="text-sm font-normal text-slate-400">min</span></div>
            <p id="peukertNoteOut" class="text-xs text-indigo-400 font-semibold mt-1">Includes Peukert Discharge Curve</p>
          </div>

          <div class="bg-slate-950 border border-emerald-500/30 rounded-xl p-4">
            <span class="text-xs uppercase text-emerald-400 font-bold">Min UPS Rating (w/ 25% Buffer)</span>
            <div id="vaReqOut" class="text-xl sm:text-2xl font-black text-emerald-400 mt-1">1,500 VA</div>
            <p id="wattCeilOut" class="text-xs text-slate-300 font-semibold mt-1">Min True Watts: 625W+</p>
          </div>
        </div>
      </div>

      <div class="mt-6 bg-indigo-950/40 border border-indigo-500/30 rounded-xl p-4 flex flex-col sm:flex-row items-center justify-between gap-4">
        <div id="upsAdviceBanner" class="text-sm text-indigo-100 font-medium"></div>
        <a id="dynamicUpsBtn" href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="shrink-0 bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold px-4 py-2.5 rounded-lg text-xs uppercase tracking-wider transition">
          Shop Matched Pure Sine UPS on Amazon →
        </a>
      </div>
    </section>

    <!-- 4-CARD HARDWARE BUNDLE -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Complete {ups_name} Battery, PDU & LiFePO4 Upgrade Kit</h2>
        <span class="text-xs text-slate-400">UL-1778 & Active-PFC Pure Sine Rated</span>
      </div>
      <div class="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">{bundle_html}</div>
    </section>

    <!-- LOAD WATTAGE & RUNTIME MATRIX TABLE -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-4">{ups_name} Runtime Chart by Equipment Wattage ({total_vah} VAh Bank)</h2>
      <div class="overflow-x-auto bg-slate-900 border border-slate-800 rounded-xl">
        <table class="w-full text-left border-collapse text-sm">
          <thead>
            <tr class="border-b border-slate-800 bg-slate-950/60 text-slate-400 uppercase text-xs">
              <th class="py-3.5 px-4">Connected IT / Gaming Load</th>
              <th class="py-3.5 px-4">Apparent Power (VA)</th>
              <th class="py-3.5 px-4 text-indigo-400">Standard SLA Runtime</th>
              <th class="py-3.5 px-4 text-emerald-400">SLA vs. LiFePO4 Comparison</th>
            </tr>
          </thead>
          <tbody>{matrix_rows_html}</tbody>
        </table>
      </div>
    </section>

    <!-- IT CHECKLIST -->
    <section class="mb-12">
      <div class="flex items-center justify-between mb-4">
        <h2 class="text-2xl font-extrabold text-white">Data Center & HomeLab Active-PFC & Auto-Shutdown Checklist</h2>
        <span id="upsBadge" class="text-xs font-bold bg-slate-800 text-indigo-400 px-3 py-1 rounded-full">0 / 4 Completed</span>
      </div>
      <div class="space-y-3">{checklist_html}</div>
    </section>

    <!-- FAQ -->
    <section class="mb-12">
      <h2 class="text-2xl font-extrabold text-white mb-5">Frequently Asked Questions ({ups_name})</h2>
      <div class="space-y-4">{faqs_html}</div>
    </section>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500 px-4">
    <p>© {datetime.now(timezone.utc).year} UPSRuntimeIndex. Independent Critical Power & Peukert Battery Engineering Database. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const amzDomain = "{amz_domain}";
    const amzTag = "{amz_tag}";

    const loadSlider = document.getElementById('loadSlider');
    const vahSelect = document.getElementById('vahSelect');
    const chemSelect = document.getElementById('chemSelect');
    const pfSlider = document.getElementById('pfSlider');
    const loadVal = document.getElementById('loadVal');
    const pfVal = document.getElementById('pfVal');
    const minOut = document.getElementById('minOut');
    const peukertNoteOut = document.getElementById('peukertNoteOut');
    const vaReqOut = document.getElementById('vaReqOut');
    const wattCeilOut = document.getElementById('wattCeilOut');
    const upsAdviceBanner = document.getElementById('upsAdviceBanner');
    const dynamicUpsBtn = document.getElementById('dynamicUpsBtn');

    function recalculateUps() {{
      const watts = parseInt(loadSlider.value, 10);
      const vah = parseInt(vahSelect.value, 10);
      const chem = chemSelect.value;
      const pf = parseFloat(pfSlider.value);

      loadVal.textContent = watts.toLocaleString();
      pfVal.textContent = pf.toFixed(2);

      let peukertFactor = 0.72;
      if (chem === 'lfp') {{
        peukertFactor = 0.92;
      }} else {{
        const cRate = watts / vah;
        if (cRate <= 1.0) peukertFactor = 0.84;
        else if (cRate <= 2.5) peukertFactor = 0.72;
        else peukertFactor = 0.60;
      }}

      const invEff = 0.86;
      const runtimeMins = Math.max(2, Math.round(((vah * invEff * peukertFactor) / watts) * 60.0));

      const minSafeWatts = Math.round(watts * 1.25);
      const rawVaNeeded = minSafeWatts / pf;
      let stdVaTier = 1000;
      if (rawVaNeeded <= 1000) stdVaTier = 1000;
      else if (rawVaNeeded <= 1350) stdVaTier = 1350;
      else if (rawVaNeeded <= 1500) stdVaTier = 1500;
      else if (rawVaNeeded <= 2200) stdVaTier = 2200;
      else stdVaTier = 3000;

      minOut.textContent = runtimeMins;
      peukertNoteOut.textContent = chem === 'lfp' ? "LiFePO4 Flat Discharge Curve" : `SLA Peukert Efficiency: ${{Math.round(peukertFactor * 100)}}%`;
      vaReqOut.textContent = `${{stdVaTier.toLocaleString()}} VA`;
      wattCeilOut.textContent = `Min True Watts: ${{minSafeWatts.toLocaleString()}}W+`;

      upsAdviceBanner.innerHTML = `⚡ <strong>Active-PFC Sizing Spec:</strong> A <strong>${{watts.toLocaleString()}}W load</strong> requires at least a <strong>${{stdVaTier.toLocaleString()}} VA / ${{minSafeWatts.toLocaleString()}}W Pure Sine Wave UPS</strong> (providing <strong>~${{runtimeMins}} minutes</strong> of backup runtime on a ${{vah}} VAh battery bank).`;
      dynamicUpsBtn.href = `https://${{amzDomain}}/s?k=${{stdVaTier}}VA+Pure+Sine+Wave+UPS+Battery+Backup+APC+CyberPower&tag=${{amzTag}}`;
    }}

    loadSlider.addEventListener('input', recalculateUps);
    vahSelect.addEventListener('change', recalculateUps);
    chemSelect.addEventListener('change', recalculateUps);
    pfSlider.addEventListener('input', recalculateUps);
    recalculateUps();

    const checks = document.querySelectorAll('.ups-check');
    const badge = document.getElementById('upsBadge');
    checks.forEach(ch => {{
      ch.addEventListener('change', () => {{
        const done = Array.from(checks).filter(c => c.checked).length;
        badge.textContent = `${{done}} / ${{checks.length}} Completed`;
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, f"{slug}.html"), "w", encoding="utf-8") as f:
        f.write(html)


def rebuild_portal_sitemap_and_rss(published, mon_cfg):
    header_cta = mon_cfg.get("header_cta", {})
    header_cta_url = build_amazon_url(header_cta.get("search_query", "Pure+Sine+Wave+UPS+Battery+Backup+1500VA"), mon_cfg)

    cards_html = ""
    for item in reversed(published):
        cards_html += f"""
        <a href="{item['slug']}.html" class="block bg-slate-900 border border-slate-800 hover:border-indigo-500/60 rounded-xl p-5 transition group">
          <div class="flex items-center justify-between mb-2">
            <span class="text-xs font-black uppercase bg-indigo-500 text-white px-2.5 py-0.5 rounded">{item.get('va', 1500):,} VA / {item.get('watts', 1000):,}W</span>
            <span class="text-xs text-slate-400">50% Load: ~{item.get('min_50', 16)} Min</span>
          </div>
          <h2 class="text-base font-bold text-white group-hover:text-indigo-400 transition">{item['ups_name']}</h2>
          <p class="text-xs text-slate-400 mt-2 line-clamp-2">{item['description']}</p>
          <span class="inline-block mt-4 text-xs font-extrabold text-indigo-400">Calculate Runtime & Replacement Battery →</span>
        </a>"""

    index_html = f"""<!DOCTYPE html>
<html lang="en" class="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>UPSRuntimeIndex — UPS Battery Backup Runtime, VA-to-Watts & RBC Sizing Calculator (2026)</title>
  <meta name="description" content="Calculate exact UPS battery backup runtime in minutes, VA-to-Watts Power Factor conversion, and 12V 9Ah RBC replacement battery sizing for APC Smart-UPS, CyberPower PFC Sinewave, Eaton, and Tripp Lite systems.">
  <link rel="canonical" href="{SITE_BASE_URL}/">
  <link rel="alternate" type="application/rss+xml" title="UPSRuntimeIndex RSS Feed" href="{SITE_BASE_URL}/rss.xml">
  <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col">
  <header class="border-b border-slate-800 bg-slate-900/80 sticky top-0 z-30 backdrop-blur">
    <div class="max-w-5xl mx-auto px-4 py-3.5 flex items-center justify-between">
      <div class="text-lg font-black text-white flex items-center gap-2">
        <span class="bg-indigo-500 text-white px-2 py-0.5 rounded font-black">UPS</span>RuntimeIndex
      </div>
      <a href="{header_cta_url}" target="_blank" rel="nofollow sponsored" class="text-xs sm:text-sm bg-indigo-500 hover:bg-indigo-400 text-white font-extrabold px-3.5 py-2 rounded-lg transition">
        {header_cta.get('cta_text', 'Shop Pure Sine Wave UPS Systems →')}
      </a>
    </div>
  </header>

  <main class="max-w-5xl mx-auto px-4 py-12 flex-1 w-full">
    <div class="text-center max-w-2xl mx-auto mb-10">
      <h1 class="text-3xl sm:text-5xl font-black text-white tracking-tight">UPS Battery Backup Runtime, VA-to-Watts & RBC Sizing Database</h1>
      <p class="text-slate-400 mt-3 text-base sm:text-lg">Select your UPS model or PC/Server wattage below to calculate Peukert battery runtime in minutes, Active-PFC watt ceilings, and replacement 12V 9Ah F2 battery cartridges.</p>
      <div class="mt-6">
        <input id="filterInput" type="text" placeholder="Search UPS model or load (e.g. CyberPower CP1500PFCLCD, APC Smart-UPS 1500, Eaton 5PX, 850W Gaming PC, Synology NAS...)" class="w-full bg-slate-900 border border-slate-700 rounded-xl px-4 py-3.5 text-sm text-white focus:outline-none focus:border-indigo-500">
      </div>
    </div>

    <div id="upsGrid" class="grid sm:grid-cols-2 lg:grid-cols-3 gap-5">{cards_html}</div>
  </main>

  <footer class="border-t border-slate-800 py-8 text-center text-xs text-slate-500">
    <p>© {datetime.now(timezone.utc).year} UPSRuntimeIndex. As an Amazon Associate, we earn from qualifying purchases.</p>
  </footer>

  <script>
    const filterInput = document.getElementById('filterInput');
    const cards = Array.from(document.getElementById('upsGrid').children);
    filterInput.addEventListener('input', (e) => {{
      const q = e.target.value.toLowerCase();
      cards.forEach(c => {{
        c.style.display = c.textContent.toLowerCase().includes(q) ? 'block' : 'none';
      }});
    }});
  </script>
</body>
</html>"""

    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DOCS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(index_html)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    urls_xml = f"""  <url>
    <loc>{SITE_BASE_URL}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>\n"""

    for item in published:
        urls_xml += f"""  <url>
    <loc>{SITE_BASE_URL}/{item['slug']}.html</loc>
    <lastmod>{item.get('date', today)}</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.9</priority>
  </url>\n"""

    with open(os.path.join(DOCS_DIR, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(f"""<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n{urls_xml}</urlset>""")

    rss_items = ""
    for item in list(reversed(published))[:30]:
        rss_items += f"""    <item>
      <title>{item['title']}</title>
      <link>{SITE_BASE_URL}/{item['slug']}.html</link>
      <guid>{SITE_BASE_URL}/{item['slug']}.html</guid>
      <description>{item['description']}</description>
    </item>\n"""

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">
  <channel>
    <title>UPSRuntimeIndex UPS Battery Backup & VA Sizing Database</title>
    <link>{SITE_BASE_URL}/</link>
    <description>Interactive UPS Battery Backup Runtime, VA-to-Watts & RBC Replacement Battery Calculators</description>
    <atom:link href="{SITE_BASE_URL}/rss.xml" rel="self" type="application/rss+xml" />
    <atom:link href="https://pubsubhubbub.appspot.com/" rel="hub" />
{rss_items}  </channel>
</rss>"""

    with open(os.path.join(DOCS_DIR, "rss.xml"), "w", encoding="utf-8") as f:
        f.write(rss_xml)

    with open(os.path.join(DOCS_DIR, "robots.txt"), "w", encoding="utf-8") as f:
        f.write(f"User-agent: *\nAllow: /\nSitemap: {SITE_BASE_URL}/sitemap.xml\n")

    with open(os.path.join(DOCS_DIR, f"{INDEXNOW_KEY}.txt"), "w", encoding="utf-8") as f:
        f.write(INDEXNOW_KEY)


def notify_search_engines(new_urls):
    if not SITE_BASE_URL or not new_urls:
        return
    parsed_host = urllib.parse.urlparse(SITE_BASE_URL).netloc
    payload = {
        "host": parsed_host,
        "key": INDEXNOW_KEY,
        "keyLocation": f"{SITE_BASE_URL}/{INDEXNOW_KEY}.txt",
        "urlList": new_urls
    }
    try:
        req = urllib.request.Request(
            "https://api.indexnow.org/indexnow",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json; charset=utf-8"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"[INDEXNOW] Pushed {len(new_urls)} URLs (HTTP {resp.status})")
    except Exception as e:
        print(f"[WARN] IndexNow ping notice: {e}")

    try:
        hub_data = urllib.parse.urlencode({
            "hub.mode": "publish",
            "hub.url": f"{SITE_BASE_URL}/rss.xml"
        }).encode("utf-8")
        req_hub = urllib.request.Request(
            "https://pubsubhubbub.appspot.com/",
            data=hub_data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST"
        )
        with urllib.request.urlopen(req_hub, timeout=15) as resp_hub:
            print(f"[WEBSUB] Google PubSubHubbub ping status: {resp_hub.status}")
    except Exception as e:
        print(f"[WARN] WebSub ping notice: {e}")


def main():
    published = load_json(PUBLISHED_FILE, [])
    mon_cfg = load_json(MONETIZATION_FILE, {})
    published_slugs = {item["slug"] for item in published}

    candidates = []
    if CUSTOM_UPS:
        candidates.append((CUSTOM_UPS.strip(), 1500, 1000, 0.67, "2x 12V 9Ah (24V Series)", 216, "Line-Interactive Pure Sine"))
    candidates.extend(SEED_UPS)
    candidates.extend(discover_google_ups_queries())

    new_urls = []
    count = 0

    for ups_tuple in candidates:
        if count >= PAGES_PER_RUN:
            break
        u_name = ups_tuple[0]
        slug = slugify(f"{u_name}-runtime-watt-calculator")
        if slug in published_slugs:
            continue

        print(f"[ENGINE] Generating UPS runtime & VA-to-Watts calculator for: {u_name}...")
        try:
            data = generate_ups_data(ups_tuple)
            build_ups_html_page(data, slug, mon_cfg)
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            sp = data.get("specs", {})

            published.append({
                "ups_name": data.get("ups_name", u_name),
                "slug": slug,
                "title": data.get("seo_title", f"{u_name} Runtime Calculator"),
                "description": data.get("meta_description", ""),
                "va": int(safe_float(sp.get("rated_va", ups_tuple[1]), ups_tuple[1])),
                "watts": int(safe_float(sp.get("rated_watts", ups_tuple[2]), ups_tuple[2])),
                "min_50": int(safe_float(sp.get("runtime_50pct_min", 16), 16)),
                "date": today
            })
            published_slugs.add(slug)
            if SITE_BASE_URL:
                new_urls.append(f"{SITE_BASE_URL}/{slug}.html")
            count += 1
            # [PEDOMAN LANGKAH 4] Sleep 15 detik untuk menghindari 429 rate-limit di free tier
            time.sleep(15)
        except Exception as e:
            print(f"[ERROR] Failed building {u_name}: {e}")

    save_json(PUBLISHED_FILE, published)
    rebuild_portal_sitemap_and_rss(published, mon_cfg)
    if new_urls and SITE_BASE_URL:
        new_urls.append(f"{SITE_BASE_URL}/")
        notify_search_engines(new_urls)
    print(f"[DONE] Published {count} new UPS battery runtime calculator pages.")


if __name__ == "__main__":
    main()
