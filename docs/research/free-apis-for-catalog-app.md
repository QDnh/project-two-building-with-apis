# Free external APIs for a "search, save, annotate" Django catalog app

Research date: 2026-11-15. Scope: free APIs a server-side Django/DRF app can call to search items, save them locally (enough data to survive the API being down), and attach user notes, ratings or status. The current draft idea is a Book Catalog System (see `project-idea.md`), so books get the most weight.

Method: candidates were found through general search and checked against the provider's own docs, terms or pricing pages. Every claim cites the page it came from. Some official pages blocked automated fetching (IGDB docs, Discogs docs, AniList's new docs site, BGG, Hardcover). For those, the claim comes from search-engine snippets of the official page, is cited to that URL and is marked *(snippet)*. Open those pages yourself before relying on the exact numbers.

---

## 1. Summary and top recommendations

The four requirements that matter most are free cost, a usable search endpoint, terms that allow you to keep saved data locally, and predictable errors (429, 503) that the app can handle cleanly. Measured against those:

| Pick | Provider | Why |
|---|---|---|
| **Best for books (and best overall for this project)** | **Open Library** | No key or account. Has a JSON `search.json` endpoint and a covers CDN. The docs ask clients to "cache responses where possible", and the Internet Archive "does not assert any new copyright" over the data, so storing saved books locally fits. Documented limits are 1 req/s, or 3 req/s if you send a User-Agent with contact info. The developer page was edited in Oct–Nov 2026, so it is actively maintained. |
| **Best no-key option (non-books)** | **TVmaze** (TV shows) | No key. Licensed CC BY-SA, and the data "can freely be used for any purpose" with credit. The limit is at least 20 calls per 10 s per IP. The docs say images may be cached indefinitely. These are the clearest storage terms of any provider checked. |
| **Best keyed option** | **TMDB** (movies + TV) | Free for non-commercial use, with a key from a free account. Data is rich and includes posters. Limit is about 40 req/s. **Caveat:** the terms forbid caching any TMDB information "for longer than 6 months", so saved rows must be refreshed periodically. Attribution and the TMDB logo are required. |
| **Book fallback / second source** | Google Books | Very good search (`intitle:`, `inauthor:`, `isbn:`). However, the Google APIs ToS forbids building databases or permanent copies and keeping cached copies longer than the cache headers allow. That conflicts with the "store enough locally" requirement, so use it only as a secondary source if at all. A key is required, and the default quota is not documented officially. |

**Avoid for this project:**
- **Spotify.** Its terms forbid storing content or building databases of it, and since Feb/Mar 2026 Development Mode requires the developer to have Spotify Premium.
- **Spoonacular.** On the free plan you may cache data for only 1 hour, except recipe id, title and image URL.
- **Edamam.** There is no free plan; the cheapest is $9/mo.
- **Last.fm.** Images are excluded from the license.
- **AniList.** The terms say "using the API as a backup or data storage service is strictly prohibited."

**Books verdict:** Use Open Library as the only external source. On save, store the title, authors, first publish year, the work key (`/works/OL…W`), `cover_i`, ISBNs (ask for them via `fields=`), subjects, and a description if you fetch the work record. That keeps the detail page working when Open Library is down. Store the cover URL (`https://covers.openlibrary.org/b/id/{cover_i}-M.jpg`) and show a placeholder if it fails. Set a `User-Agent: AppName (email)` header. Treat timeouts, 5xx and 429/403 responses as "external API unavailable" messages.

---

## 2. Comparison table

Legend: "Store locally?" means whether the terms allow keeping fetched data in your own database.

