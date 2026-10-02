# FloodGuard Africa

## Pitch deck — free access for residents, paid intelligence for organizations

Prepared October 2, 2026. Suggested presentation: 8–10 minutes.

Each numbered section is one slide. Speaker notes are for the presenter, not the slide body. Business models, prices, and milestones below are proposals to validate; they are not existing contracts or revenue.

---

## 1. Local flood intelligence, starting in Lagos

**Help communities understand rainfall risk and help organizations prepare for disruption.**

- Starting with Lekki and Ikosi-Ketu.
- A working rainfall-screening prototype with historical replay and traceable evidence.
- Our intended model: residents access the core service free; organizations fund monitoring and analysis.

**Speaker notes:** FloodGuard is an early research product. Our ambition is useful local flood intelligence. Today, we can demonstrate rainfall screening, historical evidence, and a reproducible evaluation workflow. We have not established operational flood-prediction accuracy.

---

## 2. The problem

**Rainfall forecasts alone do not tell people whether their street will flood.**

- Local drainage, tides, rivers, and earlier rainfall can change what happens on the ground.
- Historical reports often identify a day or broad area without establishing flood onset.
- Residents and operators need understandable information with its location, timing, and uncertainty visible.

**Speaker notes:** Our own research encountered these gaps. A report of flooding somewhere in Lagos is not neighborhood-level ground truth. The product must distinguish what is known, what is inferred, and what remains unknown. The examples supporting this problem are documented in our [historical evidence review](data/backtest/historical/report.md).

---

## 3. The product

**A clear rainfall outlook connected to an auditable local evidence record.**

- See low, moderate, or high rainfall screening for four six-hour windows.
- Inspect forecast dates, rainfall amounts, and the rule behind a flagged window.
- Replay historical events and compare original and sensitive rules.
- Submit observations for review, including actively monitored non-flood periods.

**Speaker notes:** These capabilities exist in the prototype. Observations remain pending until reviewed. A low rainfall screen does not mean no flood risk. Public alert delivery, enterprise workflows, and validated flood probabilities are future work.

---

## 4. The demonstration

**Follow one documented storm from rainfall input to reviewable result.**

1. Open a dated Lekki historical example.
2. Compare original and sensitive rainfall rules.
3. Inspect the six-hour windows and source evidence.
4. Record a demonstration observation and show its pending-review status.

**Speaker notes:** Run `npm run demo`. Use `/replay` and `/performance`. The demo works from local historical caches and stores submissions in a separate demo database. Historical examples are labelled with their dates; they are not current conditions. Source websites and map tiles require internet.

---

## 5. How the evaluation works

**Preserve the evidence and replay the same rules reproducibly.**

- Cache weather inputs and source records with checksums.
- Review candidate flood reports for location, date, cause, and duplicate storms.
- Separate archived model-run experiments from older ERA5 rainfall diagnostics.
- Keep missing evidence unknown; do not count silent news coverage as “no flood.”

**Speaker notes:** The recent daily comparison assumes model availability six hours after initialization, then selects an eligible run at midnight Lagos. This is a standardized simulation, not proof of exactly what a user could have seen. The early provider archive is a hindcast. Precise 6/12/18/24-hour flood-onset evaluation needs more precise event timing. The 2025 examples were inspected during sensitive-rule development and are not an untouched test for that version.

---

## 6. What the prototype has shown

**More sensitive rules flag the documented days; warning usefulness remains unproven.**

- **2024–2025 archived model comparison:** original rules flagged 0 of 4 reviewed flood area-days; sensitive rules flagged 4 of 4, across 3 storms.
- **Older rainfall diagnostic:** original rules crossed thresholds on 1 of 5 accepted days; sensitive rules did so on 5 of 5, using ERA5 reanalysis.
- **Background check:** sensitive rules flagged 10 of 58 covered area-days in August 2025; 9 alerts had unknown outcomes.
- False-alarm performance and advance flood-warning lead time remain unestablished.

**Speaker notes:** Do not present these results as “100% accuracy” or merge the two experiments into one score. The recent examples informed development; the older analysis uses retrospective rainfall rather than forecasts. A flag late on a flood day may arrive after flooding began. The cases were reviewed from public sources by an assistant, not independently field-verified. Unknown outcomes are not confirmed false alarms. Sources: [project methodology](README.md), [recent audit JSON](data/backtest/results/daily/report.json), and [older diagnostic](data/backtest/historical/report.md). Audit JSON is generated locally from cached inputs.

