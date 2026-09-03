# Hand-supplied Berkeley Earth series

Anything dropped here is used **instead of** the remote archive, per country.

## Why this exists

Berkeley Earth froze its public per-country text files at December 2020. Every
country on the site therefore stops at 2020, while the global card reaches 2024
because it is pulled from a different, still-maintained file. Current country
data lives on Berkeley Earth's Synthesis platform, which needs a free login and
so cannot be fetched unattended by the daily workflow.

## How to update a country

1. Sign in at <https://berkeleyearth.org> and export the country's monthly
   temperature series.
2. Save it here as `<slug>.txt` or `<slug>.csv`, where `<slug>` matches the
   `slug` in `_data/cvf_members.yml` (`ghana.csv`, `bangladesh.csv`, ...).
3. Commit it. The next run picks it up, logs `using the local export`, and
   records `"local": true` for that country in `_data/warming_stripes.json`.

Delete the file to go back to the remote archive.

## Accepted formats

Either the Berkeley Earth `-TAVG-Trend.txt` layout as downloaded, or a CSV with
a header row in one of these two shapes:

    year,month,anomaly          # monthly, a year needs all twelve months
    year,anomaly                # already annual, taken as given

Extra columns are ignored, so an export can keep its uncertainty column. The
value column may be named `anomaly`, `temperature_C`, `temperature`, `tavg` or
`value`. Anomalies are re-centred on 1971-2000 by the script, so it does not
matter which baseline the export uses.

Nothing is ever synthesised. A country that fails to parse is left out of the
output rather than estimated.
