# Internationalization

Phase 22 adds English and Bulgarian as first-class presentation
languages for MAT-PAL. Language changes how content is shown. It
does not change catalog IDs, mastery, adaptive policy, answers, or
student-profile identity.

## Supported Locales

- `en` — English
- `bg` — Bulgarian (`Български`)

Default and fallback: `en`.

Unknown, blank, or missing values normalize to `en`.

## Browser Persistence

Frontend stores the selected locale in `localStorage` under:

    matpal_locale

Rules:

- missing → `en`
- malformed/unknown → `en`
- `"en"` → `en`
- `"bg"` → `bg`

Language is independent of student profile. Switching student does
not switch language. Switching language does not switch student.

## Frontend Architecture

A small internal layer lives in `frontend/i18n/`:

- `types.ts` — `Locale = "en" | "bg"`
- `en.ts` / `bg.ts` — dictionaries keyed by stable ids such as
  `nav.learn`, not by English source text
- `index.ts` — `normalizeLocale`, `loadLocale`, `persistLocale`,
  `translate`, catalog/trend helpers

`LanguageProvider` and `useLanguage()` expose:

- `locale`
- `setLocale`
- `t(key, params?)`

Do not introduce Redux or a heavy i18n framework for two locales.

Catalog routing and API calls continue to use stable English IDs.
The frontend maps those IDs to localized display labels (Option B).
Generated problem prose comes from the backend when `language` is
supplied.

## Header Language Switch

Desktop DOM order:

1. MAT-PAL brand
2. student selector
3. Add profile
4. EN | BG
5. Learn
6. Progress
7. Log in

The control is a compact accessible segmented switch. No country
flags. No page reload. It also appears on the login page through
the shared header.

On narrow viewports the header wraps. Controls stay usable; the
layout must not rely on horizontal scrolling.

## Backend Session Language

Tutor content is created server-side, so locale is sent explicitly
on content requests:

- `POST /sessions/start` — `language: "en" | "bg"` (default `en`)
- `POST /problems/generate` — `language` (default `en`)
- `GET /problems/{id}?language=`

The frontend API client passes `language` as an argument. It does
not read a hidden global inside `api.ts`.

Old callers that omit `language` continue to receive English.

Progress, mastery, and student identity endpoints stay
language-neutral. Do not attach locale to progress identity.

Unknown backend language values normalize to `en`.

## Session Language Rule

A tutor session keeps the language chosen at start.

If the UI language changes while a tutor session is active, the
frontend clears/exits that session. This avoids mixed-language
tutor state, the same safety idea used when switching profiles.

A new session started after the switch uses the new locale.

Ask-a-question (Phase 23) uses that same stored session language.
The question engine does not infer output language from whether the
learner typed English or Bulgarian.

## Catalog Localization

Internal IDs stay stable:

    mathematics, physics, primary_school, ode,
    classical_mechanics, word_problems,
    first_order_linear, separable_equations, kinematics

Only display names and descriptions localize. Routing never uses
translated strings.

## Tutor Localization

Primary School, linear ODE, separable ODE, and kinematics share
one engine per topic. Message templates are selected by locale.

Do not duplicate engines per language.

Do not translate:

- internal IDs
- JSON keys / API field names
- mathematical variable names
- LaTeX
- SI unit symbols
- student-created profile names (`Student_B` stays `Student_B`)

`Guest` is a system label and may display as `Гост`.

Generated problems keep the same quantities and expected answers
for the same seed and difficulty. Only statement/title/prompts
change with locale.

## Progress Localization

Progress JSON stores English IDs and language-neutral codes such as
`strong`, `stable`, `needs_support`, and `insufficient_history`.
The UI translates labels only.

## Adding a Future Locale

1. Add the locale code to backend `SUPPORTED_LOCALES` and frontend
   `Locale`.
2. Add a dictionary file and register it in `frontend/i18n/index.ts`.
3. Add matching tutor message catalogs under `src/core/i18n/`.
4. Extend the language switcher.
5. Add helper and localization tests.

Keep IDs, math, and progress storage unchanged.

## Current Limitations

- Detailed ODE checker diagnostics for incorrect algebraic
  transformations may still appear in English. Stage prompts,
  titles, hints, and kinematics feedback are localized.
- Catalog list endpoints return English display names; the
  frontend maps known IDs. Problem detail/generate include
  localized prose when `language` is supplied.
- Adaptive recommendation `reason` strings from the policy remain
  English in the API. The UI rebuilds localized copy from
  `adjustment_reason` and topic IDs.
- Authentication is still a placeholder and is only translated in
  the login UI.
