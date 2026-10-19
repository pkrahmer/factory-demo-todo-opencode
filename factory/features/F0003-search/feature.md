# Search

## Goal

Find a todo without scrolling: a word from its title narrows the list. Done when `GET /todos?search=<text>` returns the todos whose title contains the text, ignoring case, and combines with the done filter.

## Scope

- Title search in the service and as a query parameter of `GET /todos`

## Out of scope

- Full-text search, ranking, fuzzy matching, search in anything but the title
- A search index or a repository method for it (the service filters what the repository lists)

## Stories

- S0001: Title search

## Decisions taken for the human

Product decisions taken while writing the stories or answering the pipeline's questions, for the human to review in one place. Each names where it was taken.

1. Search is a case-insensitive substring match on the title (Unicode case folding, so `STRASSE` finds `Straße`); the text is stripped first, and an empty text means no filter. (S0001, story text)
2. A search text longer than a title can be (200 characters) is rejected with 422 rather than silently matching nothing. (S0001, story text)
3. The search limit of 200 characters counts the text as sent, before stripping, as the schema's `max_length` does; a padded search of more than 200 characters is a 422 even if its stripped text is shorter. (S0001, story text; F0003's acceptance at the shakedown, 2026-10-18)
4. `search=None` means no title filter, like an empty or blank text. (S0001, story text)