---

## 7. Users and paying customers

**Residents use the service; organizations pay for a defined operational benefit.**

- **Residents:** free core rainfall information and observation submission; free basic alerts when a validated delivery service is available.
- **Property and facilities operators:** proposed site monitoring, incident records, and staff briefings.
- **Logistics and infrastructure operators:** proposed location watchlists and disruption summaries.
- **Insurers, researchers, and public agencies:** potential buyers of appropriately verified datasets and analysis.

**Speaker notes:** “Free for customers” needs a precise definition: free for residents and community users, with institutional customers paying. These are target segments, not signed partners. Initially, focus on one paying segment instead of building separate products for every buyer.

---

## 8. Revenue: organization-funded monitoring

**The first product to sell is a supported monitoring pilot.**

- A property or facilities operator pays for a defined group of locations and a fixed pilot period.
- Deliver a rainfall watchlist, reviewed incident log, and periodic evidence report.
- Charge for setup, monitoring service, and reporting; offer renewal after demonstrated usefulness.
- Keep the resident-facing core service free.

**Speaker notes:** This is the recommended first revenue experiment because it can produce value before we have a large, validated dataset. Start with a manual, clearly scoped service supported by the existing prototype. Do not sell guaranteed flood prevention, safe-route decisions, or proven early warnings. Validate willingness to pay through buyer interviews and a paid pilot before building a full enterprise dashboard.

---

## 9. Revenue: data products and licensing

**Sell the work of verifying and organizing local evidence.**

Potential products, once coverage and quality support them:

- A versioned flood-event register with documented timing precision, review decisions, and source provenance.
- Aggregate incident and monitoring summaries for defined areas and periods.
- Dataset subscriptions, licensed exports, and eventually an integration API.
- Commissioned research answering a specific buyer’s question.

**Speaker notes:** Selling data can be viable, but the current small, selected positive sample is not yet a commercial flood-risk dataset. Buyers would pay for reliable coverage, verification, usable structure, updates, and support—not simply copied public forecasts or scraped articles. Include monitored non-flood intervals and explicit missingness. Before licensing any product, confirm redistribution rights for each input. A source link or citation alone is not permission to resell an article or image. Do not market personal contact details, identifiable household reports, or movement histories as the product; design aggregate exports to reduce re-identification risk and establish permissions for contributed observations.

---

## 10. Other ways to fund free community access

**Use sponsorship and research funding to support coverage.**

- **Sponsored community coverage:** a business or foundation funds monitoring in a defined area for a fixed term.
- **Research and resilience contracts:** organizations commission data collection, retrospective studies, or evaluation reports.
- **Grants:** fund field verification, gauges, and public-interest access during development.
- **Later enterprise integrations:** organizations pay to bring established monitoring outputs into their own systems.

**Speaker notes:** Prioritize monitoring contracts first, then research work and sponsorship where there is a named budget holder. Grants can finance validation but are not proof of repeatable customer demand. Sponsors must not influence risk tiers or evidence review. Avoid making targeted advertising or emergency referral commissions the core business: neither directly validates the value of our monitoring service. Data licensing follows sufficient evidence, coverage, and rights clearance.

---

## 11. Commercial experiment and economics

**Prove one organization will pay and renew before projecting scale.**

Illustrative pricing experiment—not market evidence or a revenue forecast:

- Test a **$300 per month equivalent**, three-month monitoring pilot with a clearly limited location count and reporting scope.
- Five concurrent paying organizations at that price would produce **$1,500 monthly revenue** during their active contracts.
- Measure direct delivery cost: reviewer time, field observations, weather access, messaging, hosting, and customer support.
- Renew only if the buyer finds the service useful and the price covers delivery with an adequate margin.

**Speaker notes:** Dollar figures make this example easy to compare; actual contracts can be negotiated in naira. This is a pricing hypothesis, not a quotation or validated local benchmark. Do not annualize short pilots as contracted recurring revenue. Start with a single buyer; the five-buyer example is arithmetic, not traction. Track staff hours rather than treating founder labor as free. Keep one-off research fees, sponsorship, grants, and recurring subscriptions separate in financial reporting.

