# Phase 5 Security / QA Review

## Summary
This document records the Phase 5 backend security and QA review for the Travel Cambodia backend.
It also documents the specific fixes applied during QA, including the service request / ticket bug and access-rule validation.

## Review Scope
- Admin and user permission enforcement
- Private itinerary data access control
- Support ticket / service request API flow
- Error response polish
- Formal validation via automated tests

## What was audited
- `accounts` API endpoints for admin-only access:
  - `GET /api/accounts/admin/users/`
  - `POST /api/accounts/admin/users/create/`
  - `DELETE /api/accounts/admin/users/<pk>/delete/`
  - `GET /api/accounts/admin/roles/`
  - `POST /api/accounts/admin/roles/assign/`
  - `POST /api/accounts/admin/roles/remove/`
  - `GET /api/accounts/admin/permissions/`
  - `POST /api/accounts/admin/roles/permissions/assign/`
  - `POST /api/accounts/admin/roles/permissions/remove/`
- Support ticket endpoints:
  - `GET/POST /api/accounts/support-tickets/`
  - `GET /api/accounts/support-tickets/<pk>/`
  - `POST /api/accounts/support-tickets/<pk>/respond/`
- Itinerary endpoints:
  - `GET/POST /api/itineraries/`
  - `GET/PUT/DELETE /api/itineraries/<pk>/`
- Admin content endpoints for places/cities/categories/reviews/tickets
- Public discovery endpoints for places, cities, categories

## Fixes implemented
- Removed duplicate `ItinerarySerializer` definition in `itineraries/serializers.py` that was overriding the itinerary serializer with ticket fields.
- Added explicit QA tests for:
  - unauthenticated access denial on itinerary list/detail endpoints
  - admin role/permission endpoint restrictions
  - admin self-delete prevention
  - support ticket authentication and admin response flow
  - admin-only access to itinerary admin content endpoints
  - user-only access to their own service request details
- Confirmed `ServiceRequestListCreateView` and `ServiceRequestDetailView` now return only permitted objects.
- Added custom DRF exception handling in `accounts/exceptions.py` for better user-facing error JSON.

## Evidence of validation
- Tests run successfully:
  - `python manage.py test accounts itineraries`
- System check passed:
  - `python manage.py check`

## Results
- The Phase 5 backend implementation is no longer partially broken.
- The service request / ticket data flow has been audited and corrected.
- Support ticket backend endpoints are now documented and backed by tests.

## Remaining front-end/interface work
- This document covers backend QA and security validation only.
- The support ticketing flow is implemented backend-side with final endpoints available, but UI integration is still a front-end task.
- The next step is to wire these endpoints into the front-end user/admin interfaces.
