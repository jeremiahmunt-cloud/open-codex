# Website quality checklist

Scale checks to the change. Record actual commands, viewport sizes, and results. A build pass does not establish visual quality or data protection.

## Build and behavior

- Run relevant build, type, lint, and existing test commands.
- Exercise navigation, mobile menu, deep links, primary CTA, and any gallery, filter, search, accordion, or download.
- Check empty content, long content, missing images, loading, failure, and success states that can occur.
- For forms, verify client/server validation, keyboard submission, duplicate handling, error recovery, and receiving-system confirmation. Do not send test messages to real people without authorization; use a test destination and report that scope.
- For private views, test unauthenticated and unauthorized requests to pages and data endpoints. Check built assets for private fixtures and credentials.

## Visual and accessibility review

- Inspect approximately 390 px mobile, 768 px tablet, and 1440 px desktop widths, plus narrow widths and zoom where the layout is at risk.
- Capture and actually inspect mobile and desktop screenshots. Check overflow, overlap, cropping, text wrapping, balance, and content below the fold.
- Test keyboard order, focus visibility, semantic headings/landmarks, descriptive links, form labels, and error association.
- Check text/control contrast. Use WCAG 2.2 AA as an engineering target; verify current W3C criteria before claiming conformance.
- Check menus/dialogs for appropriate Escape behavior, focus restoration, and keyboard operation.
- Respect reduced motion. Avoid scroll hijacking, uncontrolled carousels, and information conveyed only through color or animation.
- Use automated accessibility tools when available, followed by manual checks. Do not equate an automated pass with full compliance.

## Content and delivery

- Confirm prices, specifications, availability, claims, and source dates. Distinguish unknown, verified, and synthetic records.
- Verify usage rights and adjacent concept/staging labels for property images.
- Check titles, descriptions, social previews, favicon, and intended indexing. Use accurate schema only.
- Check image sizes/dimensions, unnecessary scripts, and fonts. Report measured performance with context.
- Verify environment-variable names without printing values. Exclude `.env` and private source material from commits.
- State whether a preview is local, shareable, or production. Check the actual URL after authorized deployment.
- Mark checks blocked by unavailable browser, dependencies, credentials, or services as not run, with the consequence.
