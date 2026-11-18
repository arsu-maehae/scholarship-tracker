# Worldwide web suggestions

The catalogue remains the source of structured, reviewed search results. Keywords search title, scheme and description together with the other catalogue filters. When Find scholarships is pressed, the app also sends a search phrase based on the selected filters to Brave and displays separate web suggestions inside the app. Web suggestions can be unrelated or outdated; they do not prove eligibility, funding, a deadline, or a match to every filter. Check the awarding organisation's official page.

In-app web search is disabled by default and requires `BRAVE_SEARCH_ENABLED=true` and a Brave Search API key. Do not enable it under the current zero-spending requirement. Obtain one from https://api-dashboard.search.brave.com/ and add `BRAVE_SEARCH_API_KEY` to the existing project-root `.env`; restart the backend. Do not share or commit the key. Review current plans and costs at https://brave.com/search/api/ before signing up. Each search and web retry sends the displayed search phrase to Brave and may use the account's quota or credits.

If the key is absent or the provider is unavailable, the web section shows an unavailable message while catalogue results continue working. Provider output is unverified and is not saved to the catalogue. To add an opportunity, follow `docs/CATALOGUE_REVIEW.md` and check the official source before publishing.
