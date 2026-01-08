# Perpee - Product Requirements Document

**Version:** 1.0  
**Last Updated:** January 6, 2025  
**Status:** Ready for Implementation

---

## Executive Summary

### What is Perpee?

Perpee is an AI-powered price monitoring agent for Canadian online retailers. Users can add products via URL or natural language chat, and Perpee will automatically track prices, detect changes, and send email alerts when prices drop or meet user-defined conditions.

### Key Value Proposition

| Feature | Description |
|---------|-------------|
| **Conversational Interface** | Add and manage products through natural chat instead of complex forms |
| **Intelligent Extraction** | Automatically extracts product data from supported retailers without manual configuration |
| **Scan Website** | Can scan a new website's structure to validate it's safe before adding to whitelist |
| **Self-Healing** | Automatically recovers when website structures change |
| **Cross-Store Comparison** | Track the same product across multiple retailers |
| **Budget-Friendly** | Designed to run on free-tier infrastructure (~$10/year) |

### Target User

**Primary Persona:** A reseller business automating deal-hunting across Canadian stores.

**User Profile:**
- Tracks 50-500 products across multiple stores
- Wants "set and forget" monitoring with alerts
- Comfortable with basic web interfaces
- Values simplicity over advanced features

---

## Scope

### In Scope (MVP)

| Area | Details |
|------|---------|
| Geography | Canadian retailers only |
| Users | Single user (no authentication) |
| Interface | Web application |
| Notifications | Email only |
| Product Addition | Manual (URL paste or chat) |
| Alerts | Basic price alerts (target price, % drop, any change, back in stock) |

### Out of Scope (Post-MVP)

- Mobile app / browser extension
- Multi-user / authentication
- Real-time price updates (daily is sufficient)
- Price prediction or analytics
- Social features / sharing
- Affiliate monetization
- Slack / Discord notifications
- Push notifications

---

## Problem Statement

### The Problem

Online prices fluctuate frequently. Resellers miss deals because:

1. **Manual checking is tedious** - Visiting multiple sites daily is unsustainable
2. **Existing tools are limited** - Many price trackers only support Amazon or require browser extensions
3. **No intelligent recovery** - When a site changes layout, traditional scrapers break silently
4. **Poor UX** - Most tools require filling forms instead of natural interaction
5. **Access to Latest Price** - Must visit the website every time to get the latest price
6. **Product Data Availability** - Have to manually add product information when selling

### The Solution

Perpee solves this by providing:

1. **Chat-first interface** - "Track the PS5 on Walmart and Best Buy" just works
2. **Multi-retailer support** - Works with any supported Canadian retailer
3. **Scan Website** - Validates new websites are safe before adding to whitelist
4. **Self-healing scrapers** - Automatically adapts when sites change
5. **Proactive alerts** - Get notified only when action is needed
6. **Quick Access to Latest Price** - Database stores product data for instant lookup
7. **Intelligent Extraction** - Automatically extracts product data without manual configuration

---

## Goals & Success Metrics

### Primary Goals

| Goal | Success Metric | Target |
|------|----------------|--------|
| Reliable price tracking | Successful scrape rate | >95% |
| Timely alerts | Alert delivery time after price change | <30 min |
| Low maintenance | Self-healing success rate | >80% |
| Cost efficiency | Monthly operational cost | <$1 |
| User satisfaction | Products actively tracked | >50 |

### Key Results (MVP Launch)

- [ ] Successfully track products from 16 P0 stores
- [ ] Daily price checks running reliably
- [ ] Email alerts delivered within 30 minutes of detection
- [ ] Self-healing recovers from 80%+ of selector breakages
- [ ] Total monthly cost under $1

---

## User Stories

### Core User Stories (MVP)

| ID | As a... | I want to... | So that... | Priority |
|----|---------|--------------|------------|----------|
| US-01 | User | Add a product by pasting a URL | I can start tracking its price immediately | P0 |
| US-02 | User | See current price and price history | I know if now is a good time to buy | P0 |
| US-03 | User | Set a target price alert | I get notified when the price drops to my target | P0 |
| US-04 | User | Compare prices across stores | I can find the best deal | P0 |
| US-05 | User | View all my tracked products | I can manage my watchlist | P0 |
| US-06 | User | Remove a product from tracking | I can clean up items I no longer want | P0 |
| US-07 | User | Set a custom check schedule | I can control how often prices are checked | P0 |
| US-08 | User | Receive email notifications | I'm alerted even when not using the app | P0 |
| US-09 | User | See which products have issues | I know if tracking is broken | P1 |
| US-10 | User | Chat naturally with the agent | I don't need to learn specific commands | P0 |

### Agent Behavior Stories

