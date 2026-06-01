# Roadmap

Forward-looking ideas for the South Florida Economic Report. Near-term items are committed work; longer-term items are under consideration.

## Near-term (post-Athens)

- **Monthly data audit.** Set up a recurring accuracy check comparing the cached QCEW/FRED/IRS data against the latest releases, with a dated report dropped into `audits/`.
- **Methodology page.** Add a public-facing methodology page documenting data sources, transformations (STL trend, 2Q linear projection, QoQ establishment churn), filters (own_code, agglvl_code, "Unclassified" exclusion), and update cadence.

## Longer-term ideas

- **Subscription / new-data notifications.** Let users subscribe (email or RSS) to be notified when fresh data lands. Triggered by the weekly GitHub Action after a successful rebuild.
- **Public data release schedule.** Alternative to subscriptions — publish a forward calendar of expected release dates, modeled on the [BLS QCEW release calendar](https://www.bls.gov/cew/release-calendar.htm).
- **Other QCEW features worth replicating.** Periodically scan [bls.gov/cew](https://www.bls.gov/cew/) for analyses, charts, or data cuts that could be adapted for the South Florida region.
