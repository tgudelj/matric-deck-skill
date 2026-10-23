# MATRIC Deck Skill agent instructions

- This is an independent public project. Keep changes within this repository; do not modify MATRIC application code, its manual or its build/release process for skill-only work.
- Keep the installable payload in `skills/matric-decks`. It must work without the developer tools, a MATRIC checkout, or MATRIC binaries.
- Use standard-library Python for the installed helpers. Keep deterministic authoring checks separate from claims about native import or live application behavior.
- Never commit users' decks, OBS collections, credentials, private configuration or MATRIC binaries. Use synthetic fixtures for tests.
- Changes to action/control compatibility should come from a verified catalog or the target implementation. Keep Stream Deck support experimental and preserve its documented exclusions.
- Run the independent tests and packaging after relevant changes. Optional native tests take an explicitly supplied MATRIC build and use isolated temporary collections; never use a real deck library or execute actions.
- Record meaningful changes and remaining limits in `docs/DEVELOPMENT.md`. Use `VERSION` for this project's releases, independently of the MATRIC deck format and application version.
- Keep `LICENSE` and `skills/matric-decks/LICENSE.txt` identical so direct skill installs retain the MIT notice.
- Document new C# classes and methods with XML comments. Prefer straightforward code and concrete dependencies.