Commercial weather access is a real cost to investigate: Open-Meteo distinguishes its free non-commercial service from subscription access for commercial use, while its data licensing requires attribution. Confirm the relevant service and input terms before launch. [Open-Meteo pricing](https://open-meteo.com/en/pricing), [data licensing information](https://open-meteo.com/).

---

## 12. Positioning and defensibility

**Build local evidence and useful workflows that a generic weather feed does not provide.**

- Public weather inputs supply the rainfall signal.
- FloodGuard’s proposed added value is local verification, transparent evaluation, and maintained incident records.
- A growing record of both flood and monitored non-flood periods could improve evaluation and buyer usefulness.
- Long-term differentiation depends on evidence quality, trusted local partnerships, and repeat use.

**Speaker notes:** This advantage must be earned; the present dataset is small and not proprietary by default. Established flood-data businesses already serve institutional buyers—for example, Fathom describes flood-risk data products for insurers. That supports the existence of this category, not demand for our specific product or equivalence with their capabilities. Our proposed entry point is a narrow Lagos monitoring workflow, not an immediate replacement for established catastrophe models. [Fathom’s insurance offering](https://www.fathom.global/sector/insurance/).

---

## 13. Next milestones

**Develop the evidence and the business together.**

- **First 30 days:** interview property/facilities buyers, choose one paid-pilot use case, and agree a local observation protocol.
- **Days 31–60:** recruit independent reviewers and field observers; record exact locations, time ranges, and monitoring gaps.
- **Days 61–90:** assess buyer usefulness, service cost, and renewal intent; evaluate new observations without retuning against them.
- **After sufficient coverage:** decide whether performance and data quality justify wider release or a licensed dataset.

**Speaker notes:** These are proposed execution targets, not promises of statistically adequate validation within 90 days. Event occurrence and local verification may require longer, including a wet season. Preserve future evaluation cases, measure false alarms only where outcomes are known, and keep incomplete 2026 results and model cycles separate. Rainfall-source quality, drainage, tides, and river effects remain research priorities rather than implemented capabilities.

---

## 14. The ask

**Help us run a paid, independently reviewed Lagos pilot.**

We are seeking:

- One property or facilities organization willing to define and fund a monitoring pilot.
- Local observers and an independent flood or hydrology reviewer.
- A research or resilience sponsor to support evidence collection and community access.

**Closing line:** “We want residents to access useful flood information without a subscription. Organizations can fund that access by paying for dependable monitoring and verified local evidence.”

**Speaker notes:** The immediate ask is pilot participation and validation support. No funding round size, signed customer count, founder credentials, or market-size claim is supplied in this deck because those facts have not been established in the project. Add verified team information and a named contact before external circulation.

---

# Presenter appendix

## Revenue priorities

1. **Now:** sell a scoped monitoring and reporting pilot to one organization.
2. **Alongside it:** pursue commissioned research and community sponsorship with explicit deliverables.
3. **After sufficient evidence exists:** test licensed aggregate datasets and recurring updates with institutional buyers.
4. **After repeated integration demand:** build a paid enterprise API.

Keep residents’ core access free. Organizational fees should fund verification and delivery; monetization must not depend on selling identifiable residents’ data.

## Answers to likely questions

**“Does it predict floods accurately?”**

We have not established that. The sensitive rules flag the documented days in two separate historical experiments. Exact onset, representative non-flood monitoring, and independent prospective validation are still limiting factors.

**“Why would anyone pay if weather data is already available?”**

The hypothesis is that an operator will pay for a maintained local incident record, a monitored set of locations, clear uncertainty, and reporting that fits its workflow. Paid pilots must test that hypothesis.

**“Can you sell the data today?”**

We can discuss a scoped research service today. The current small historical sample does not support selling a comprehensive or validated flood-risk dataset. Dataset licensing needs stronger coverage, verification, appropriate permissions, and a demonstrated buyer need.

**“Why not just lower thresholds until every event is caught?”**

A system that flags every day also catches every flood day. The useful question is whether alerts precede flooding and remain manageable when outcomes are independently observed. That is the next evaluation task.

**“Is there already revenue or customer traction?”**

This deck establishes a working prototype and historical research, not paying customers, user growth, or booked revenue. Present commercial activity only once documented.

## Materials supporting the pitch

- [Project implementation and methodology](README.md)
- [Presentation walkthrough](PRESENTATION_WALKTHROUGH.md)
- [Older-event evidence and rainfall diagnostic](data/backtest/historical/report.md)
- [Recent daily audit JSON, generated locally](data/backtest/results/daily/report.json)
- [Older diagnostic JSON, generated locally](data/backtest/historical/results/report.json)

The operational recommendations and proposed prices in this document are business hypotheses. External sources support only the claims placed next to their links. Review figures and commercial terms again before presenting at a later date.
