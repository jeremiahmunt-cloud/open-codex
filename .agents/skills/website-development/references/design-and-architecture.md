# Design and architecture decisions

## Match the project before choosing a stack

| Situation | Default approach | Escalate only when needed |
| --- | --- | --- |
| Existing repository | Keep its framework, router, components, and lockfile | Migrate only for a stated requirement or demonstrated limitation |
| Small brochure or campaign | Static HTML/CSS or an existing static-site tool | Add a server for real submissions or private content |
| Content-heavy public site | Existing CMS/static generation or server rendering | Add client state for interactions that require it |
| Dashboard or application | Existing app stack and typed data boundaries | Add auth and persistence according to actual users and data |
| Existing ChatGPT Site | Its Sites project and supported build/publish flow | Avoid editing a Library projection as ordinary source |

For a greenfield React project, choose a current supported framework only after checking the deployment target and current docs. Prefer TypeScript when consistent with the project. Do not hardcode a framework version in a reusable brief. Respect the user's explicit stack preference.

## Make the direction specific

Describe the intended hierarchy in a few sentences before building a substantial new design. Decide:

- Main message and action; secondary action if useful.
- Display and body typography, with a readable type scale.
- Surface, text, accent, muted, border, and focus colors with adequate contrast.
- Spacing scale, content width, image ratios, and mobile stacking order.
- Which elements move, why, and their reduced-motion alternative.

For luxury editorial work, consider warm ivory, charcoal, muted bronze, material close-ups, generous margins, and architectural photography. These are starting points, not mandatory brand colors. Do not claim the supplied tokens are an official Blessed Homes brand standard. For software, services, or dashboards, choose a direction appropriate to those audiences.

## Implement a system

Use shared containers, headings, buttons, controls, card variants, and spacing tokens. Scope theme CSS so it does not unexpectedly restyle an existing app. Use a grid that remains readable between screenshot sizes, not only at exact breakpoints.

Keep text as HTML. Place important hero copy on a stable surface or test its overlay across image crops. Preserve visible focus, natural reading order, zoom, and long-text wrapping. Do not use effects to hide important information or hijack scrolling.

Use realistic content lengths early. Three-word placeholders do not prove that actual property names, prices, or form errors fit.

## Keep performance observable

Size images for their use, reserve dimensions, and defer offscreen media. Avoid autoplay video and large animation libraries unless justified. Choose font loading and fallbacks deliberately. Measure with available project/browser tools; report measurements and conditions instead of inventing a score.
