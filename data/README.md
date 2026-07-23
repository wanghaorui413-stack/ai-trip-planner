# Shanghai MVP Demo Mock Data

This directory contains structured Demo mock data for the Shanghai MVP trip planner and local RAG knowledge base.

These files are for product demonstration and local development only. They do not connect to real hotel inventory, payment systems, ticketing systems, official transport feeds, or ride-hailing platforms.

## Files

- `pois_shanghai.json`: 36 structured Shanghai POIs covering landmarks, food areas, neighborhoods, museums, parks, shopping areas, scenic walks, and theme park style attractions.
- `hotels_mock.json`: 14 mock hotel records across `economy`, `comfort`, and `luxury` categories.
- `transport_rules.json`: Demo estimation rules for `walking`, `metro`, and `taxi`.
- `city_tips.md`: Shanghai travel notes, budget guidance, route suggestions, and RAG retrieval hints.

## Field Conventions

- Field names use `snake_case`.
- JSON files use a top-level `metadata` object.
- Collection files use `items` for POIs and hotels, and `rules` for transport modes.
- Money ranges use `{ "min": number, "max": number, "currency": "CNY" }`.
- Duration ranges use `{ "min": number, "max": number }` in minutes.
- Coordinates are approximate and intended only for MVP ranking, clustering, and itinerary examples.
- `booking_required` means the planner should remind users to check reservation rules. It does not mean this project can book tickets.
- `inventory_supported` and `payment_supported` are explicitly `false` for hotel mocks.

## Safety Notes

- Do not treat prices, opening hours, coordinates, or booking hints as authoritative.
- Do not use these files to process real payments, confirm reservations, check hotel stock, issue tickets, or call real transport providers.
- When generating user-facing itineraries, describe data as estimates or suggestions and ask users to verify current official information before departure.