| Provider | Category | Key / auth | Free limits | Store locally? | Attribution | Format | Verdict |
|---|---|---|---|---|---|---|---|
| Open Library | Books | None (User-Agent with contact info requested) | 1 req/s default; 3 req/s identified; covers 100 req / 5 min per IP for non-ID lookups | Yes: caching encouraged; bulk scraping discouraged | Courtesy link "appreciated" (covers) | JSON | **Top pick for books** |
| Google Books | Books | API key (or OAuth) | Not documented officially (1,000/day is widely reported but unverified) | **Restricted**: no permanent copies beyond cache headers (Google APIs ToS) | Per API docs; cannot charge users | JSON | Secondary only |
| Gutendex | Books (public-domain Project Gutenberg only) | None | Not documented | Not documented; underlying works are public domain | Not documented | JSON | Niche; site says "run your own server" for long-term use |
| Hardcover | Books | Token (GraphQL); beta | Free: 5,000/day, 60/min, burst 10 *(snippet)* | Not verified | Not verified | GraphQL | Promising but beta; GraphQL adds complexity |
| TMDB | Movies, TV | Free account + key or Bearer token | ~40 req/s | **Max 6 months** cache | Logo + disclaimer required | JSON | Best movie option |
| OMDb | Movies, TV | Key (free tier by email) | 1,000/day | Not documented | Content CC BY-NC 4.0 | JSON/XML | OK, but posters are for patrons only |
| TVmaze | TV | None | ≥20 calls / 10 s per IP | Yes (CC BY-SA; images may be cached indefinitely) | Credit + link back | JSON | **Best no-key option** |
| RAWG | Video games | Key | 20,000 req/month, non-commercial | Not documented; no redistribution | Active link back on every page using data | JSON | Good for games |
| IGDB (Twitch) | Video games | Twitch Client ID + OAuth client-credentials token | 4 req/s, 8 open requests *(snippet)* | Yes: IGDB "prefers" you store and serve data *(snippet)* | Attribution to IGDB.com for commercial partners *(snippet)* | JSON (Apicalypse POST bodies) | Strong but more setup |
| MusicBrainz | Music | None for reads; User-Agent required | 1 req/s per IP | Yes: core data CC0 | None for CC0 core data | XML default, JSON via `fmt=json` | Good no-key music source |
| Cover Art Archive | Music art | None | Docs contradict themselves on limits | Not documented | Not documented | JSON + images | Pairs with MusicBrainz |
| Discogs | Music | Key/secret or token (search needs auth) | 60/min authenticated, 25/min unauthenticated *(snippet)* | **Restricted**: no storing "longer than is necessary"; 6-hour freshness rule *(snippet)* | Not verified | JSON | Not a good fit |
| Last.fm | Music | Key | Not specified ("sets and enforces limits") | Cache per HTTP headers; 100 MB cap | Credit + links required | JSON/XML | Weak: images excluded |
| Spotify | Music | OAuth; dev mode needs Premium (2026) | Search max `limit` cut to 10 | **No**: no databases; only temporary caching | Branding guidelines | JSON | **Avoid** |
| iTunes Search | Music, podcasts, ebooks, movies | None | ~20 calls/min | Large sites should cache; art only on pages that promote the item | Promotional use only; badges | JSON | Terms poorly suited |
| TheMealDB | Recipes | Test key "1" (dev / education) | Free key limited to 100 items for "list all" | Not documented | Not documented | JSON | Easiest recipe option for a class project |
| Spoonacular | Recipes | Key | 50 points/day, 1 req/s | **1 hour** (except id, title, image URL) | Backlink required | JSON | Avoid (storage rule) |
| Edamam | Recipes | Paid key | No free plan ($9/mo minimum) | Paid plans only | Required | JSON | Avoid (cost) |
| Jikan | Anime/manga (unofficial MyAnimeList scraper) | None | 3/s, 60/min *(snippet)* | Not documented; "respect MyAnimeList's ToS" | Not documented | JSON | OK for a demo; unofficial |
| MyAnimeList official API | Anime/manga | Client ID | Not verified | Educational = non-commercial; must delete removed content within 24 h | "authorized by MyAnimeList" allowed | JSON | Possible; more terms to follow |
| AniList | Anime/manga | None for public queries | 90/min (currently degraded to 30/min) | **No** "backup or data storage service"; no hoarding | None stated | GraphQL | Poor fit for local storage |
| BoardGameGeek XML API | Board games | **Registered app + Bearer token (since fall 2025)** | "Still being determined" *(snippet)* | Caching recommended; data may not be modified *(snippet)* | "Powered by BGG" logo + credit *(snippet)* | XML | Usable, but XML plus approval wait |

---

## 3. Per-provider details

### Books

