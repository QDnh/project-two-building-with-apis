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

## 2026-11-16 — Grilled the Book Catalog System design, prototyped the UI and privacy rules, wrote the PRD

### Prompts
1. `/grill-me @project-idea.md`
2. C looked good, but those missing author keys sound like potential future trouble. Option A is probably best. You did say it was the standard.
3. I was originally thinking Option A. Option B sounds better. However, I want to make sure it doesn't add a lot of code.
4. Star rating should not be required. The rating options for users should be full stars. The actual public rating of the book can be up to one decimal point. We should probably lock rating behind saved books, similar to read status.
5. This question ties into other things too. So, I don't think the privacy thing is much of an issue. If there is a book with five stars, it doesn't necessarily reveal who rated it that way. It would only do so if that user selected to share they saved the book. Even then, would the book's page even show the users who have it saved? It makes much more sense to have that on user profiles. At that point, the user would have to share they saved the book. Lastly, ratings are usually public anyway. As for this question, it is probably best to have just this app's community. Since it is just a college assignment, it will probably help me perform manual tests. We can also seed ratings if needed.
6. Let's make this user profile focused. This app is for users to find, save, and rate books. If some users have no interest in sharing anything, fine. If other users want to share some saved books and not others, that should be allowed. It should be per book, so users can build a profile. If a user wants everything shown, they'll need to set them all public. Nice catch on ratings. A rating should not be public unless a user selects it to be. Whether books say how many ratings there are or not, it won't give anything away if that user hasn't saved that book publically.
7. Wouldn't B technicaly be a security risk? If profiles are shown by username, malicious actors already have half the puzzle. I suppose email would be required to contact users, perform account recovery (technically solves security issue), and could hypothetically be used for two-factor auth (we won't worry about that for this project).
8. Let's go with B. We won't worry about email stuff, just store it. I think recovery is out of scope for this project.
9. Nothing is going to actually be sent to OpenLibrary, right?
10. Option B. How easy would it be to add expirations to the tokens, or would that even be necessary here?
11. Option A. Mark description saving as future work. I wasn't told exactly what "enough information" meant, so I'll make a judgement call and leave it out.
12. Wait, now I'm confused. Wouldn't browse be viewing books from OpenLibrary, or am I misunderstanding here?
13. Oh, okay. In that case, yes, it would only show that user's saved books. Why would it show other users' books?
14. Option B. In this case, it makes no sense for someone without an account with us to use our service. They could literally just use OpenLibrary itself for browsing, since OpenLibrary actually has the books. We just store lists of the books users save.
15. Option A. If we force logins for public profiles, we basically make the social aspect of our app useless. Unless we add rating descriptions or a list of users, there is no way to find other users. This creates a share based discovery system. If logged out users can't see public profiles, they can't share their collection with friends not on the platform.
16. Option B. It isn't really even a trade-off. If OpenLibrary is down, users can't search to even find an unsaved book. If they find a book from a friend's profile, the book is already saved on our side. Am I getting that right?
17. For the save button on public profiles, I meant finding the books page from the friend's profile. If we have a book saved, I imagine the book's page will stay available even if OpenLibrary is down, right? For this question, Option C seems convenient. Having something a hypothetical IT department could use to quickly prune unsaved books could be helpful if the website starts lagging heavily or something. Additionally, I will clarify that our database should NOT be able to delete a book that is currently saved.
18. I'm realizing we might have some consistency issues. Public profiles are visible, the catalog is not. If we allow logged out users to view book pages, it defeats the point of hiding the catalog, because the book page has a save button. Yet, it also would be strange for a user to send their profile to a friend, but that friend can't access any of the book pages on said list. As for book pages itself, it doesn't violate privacy because it doesn't say who has saved it. Before we make a decision and move on, we should probably get things consistent.
19. I agree, let's do Option A. Also, I called the Find Books page a catalog. I forgot we mentioned a all saved books catalog. Yes, mark that as future work. We really should get consistent names too. This is a Book Catalog System, so Find Books -> Browse Catalog. My Library -> Saved Books. The rest work as is. The future work catalog should probably be the Saved Book Catalog. What do you think; a bit more clear?
20. I like your modifications better. Since we are doing Option A, do we still need the change to the books URL?
21. Keep the Open Library ID, store the short form. I like it.
22. What is the work difference between B and C?
23. Do C. I'm not sure what my instructor meant by entries, so I'll play it safe.
24. Option B, with the filtering logic in one function. I agree, Option A is just too small. Do you think I should have you prototype this now, or do you have some more questions about this page first?
25. What about status and sharing on the Saved Books page, and Rating on the Book Page?
26. So the search features reload the HTMX, but the status/public doesn't. I like that. It is convenient if a user accidentally changes status/public on the wrong book, or sets the status to the wrong state (since there is three).
27. What is stopping the user from just clicking the search button again?
28. Yes, I agree. Option A. I'm glad I caught that with the retry button.
29. Option B is the only practical option here. I like your rate limit protection too. Most users who are looking for something specific, will likely check page two or three before refining their search. Users who are just browsing have 200 options.
30. Option B. Ideally, we want each feature contained within its own app. However, the limit is when we have to import constantly.
31. Option B, with the safety net fixture. We CANNOT allow our tests to call the actual OpenLibrary.
32. Option A is not ideal. Option B is tedious. Option C it is.
33. Option C. Why would we go with anything else?
34. Option B. Quick question. How difficult would ISBN searches be?
35. Yes, ISBN search in Search Catalog only. If a user has the book saved, they probably won't search for it using an ISBN.
36. Actually, it is best to prototype now BEFORE we make a PRD. The question is, what needs prototyping?
37. `/prototype` Start with the Saved Books UI prototype
38. I like Option A the best. This design works so well I am actually questioning if we should allow rating changes here too.
39. Add the clickable stars to the prototype first
40. Not quite sure about mobile proportions. Not going to worry about it for this project. It works great.
41. Build the privacy logic prototype next
42. I think it works well.
43. `/to-prd`
44. append a session log to PROMPTS.md at the repo root, under today's date, newest entry at the top (line 31); record every prompt the user gave you this session, in order, including any corrections; end the entry with a short summary: the outcome, any places where the user deviated from a recommended answer or asked follow-up questions, and anything that went sideways.

