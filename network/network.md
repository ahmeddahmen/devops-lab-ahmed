# Network Specification

## Networks

| Name | CIDR | Gateway | Hosts | Purpose |
|----------|---------------|------------|-------|----------------------------|
| frontend | 172.20.0.0/24 | 172.20.0.1 | 254 | Public services (web) |
| backend | 172.21.0.0/24 | 172.21.0.1 | 254 | Internal (API, database) |

## Rules

- The frontend and backend networks must not overlap.
- Only services on the frontend network are exposed to users.
- The database is connected to the backend network only.

## Change history

This file is managed with Git. Run: git log network/network.md