| ID | As the... | I should... | So that... | Priority |
|----|-----------|-------------|------------|----------|
| AG-01 | Agent | Extract product data automatically | Users don't configure selectors manually | P0 |
| AG-02 | Agent | Recover from scraping failures | Tracking continues without user intervention | P0 |
| AG-03 | Agent | Respect rate limits and robots.txt | I don't get blocked by retailers | P0 |
| AG-04 | Agent | Confirm destructive actions | Users don't accidentally delete data | P1 |
| AG-05 | Agent | Stay focused on price tracking | I don't go off-topic or hallucinate | P0 |
| AG-06 | Agent | Link same products across stores | Users can compare prices easily | P1 |
| AG-07 | Agent | Scan new websites before whitelisting | Users can safely add stores not in the default list | P0 |

---

## Constraints & Assumptions

### Technical Constraints

| Constraint | Details |
|------------|---------|
| Budget | ~$10/year operational cost |
| Hosting | Oracle Cloud Free Tier (1GB RAM, limited CPU) |
| LLM Cost | Must use free/cheap models primarily |
| Storage | SQLite only (no managed DB cost) |
| Architecture | Single Docker container |

### Assumptions

| Assumption | Risk if Wrong |
|------------|---------------|
| Canadian retailers allow scraping (with rate limits) | Core functionality breaks |
| Free LLM models provide adequate function calling | Agent reliability suffers |
| Daily price checks are sufficient | Users want real-time updates |
| Single user is enough for MVP | Need auth sooner than planned |
| Sites use standard product markup (JSON-LD, meta tags) | More LLM extraction needed (cost) |

### External Dependencies

| Dependency | Type | Risk Level | Mitigation |
|------------|------|------------|------------|
| OpenRouter API | External service | Medium | Multiple model fallbacks |
| Crawl4AI | Open source library | Low | Can fork if needed |
| ChromaDB | Open source library | Low | Can migrate to pgvector |
| Resend | External service | Low | Many email alternatives |

---

## Security Requirements

### High Priority

| Risk | Mitigation |
|------|------------|
| SSRF via user URLs | Domain whitelist + block private IPs + scan_website validation |
| Prompt injection | Separate user input from system prompts |
| XSS via scraped content | 4-layer sanitization (Crawl4AI → extraction → storage → frontend) |
| Resource exhaustion | Rate limits, timeouts, response size limits |
| Cost runaway | Daily token limits, hard caps |

### Medium Priority

| Risk | Mitigation |
|------|------------|
| API error leakage | `debug=False`, standardized error responses |
| Scraper detection | Realistic headers, rate limiting, stealth mode |

---

## Supported Stores

### P0 - MVP Launch (16 stores)

| Category | Stores |
|----------|--------|
| General | Amazon Canada, Walmart Canada, Costco Canada, Canadian Tire |
| Electronics | Best Buy, The Source, Memory Express, Canada Computers, Newegg |
| Grocery | Loblaws, No Frills, Real Canadian Superstore, Metro, Sobeys |
| Pharmacy | Shoppers Drug Mart |
| Home | Home Depot Canada |

### Store Addition Policy

- **Whitelisted stores (P0/P1/P2):** Work immediately with pre-configured selectors
- **New stores:** Must use `scan_website` tool to validate safety and feasibility first
- **After successful scan:** Store added to whitelist with learned selectors

*See Technical Spec Appendix A for full P1/P2 store lists.*

---

## Cost Budget

| Component | Monthly | Yearly |
|-----------|---------|--------|
| Hosting (Oracle Free Tier) | $0 | $0 |
| Database (SQLite + ChromaDB) | $0 | $0 |
| LLM (OpenRouter free tier) | ~$0.50 | ~$5 |
| Embeddings (OpenAI) | ~$0.10 | ~$1-2 |
| Email (Resend free tier) | $0 | $0 |
| **Total** | **~$0.60** | **~$7** |

---

## Future SaaS Migration Path

When transitioning from single-user MVP to multi-user SaaS:

| Component | MVP | SaaS |
|-----------|-----|------|
| Database | SQLite | Supabase (PostgreSQL) |
| Vector DB | ChromaDB | Supabase (pgvector) |
| Auth | None | Supabase Auth |
| Notifications | Email only | Email + Push + Slack/Discord |
| Scheduling | Daily minimum | Hourly+ for paid tiers |

---

## Document References

| Document | Purpose |
|----------|---------|
| `TECHNICAL_SPEC.md` | Detailed architecture, component specs, schemas |
| `API_REFERENCE.md` | API endpoints (extracted from Tech Spec C8) |

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | Jan 6, 2025 | Initial MVP PRD - split from combined PRD/Tech Spec |

---

*This PRD defines WHAT to build and WHY. See TECHNICAL_SPEC.md for HOW to build it.*