#### Open Library (openlibrary.org), recommended
- **Search:** `GET https://openlibrary.org/search.json` with `q`, plus `title=` / `author=` (shown in the examples), `fields`, `limit`, `page`/`offset`, `sort` (`new`, `old`, `random`, `key`) and `lang`. The response has `num_found`, `start` and `docs[]`. Example doc fields: `key`, `title`, `author_name`, `author_key`, `first_publish_year`, `cover_i`, `edition_count`, `has_fulltext`, `ia`. The docs warn that "The schema is not guaranteed to be stable." ISBNs are not in the documented example, so request them explicitly with `fields=` and verify the result. [search docs](https://openlibrary.org/dev/docs/api/search)
- **Other APIs:** Works, Editions, Authors, Subjects, Covers, Lists, and more. The Legacy JSON API is deprecated. [developers/api](https://openlibrary.org/developers/api)
- **Covers:** `https://covers.openlibrary.org/b/{key}/{value}-{S|M|L}.jpg`, where key is `isbn`, `oclc`, `lccn`, `olid` or `id`. Lookups by keys other than CoverID/OLID are limited to "100 requests/IP … every 5 minutes", and going over returns 403. Public pages should use a `src` pointing to covers.openlibrary.org, a courtesy link back is "appreciated", and the service is "not for bulk download." [covers docs](https://openlibrary.org/dev/docs/api/covers) Tip: store `cover_i` and build the `/b/id/` URL, which avoids the ISBN rate limit.
- **Rate limits / auth:** No key. 1 req/s default, 3 req/s for "identified" requests that send `User-Agent: AppName (contact email)`. The docs ask you to cache responses, avoid bulk downloads through the API (use the monthly dumps instead), not spread requests across IPs, and not use Open Library "as a backend for high-traffic commercial services". There is a use-case registration form. "Violations may result in aggressive rate limiting or blocking." [developers/api](https://openlibrary.org/developers/api)
- **License:** The Internet Archive "does not assert any new copyright or other proprietary rights" over the database, with a warning that some contributions may carry existing rights. No named license such as CC0 is stated. [licensing](https://openlibrary.org/developers/licensing); site ToS: [archive.org/about/terms.php](https://archive.org/about/terms.php)
- **Maintenance:** The developer page's revision history shows edits from 2026-10-03 to 2026-11-08. [developers/api](https://openlibrary.org/developers/api)
- **Python:** Plain REST/JSON with `requests` or `httpx`. Only a header is needed.

#### Google Books API
- **Search:** `GET https://www.googleapis.com/books/v1/volumes?q=…`, with operators `intitle:`, `inauthor:`, `isbn:` and others. `maxResults` defaults to 10 (max 40); `startIndex` pages the results. `volumeInfo` includes title, authors, publisher, publishedDate, description, pageCount, industryIdentifiers (ISBN_10/13), categories, averageRating, imageLinks, language and infoLink. [using](https://developers.google.com/books/docs/v1/using)
- **Auth:** "A request that does not provide an OAuth 2.0 token must send an API key." A key comes from a Google Cloud project. "My Library" bookshelf endpoints need OAuth. [using](https://developers.google.com/books/docs/v1/using)
- **Quota:** No official numeric default was found. The commonly cited 1,000/day comes from forums and third-party pages, and one forum post shows a conflicting figure. Check your project's Quotas tab in the Cloud console. [Google forum](https://discuss.google.dev/t/how-to-apply-for-higher-google-books-api-quota/321977) (non-primary; listed for context only)
- **Terms:** Books API terms (last updated 2012-04-25): "You may not charge users any fee for the use of your application." [books/terms](https://developers.google.com/books/terms) The Google APIs ToS (2021-11-09) §5(e) forbids you to "Scrape, build databases, or otherwise create permanent copies of such content, or keep cached copies longer than permitted by the cache header." §6(b) requires the attributions given in the API docs. [developers.google.com/terms](https://developers.google.com/terms)
- **Fit:** High-quality search, but the storage clause conflicts with saving books locally.

#### Gutendex (Project Gutenberg metadata)
- `GET https://gutendex.com/books?search=…` returns 32 results per page. Fields include `id`, `title`, `authors` (name, birth/death year), `subjects`, `bookshelves`, `languages`, `copyright`, `formats` (MIME type → URL map) and `download_count`. [gutendex.com](https://gutendex.com/)
- Key: not documented. Rate limits: not documented. "For long-term use, please run your own server." [gutendex.com](https://gutendex.com/) The code is MIT-licensed. [GitHub](https://github.com/garethbjohnson/gutendex)
- **Fit:** Covers public-domain ebooks only, so it is too narrow for a general book catalog.

#### Hardcover (hardcover.app)
- GraphQL API, the same one Hardcover's own site and apps use. It is described as "currently in beta". The free plan allows 5,000/day, a burst of 10 and 60/min. Requests over the burst limit return 403. Do not ask users to paste personal access tokens. *(snippet)* [getting-started](https://docs.hardcover.app/api/getting-started/)
- Terms on storage and commercial use: not verified.
- **Fit:** Interesting because it is reading-focused, but beta status plus GraphQL make it riskier than Open Library.

### Movies and TV

#### TMDB (The Movie Database)
- **Key:** Apply from your account settings ("API" link). You must accept the terms. [getting-started](https://developer.themoviedb.org/docs/getting-started), [FAQ](https://developer.themoviedb.org/docs/faq) Auth is a v3 `api_key` query parameter or an API Read Access Token in the `Authorization` header. [auth](https://developer.themoviedb.org/docs/authentication-application)
- **Cost:** "free to use for non-commercial purposes as long as you attribute TMDB." [FAQ](https://developer.themoviedb.org/docs/faq) Whether a credit card is required is not documented (none is mentioned).
- **Rate limit:** About 40 req/s. The old 40-per-10-s limit has been disabled. Respect 429 responses. [rate-limiting](https://developer.themoviedb.org/docs/rate-limiting)
- **Images:** `https://image.tmdb.org/t/p/{size}/{file_path}`, with base URL and sizes from `/configuration`. [image-basics](https://developer.themoviedb.org/docs/image-basics)
- **Terms (updated 2023-10-20):** No commercial use without a separate agreement. You may not "Cache, for longer than 6 months, any information obtained through or from TMDB". You must use the TMDB logo and the not-endorsed disclaimer, and delete all content on termination. [api-terms-of-use](https://www.themoviedb.org/api-terms-of-use)

#### OMDb
- Key by email. Free tier: "FREE! (1,000 daily limit)". The other tier is Patreon. [apikey](https://www.omdbapi.com/apikey.aspx)
- Search with `s=` (pages 1–100); look up with `t=` (title) or `i=` (IMDb ID). JSON by default, XML via `r=xml`. The Poster API is for patrons only. "All content licensed under CC BY-NC 4.0." [omdbapi.com](https://www.omdbapi.com/)
- Caching terms: not documented on the main page.

#### TVmaze
- No key is mentioned for the public API. Search with `/search/shows?q=` and `/singlesearch/shows?q=`. `image` objects have `medium` and `original` URLs. [tvmaze.com/api](https://www.tvmaze.com/api)
- Rate limit: "at least 20 calls every 10 seconds per IP"; 429 on excess. Output is cached for 60 minutes at the load balancer. Images may be cached indefinitely. [tvmaze.com/api](https://www.tvmaze.com/api)
- License: CC BY-SA. The data "can freely be used for any purpose" if TVmaze is credited (for example, with a link back). [tvmaze.com/api](https://www.tvmaze.com/api)

### Video games

#### RAWG
- A key is required on every request. Free tier: non-commercial, 20,000 requests/month, with "Required backlinks to RAWG from pages where the data is used." Paid Business and Enterprise tiers exist. Search with `/api/games?search=` (plus `search_precise`/`search_exact`). No redistribution or reselling of data. Caching rules: not documented. [rawg.io/apidocs](https://rawg.io/apidocs)

#### IGDB (Twitch)
- Needs a Twitch developer app (Client ID + secret) and an OAuth client-credentials token. Queries are POST bodies in the Apicalypse syntax. *(The official docs blocked fetching; details come from search snippets of [api-docs.igdb.com](https://api-docs.igdb.com/) and [igdb.com/api](https://www.igdb.com/api).)*
- 4 req/s and up to 8 open requests; 429 on excess. Free for non-commercial use under the Twitch Developer Service Agreement. The FAQ wording on commercial use conflicts with that. IGDB prefers that you store and serve the data yourself. *(snippet)*
- **Fit:** The storage terms are friendly, but token handling and the query language add work.

### Music

#### MusicBrainz
- Search with `/ws/2/<entity>?query=…&limit=&offset=`. XML is the default; get JSON with `fmt=json` or `Accept: application/json`. Reads need no auth. Digest auth will be removed in August 2027 (it only affects writes). "Non-commercial use of this web service is free." [MusicBrainz_API](https://musicbrainz.org/doc/MusicBrainz_API)
- Rate limit: about 1 req/s per source IP. Going over means 100% of requests are declined with 503, not just the excess. A meaningful User-Agent (`App/version ( contact )`) is required; generic ones such as `Python-urllib` are throttled. [Rate_Limiting](https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting)
- License: core data is CC0; supplementary data is CC BY-NC-SA 3.0. [Data_License](https://musicbrainz.org/doc/About/Data_License)
- Cover art comes from the Cover Art Archive: `coverartarchive.org/release/{mbid}/front[-250|500|1200]`. The docs both say "no rate limiting rules in place" and list 503 for exceeding a limit. [CAA API](https://musicbrainz.org/doc/Cover_Art_Archive/API)

#### Discogs
- `/database/search` requires authentication. The limit is 60/min authenticated and 25/min unauthenticated per IP. *(snippet of [discogs.com/developers](https://www.discogs.com/developers))*
- API Terms: you may not cache or store content "longer than is necessary", or display content more than 6 hours older than the live site. Images are "restricted data". *(snippet of [API Terms of Use](https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use))* This is a poor fit for local saving.

#### Last.fm
- Non-commercial only. Cache "in accordance with the HTTP headers", with a 100 MB "Reasonable Usage Cap". You must credit Last.fm and link to it. "You will not use any audio, audiovisual, images and/or artwork." [api/tos](https://www.last.fm/api/tos)

#### Spotify Web API (changed 2024–2026)
- **2024-11-27:** New apps lost Related Artists, Recommendations, Audio Features/Analysis, featured/category playlists, and preview URLs. [blog](https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api)
- **2026-02-06 announcement:** Development Mode requires a Spotify Premium account, one Dev-Mode Client ID per developer, and at most 5 authorized users. This applies to new Client IDs from 2026-02-11 and to existing ones from 2026-03-09. [blog](https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security)
- Search still exists, but `limit` max drops 50 → 10 and the default 20 → 5. Batch GETs (`/tracks`, `/albums`, …) are removed. [migration guide](https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide)
- Terms (v10, effective 2025-05-15): "you may not store, aggregate or create compilations or databases of Spotify Content". Local caching is allowed only "as strictly necessary" for temporary caching of metadata and cover art. [developer terms](https://developer.spotify.com/terms)
- **Verdict:** Incompatible with the local-save requirement, and it costs money (Premium).

#### iTunes Search API (Apple)
- `https://itunes.apple.com/search?term=…&country=…&media=…`. Media types include music, podcast, movie, ebook and others. About 20 calls/min; no key. Content may only promote store items and must appear near Download badges. [search-api](https://performance-partners.apple.com/search-api)

### Recipes

#### TheMealDB
- "You can use the test API key "1" during development of your app or for educational use". You "must become a supporter if releasing publicly on an appstore". Endpoints: `search.php?s=`, `lookup.php?i=`, `filter.php?i=|c=|a=`. Thumbnails take `/small`, `/medium` or `/large` suffixes. Free keys are limited to 100 items when listing the full database. [api.php](https://www.themealdb.com/api.php)
- Caching and attribution terms: not documented on the API page.

#### Spoonacular
- Free plan: 50 points/day, 1 req/s, 2 concurrent requests, a backlink, and no card when you sign up directly (RapidAPI's free plan does require a card). [pricing](https://spoonacular.com/food-api/pricing)
- Terms: cache user-requested data "for a maximum of 1 hour". Only the recipe id, title and image URL may be stored indefinitely. [terms](https://spoonacular.com/food-api/terms)

#### Edamam Recipe Search
- No free plan. Basic is $9/mo (10-day trial, 10,000 calls/month). Caching only on paid plans and only for the subscribed end user. Attribution is required. [recipe API](https://developer.edamam.com/edamam-recipe-api)

### Anime / manga

#### Jikan (unofficial MyAnimeList API)
- "Jikan is not affiliated with MyAnimeList.net"; it scrapes MAL. "Please be respectful towards MyAnimeList's Terms Of Service." v3 is discontinued. [GitHub](https://github.com/jikan-me/jikan-rest)
- Public API: 60 req/min, 3 req/s, no daily limit. MAL may rate-limit separately. *(snippet of [docs.api.jikan.moe](https://docs.api.jikan.moe/))*

#### MyAnimeList official API
- Educational apps count as non-commercial. Content must come only through the API. Removed content must be deleted within 24 h of a request. Personal user information may not be stored server-side. [API agreement](https://myanimelist.net/static/apiagreement.html) Rate limits: not verified.

#### AniList (GraphQL)
- 90 req/min normally. Currently "in a degraded state and is limited to **30 requests per minute**". Raise requests are paused. [rate limiting](https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting)
- Terms: free under $150/month revenue. "Using the AniList API as a backup or data storage service is strictly prohibited"; no hoarding (with leniency for educational projects). [terms](https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/terms-of-use) (The GitBook copy was read because the newer docs.anilist.co returned 403.)

### Board games

#### BoardGameGeek XML API
- Since fall 2025, every request needs a token in `Authorization: Bearer …`, from an approved application registered at boardgamegeek.com/applications. Usage limits are "still being determined"; caching is recommended. *(snippet of [using_the_xml_api](https://boardgamegeek.com/using_the_xml_api))* See also the BGG announcement thread [registration now open](https://boardgamegeek.com/thread/3525319/registration-to-use-the-xml-api-and-obtain-soon-to).
- Terms: non-commercial only, no modifying data, credit BGG, a "Powered by BGG" logo linked back, and no AI training. *(snippet of [XML API Terms of Use](https://boardgamegeek.com/wiki/page/XML_API_Terms_of_Use))*
- **Python:** XML parsing (`xml.etree` / `defusedxml`).

---

## 4. Unverified / open questions

- **Open Library data license:** No named license (e.g. CC0) was found, only "does not assert any new copyright". ISBN availability in `search.json` is not in the documented example; test `fields=key,title,author_name,first_publish_year,cover_i,isbn`.
- **Open Library covers:** No explicit rule on downloading and storing cover image files locally. Hotlinking is the documented path.
- **Google Books** default daily quota: not documented on an official page.
- **TMDB:** Whether account signup needs a credit card is not documented (none mentioned). How the 6-month cache limit applies to a user's personal saved list should be answered conservatively: refresh saved rows before 6 months.
- **OMDb:** Caching and commercial terms beyond the CC BY-NC 4.0 notice: not documented on the main page; the Legal page was not checked.
- **RAWG, TheMealDB, Gutendex, Jikan:** Caching/storage terms not documented.
- **IGDB, Discogs, BGG, Hardcover, Jikan rate limits:** Official pages blocked automated fetching. Figures come from search snippets of the official URLs and should be confirmed in a browser.
- **Spotify:** A secondary source reports further Dev-Mode quota changes on 2026-07-23; not confirmed on an official Spotify page.
- **AniList:** The date of the "degraded state" notice is unknown.
- **MyAnimeList official API:** Rate limits not verified.

---

## 5. Sources

Books
- https://openlibrary.org/developers/api
- https://openlibrary.org/dev/docs/api/search
- https://openlibrary.org/dev/docs/api/covers
- https://openlibrary.org/developers/licensing
- https://developers.google.com/books/docs/v1/using
- https://developers.google.com/books/terms
- https://developers.google.com/terms
- https://gutendex.com/
- https://github.com/garethbjohnson/gutendex
- https://docs.hardcover.app/api/getting-started/

Movies / TV
- https://developer.themoviedb.org/docs/getting-started
- https://developer.themoviedb.org/docs/faq
- https://developer.themoviedb.org/docs/rate-limiting
- https://developer.themoviedb.org/docs/image-basics
- https://developer.themoviedb.org/docs/authentication-application
- https://www.themoviedb.org/api-terms-of-use
- https://www.omdbapi.com/
- https://www.omdbapi.com/apikey.aspx
- https://www.tvmaze.com/api

Games
- https://rawg.io/apidocs
- https://api-docs.igdb.com/
- https://www.igdb.com/api

Music
- https://musicbrainz.org/doc/MusicBrainz_API
- https://musicbrainz.org/doc/MusicBrainz_API/Rate_Limiting
- https://musicbrainz.org/doc/About/Data_License
- https://musicbrainz.org/doc/Cover_Art_Archive/API
- https://www.discogs.com/developers
- https://support.discogs.com/hc/en-us/articles/360009334593-API-Terms-of-Use
- https://www.last.fm/api/tos
- https://developer.spotify.com/blog/2024-11-27-changes-to-the-web-api
- https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security
- https://developer.spotify.com/documentation/web-api/tutorials/february-2026-migration-guide
- https://developer.spotify.com/terms
- https://performance-partners.apple.com/search-api

Recipes
- https://www.themealdb.com/api.php
- https://spoonacular.com/food-api/pricing
- https://spoonacular.com/food-api/terms
- https://developer.edamam.com/edamam-recipe-api

Anime / manga
- https://docs.api.jikan.moe/
- https://github.com/jikan-me/jikan-rest
- https://myanimelist.net/static/apiagreement.html
- https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/rate-limiting
- https://anilist.gitbook.io/anilist-apiv2-docs/docs/guide/terms-of-use

Board games
- https://boardgamegeek.com/using_the_xml_api
- https://boardgamegeek.com/wiki/page/XML_API_Terms_of_Use
- https://boardgamegeek.com/thread/3525319/registration-to-use-the-xml-api-and-obtain-soon-to
