# Perception Tools — Real API Setup

**Policy:** Only **free** APIs are integrated. For any **non-free** option (including subscription or limited free-tier APIs), the project uses **mock data only** — no integration with project44, MarineTraffic, D&B, Sayari, etc.

Use environment variables for API keys (e.g. `.env` with `python-dotenv` or your deployment secrets).

---

## 1. `search_disruption_news(query)` — News / search

**Purpose:** Search for supply chain and disruption news; return articles with summaries and metadata.


| API                             | What you get                                  | Auth                                     | Notes                                                                            |
| ------------------------------- | --------------------------------------------- | ---------------------------------------- | -------------------------------------------------------------------------------- |
| **Google Custom Search / News** | Web + news results, snippets                  | API key + Search Engine ID               | [Programmable Search](https://programmablesearchengine.google.com/); news index. |
| **NewsAPI.org**                 | News articles by keyword, source, date        | API key (free tier)                      | [NewsAPI](https://newsapi.org/). Good for “disruption” / “supply chain” queries. |
| **Google Gemini (generative)**  | Summarize + classify from URLs or pasted text | Vertex AI / Gemini API (you already use) | Call Gemini to summarize/classify results from any news source.                  |


**Recommendation:** NewsAPI for quick setup (free tier). For production, Google Custom Search + Gemini to classify severity/type from snippets.

**Env vars:** `NEWSAPI_KEY` or `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID`

**Pipeline:** The Google Custom Search pipeline is in `tools/perception_tools.py` in `search_disruption_news()`. It requires `GOOGLE_SEARCH_API_KEY` and `GOOGLE_SEARCH_ENGINE_ID` in the environment; if either is missing, the tool returns an error (no mock fallback). Load these from project root `.env` or `perception_agent/.env` (both are loaded automatically).

### Reliable sources for Google Custom Search (sites to add)

When you configure your Programmable Search Engine, add **only** these domains for high-reliability supply chain / disruption news:

**Wire services & major news**

- `reuters.com`
- `apnews.com`
- `bloomberg.com`
- `bbc.com`
- `ft.com` (Financial Times)
- `wsj.com` (Wall Street Journal)
- `economist.com`

**Established trade / logistics (editorial, cited in industry)**

- `freightwaves.com`
- `joc.com` (Journal of Commerce)
- `theloadstar.com`
- `supplychaindive.com`

**Regional (for Taiwan / Asia exposure)**

- `scmp.com` (South China Morning Post)

Add these domains one per line under **Sites to search**. Avoid tabloids, partisan outlets, and unvetted blogs.

---

## 2. `get_shipping_lane_status(lane)` — Shipping / logistics

**Purpose:** Operational status of lanes (delays, reroutes, surcharges).

**In this project:** **Mock only.** All options below are paid (or subscription/limited); we do not integrate them.

| API                         | What you get                                                  | Auth                 | Notes                                                                                                             |
| --------------------------- | ------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------------------------------------------- |
| **project44**               | Real-time visibility, delays, ETA, disruptions by lane/region | API key (enterprise) | [project44](https://www.project44.com/) — industry standard for ocean/road/rail.                                  |
| **Flexport / Flexport API** | Shipment tracking, lane-level data (if you use Flexport)      | OAuth / API key      | For existing Flexport customers.                                                                                  |
| **MarineTraffic**           | Vessel positions, port calls, AIS                             | API key              | [MarineTraffic API](https://www.marinetraffic.com/en/ais-api-services) — more raw data; you derive “lane status”. |
| **Windward**                | Maritime risk, delays, port congestion                        | API key (enterprise) | Good for risk and disruption signals.                                                                             |

**None of the above are free for API use** — all require a paid or enterprise plan (MarineTraffic has a limited free trial). Free alternatives (JSONCargo, Data Docked) could be integrated later if desired; for now **mock is used**.

**Free or low-cost alternatives:**

| API | What you get | Auth | Notes |
|-----|----------------|------|--------|
| **JSONCargo** | Container tracking, ETAs, port/vessel info | Free API key | [JSONCargo](https://jsoncargo.com/ocean-freight-track-trace-api/) — free tier for ocean freight tracking. |
| **Data Docked** | Vessel positions, port activity | Free API (no credit card) | Real-time data for 800k+ vessels; you derive lane/route status. |
| **Portcast** | Port congestion (berth counts, waiting times) | API key (check for trial) | Lane-level disruption signals via congestion by port. |

For a free path: use **JSONCargo** or **Data Docked** with your own mapping from ports/routes to lane names (e.g. “Asia-Europe (Suez)”). Not integrated in this project; **mock is used**.

**Env vars:** None (mock only).

---

## 3. `get_climate_alerts(regions)` — Climate / disasters

**Purpose:** Active alerts (storms, floods, earthquakes) by region.

**In this project:** **NASA EONET** is integrated. Uses [EONET API v3](https://eonet.gsfc.nasa.gov/docs/v3) (open natural events). Set **NASA_API_KEY** in the environment (optional; may improve rate limits). Regions are mapped to bounding boxes; only events whose geometry falls inside a requested region are returned.

| API            | What you get                                                                    | Auth          | Notes                                                                              |
| -------------- | ------------------------------------------------------------------------------- | ------------- | ---------------------------------------------------------------------------------- |
| **NASA EONET** | Natural events (wildfires, severe storms, cyclones, etc.) by geometry/bbox      | Optional key  | [EONET v3](https://eonet.gsfc.nasa.gov/api/v3/events) — used in this project.      |
| **GDACS**      | Global disaster alerts (cyclones, earthquakes, floods, droughts) by region/bbox | None (public) | [GDACS API](https://www.gdacs.org/gdacsapi/api/) — JSON feed; free, no key.        |
| **NOAA / NWS** | US-focused severe weather                                                       | None (public) | For US regions.                                                                    |

**Env vars:** `NASA_API_KEY` (optional; set in `.env` or `perception_agent/.env`).

---

## 4. `score_supplier_health(supplier_id)` — Supplier risk / health

**Purpose:** Financial and operational health, risk flags, recommendations.

**In this project:** **Gemini API** is used. The tool loads supplier context from `mock_profile.json` (or `config/manufacturer_profile.json`), sends it to Gemini with a structured prompt, and parses the model output into the same health_data shape (overall_health_score, financial_stability, recommendation, etc.). Set **GEMINI_API_KEY** or **GOOGLE_API_KEY** in the environment.

| API                        | What you get                                            | Auth                 | Notes                                                                         |
| -------------------------- | ------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------------- |
| **Gemini (this project)**  | LLM-generated health score and recommendation from context | API key              | Uses supplier profile + prompt; no D&B/Sayari.                                |
| **Dun & Bradstreet (D&B)** | Company financials, risk scores, firmographics          | API key (enterprise) | [D&B API](https://developer.dnb.com/) — map your `SUP-001` to D‑U‑N‑S number. |
| **Sayari**                 | Supply chain risk, ownership, sanctions, adverse events | API key              | [Sayari](https://sayari.com/) — good for geopolitical and compliance signals. |

**Env vars:** `GEMINI_API_KEY` or `GOOGLE_API_KEY` (required for `score_supplier_health`).

---

## Summary checklist

| Tool                       | In this project        | Env var(s)                                                           |
| -------------------------- | ---------------------- | -------------------------------------------------------------------- |
| `search_disruption_news`   | **Real** (Google CSE)  | `GOOGLE_SEARCH_API_KEY` + `GOOGLE_SEARCH_ENGINE_ID`                  |
| `get_shipping_lane_status` | **Mock** (no paid API) | —                                                                    |
| `get_climate_alerts`       | **Real** (NASA EONET)  | `NASA_API_KEY` (optional)                                            |
| `score_supplier_health`    | **Real** (Gemini)      | `GEMINI_API_KEY` or `GOOGLE_API_KEY`                                |


---

## Implementation order

1. **search_disruption_news** — Google Custom Search is integrated; set env vars to use it.
2. **get_climate_alerts** — NASA EONET is integrated; set `NASA_API_KEY` (optional) in `.env` or `perception_agent/.env`.
3. **score_supplier_health** — Gemini is integrated; set `GEMINI_API_KEY` or `GOOGLE_API_KEY` in `.env` or `perception_agent/.env`.
4. **get_shipping_lane_status** — mock only; no integration with paid APIs.

Store keys in `.env` (and add `.env` to `.gitignore`). Only `GOOGLE_SEARCH_*` are used for perception tools.