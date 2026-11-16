# PROMPTS.md — AI Usage Log

This file is the record of AI use on this codebase. At the end of every
agent session, direct the agent to write the session log with this prompt:

> Append a session log to PROMPTS.md at the repo root, under today's date,
> newest entry at the top. Record every prompt I gave you this session, in
> order, including any corrections. End the entry with a short summary:
> the outcome, any places where I deviated from a recommended answer or
> asked follow-up questions, and anything that went sideways.

Two rules:

- Entries are added only by that prompt, never unprompted.
- New entries go at the top. Never rewrite or delete an old entry — the
  log is part of your work, and an honest log of a session that went
  sideways is worth more than a tidy one.

Each entry has this shape:

    ## YYYY-MM-DD — <one-line summary>

    ### Prompts
    1. ...

    ### Summary
    - **Outcome:** what was built and what was kept
    - **Deviations:** recommendations overridden, follow-up questions asked
    - **Sideways:** failures, wrong turns, and how they were caught

## 2026-11-16 — Researched free APIs, picked Open Library, built a tested console search script

### Prompts
1. `/research` Find free external APIs for a Django application where users search for items, save them, and add their own notes, ratings, or progress. Explore topics such as recipes, books, movies, television, games, music, and more. Compare promising providers using official documentation, including available data, free limits, signup requirements, etc...
2. `/grill-me` I need you to make me a short console script that makes a real request to OpenLibrary. I need it to: accept user input (i.e. search phrase or id), make a meaningful request to the external API, use credentials if required, clearly display selected results in console, handle unsuccessful/empty requests with messages.
3. A, search phrase only. This is just a test script. The final product will have more capability.
4. Is requests part of uv?
5. Is requests safe? Is PyPI reputable?
6. A, requests
7. B, standard.
8. A, one search, top 5. Final product should probably use pagination.
9. B, specific message for each situation.
10. A, uv project with script in scripts/. It'll have to be done eventually anyway.
11. B, pytest with faked responses.
12. My instructor stated "Do not put API keys or tokens in source code, prompts, research notes, or PROMPTS.md. Use environment variables or an ignored .env file. Confirm that credentials are excluded before committing to your public repository."
13. B, python-dotenv.
14. Okay, it looks like it works.
15. Could you explain how the API requests get made, retrieved, and displayed back to me in the console?
16. append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top (line 31); record every prompt the user gave you this session, in order, including any corrections; end the entry with a short summary: the outcome, any places where the user deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A background research agent wrote `docs/research/free-apis-for-catalog-app.md`, comparing 22 providers from their official docs. It recommended Open Library for books because it needs no key and allows local caching. A grill-me interview settled the design of a console script, which was then built:
  - The repo is now a uv project named `book-catalog-system`, with `requests` and `python-dotenv` as dependencies and `pytest` for development.
  - `scripts/openlibrary_search.py` searches Open Library and shows the top 5 results. Each result has title, author(s), first publish year and work ID. Every failure case gets its own message.
  - `tests/test_openlibrary_search.py` has 12 pytest tests that fake Open Library's responses. All of them pass.
  - The contact email for the `User-Agent` header is read from a git-ignored `.env` file. `.env.example` holds only a placeholder.
  - A real search for "dune herbert" returned 5 of 282 matches. The session ended with a walkthrough of how a request is made, checked and printed. Nothing has been committed yet.
- **Deviations:** Every final choice matched the recommended option (A, A, B, A, B, A, B, then B for `.env` loading). Follow-up questions came before the HTTP library choice: whether `requests` is part of uv, and whether `requests` and PyPI are safe. The instructor's credential rule (prompt 12) changed the plan. The contact email moved from source code into an environment variable and a git-ignored `.env`, which added a final question about how to load it. The user also pointed ahead to the final app: it will have more capability than the test script, and it should paginate.
- **Sideways:**
  - `uv init` found a uv workspace in the parent `CIDM3312` folder and added this repo to its member list. That edited a file outside the repo, and it failed because another project there is already named `book-catalog`. The added line was removed. The project was renamed `book-catalog-system` and dependencies were added with `--no-workspace`. A check confirmed the parent `uv.lock` was unchanged.
  - The work ID given for *Dune* in a design example (`OL893415W`) was wrong; the real search returned `OL893414W`. The test data was corrected.
  - The PowerShell pipe used for the test run added a stray byte-order mark (BOM) character to the query text. Typed input isn't affected, so the code wasn't changed.
  - The parent folder's activated `.venv` makes uv print a harmless `VIRTUAL_ENV` warning.
  - The AI's design summary quoted the user's real email in chat. It was kept out of all repo files, and a search of the repo confirmed that. This log uses placeholders only.
  - The research agent couldn't fetch some official pages (IGDB, Discogs, BoardGameGeek, Hardcover, Jikan rate limits). Those figures are marked "(snippet)" in the research file and should be checked by hand.

