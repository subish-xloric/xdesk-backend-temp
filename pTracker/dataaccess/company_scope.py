""" Company filter for the per-company lookup lists (job titles, leave types,
project activities).

Pass the company id to get one company's rows. Passing None - e.g. no active
company could be resolved for the request - yields NO rows, never every
company's. Only an explicit ALL_COMPANIES returns rows across companies; it is
for id -> name lookups of existing records, never for lists shown to a user.
"""

ALL_COMPANIES = object()


def filter_by_company(queryset, company_id):
    if company_id is ALL_COMPANIES:
        return queryset
    if company_id is None:
        return queryset.none()
    return queryset.filter(company_id=company_id)
