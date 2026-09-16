# Django Rules

- Follow existing Django architecture.
- Prefer ORM.
- Use `select_related` / `prefetch_related` where appropriate.
- Keep business logic in services where the project already uses services.
- Do not put business logic in templates.
- Use forms/serializers for validation.
- Follow existing authentication and permission patterns.