### Summary
- **Outcome:** A grill-me interview worked through 24 design questions for the Book Catalog System:
  - **Data model:** a shared `Book` table and a per-user `SavedBook`.
  - **User data:** three reading statuses, an optional 1–5 rating, and per-book public sharing.
  - **Accounts:** a custom user with a unique email.
  - **Saving:** done by Open Library work ID, with the server fetching the book details itself.
  - **API:** DRF with session and token authentication.
  - **Pages:** consistent page names, chosen access rules, and filters, sorts and pagination.
  - **Testing:** a test safety net that blocks real network calls.

  Two throwaway prototypes followed:
  - `prototypes/saved-books-ui.html`: the user chose Variant A, "Shelf grid", and rating moved onto the cards.
  - `prototypes/privacy-logic.html`: the privacy rules were confirmed with no changes.

  `prototypes/README.md` records both results. `/to-prd` then wrote `prd/book-catalog-system.md`, with 76 user stories, the implementation decisions, the out-of-scope list and further notes. No production code was written. Nothing was committed.
- **Deviations:**
  - *Overrode the recommendation:*
    - **Public rating:** the app's own community average instead of Open Library's rating. The user argued an anonymous average doesn't reveal who rated.
    - **Sharing:** per book instead of a profile-wide switch.
    - **Pruning:** a `prune_books` command (C) instead of keeping books forever (A), plus the explicit rule that saved books can't be deleted.
    - **Book API endpoint:** added (C) "to play it safe" about what "entries" means.
    - **Rating:** first only on the book page, then onto the cards after the prototype.
    - **Ordering:** prototype *before* the PRD, which reversed the suggested order.
  - *Started on one option and moved to the recommended one:* data model (C → A) and status (A → B, after asking how much code it adds).
  - *Proposed changes the AI adopted:* new page names (Search Catalog / Saved Books, with the AI's tweaks to two of the names), and the status and sharing controls on cards.
  - *Questions that changed decisions:*
    - The user caught the inconsistency between hidden-catalog and public book pages, which led to separating privacy rules from scope.
    - The user caught that a retry button duplicates the Search button, so it was dropped.
    - The user asked whether the Open Library ID URL was still needed after Option A. It was kept, for stable links.
  - *Other follow-up questions:* whether a public username is a security risk; what gets sent to Open Library; whether token expiry is needed; the work difference between API options B and C; why choose anything other than vendored HTMX; how hard ISBN search would be; and what actually needs prototyping.
- **Sideways:**
  - Unclear naming from the AI caused confusion. "Browse" and "Find Books" were mixed up (prompt 12). The hidden "Catalog" was first described in privacy terms when it was really a scope decision (prompt 18). Both were fixed with a glossary and a reframed privacy model.
  - The AI misread "save button on public profiles" as a button on the profile itself. The user clarified they meant the book page reached from a profile (prompt 17).
  - The AI recommended a "Try again" button that duplicated the existing Search button. The user caught it, and the recommendation was revised.
  - For API options B vs C, the AI's recommendation softened from B to "either is fine" once the actual difference turned out to be about 15 lines.
  - Neither prototype could be run or syntax-checked in the session: `python` resolves to the Microsoft Store alias, and Node isn't installed. The user opened them in a browser and reported they worked. Before handoff, the AI found and fixed two small bugs by reading the code: a "Saved ✓" flash that came back after list refreshes, and a leftover dead condition in the privacy demo.
  - The single-rater edge case (a lone private rating shows up as the "community average") was put to the user. Their "works well" was recorded as accepting it, with a note that the README should explain it.

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

