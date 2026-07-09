# EA Slide Builder Web Version Guide

This guide walks a CSM or account team through the GitHub Pages web version of
EA Slide Builder. Use it to turn EPD contract/license data and Telemetry Tableau
usage exports into a one-slide PowerPoint summary.

Web app:

<https://ryleyp.github.io/CSM_OneSliders/>

## What You Need Before Starting

Collect the inputs from two approved sources.

| Source | What to collect | Where it goes in the web app |
| --- | --- | --- |
| EPD | Exhibit A contract details | Contract Review Blanks -> Exhibit A blanks |
| EPD | Support level, support scope, FLEX credits, SystemLink Support (SNOW) | Contract Review Blanks -> Support & credits blanks |
| EPD | Finite quantity NI software license table | Finite license blanks |
| EPD | Unlimited quantity NI software bundle table | Unlimited bundle blanks |
| Telemetry Tableau | Machine usage trend table | Pasted Tables -> Machine Count |
| Telemetry Tableau | Site/location machine counts | Pasted Tables -> Locations |
| Telemetry Tableau | Product/version usage table | Pasted Tables -> Usage Versions |

> [!IMPORTANT]
> The web version is a static GitHub Pages app. The page code is public, but the
> data you type or paste is processed in your browser. It has no backend, no
> telemetry, no third-party scripts, and no customer-data upload.

> [!CAUTION]
> Only use the web version on company-approved devices and trusted networks.
> Do not paste contract data into chat tools, public issue trackers, or any
> non-approved site while preparing the slide.

## Recommended Input Flow

Follow this order. It matches how the web page is laid out and reduces rework.

### 1. Open the Web App

1. Go to <https://ryleyp.github.io/CSM_OneSliders/>.
2. Confirm the top of the page says **EA Slide Builder Lite**.
3. Review the **Security Mode** box before entering customer data.

> [!NOTE]
> If the page has been open for a while, refresh it before building a deck. This
> helps make sure you are using the latest PowerPoint generator.

### 2. Enter EPD Contract Details

Use the EPD Exhibit A section as the source of truth.

In **Contract Review Blanks -> Exhibit A blanks**, enter:

1. **EA/EP Service ID**: for example, `EA-15647`.
2. **Customer / Company**: customer name as it should appear on the slide.
3. **Start / Effective Date**: from the EPD.
4. **EP Term**: for example, `3 years`.
5. **EA End Date**: enter directly from the EPD or click **Recompute End Date & Phase** after entering start date and term.
6. **Phase**: enter manually or let the app recompute it.
7. **Contract Scope**: enter the scope language you want summarized.
8. **Debug licenses**: choose `Yes` or `No`.

Then in **Support & credits blanks**, enter:

1. **Support tier**: for example, `Enterprise Support`.
2. **Support scope**: for example, `All Users`.
3. **FLEX credits purchased**: from the EPD.
4. **Credits used**: current usage value if known.
5. **SystemLink support (SNOW)**: check this if the contract includes SystemLink Support (SNOW).

> [!IMPORTANT]
> Treat EPD values as contract data. Do not export profile JSON files or
> downloaded PPTX files to public folders, public GitHub repos, or shared
> personal cloud locations.

### 3. Enter EPD Finite License Rows

Use the finite quantity NI software license table from the EPD.

In **Finite license blanks**:

1. Click **Add Row** for each contract row.
2. Enter the license **count**.
3. Choose the license type from the dropdown:
   - `Concurrent`
   - `Named-User or Computer-Based`
4. Enter the software/license name.
5. Remove any extra blank rows before generating the preview.

Example:

| Count | License type | License name |
| --- | --- | --- |
| 142 | Named-User or Computer-Based | DIAdem Professional with DAC |
| 53 | Named-User or Computer-Based | Circuit Design Suite |
| 23 | Concurrent | SystemLink Server Test Operations Suite Server |

### 4. Enter EPD Unlimited Bundle Rows

Use the unlimited quantity NI software license table from the EPD.

In **Unlimited bundle blanks**:

1. Click **Add Row** for each bundle title.
2. Enter one bundle name per row.
3. Include debug bundle information if the EPD lists it separately.

Example:

| Bundle name |
| --- |
| EA Platform Bundle |
| EA Platform Bundle. Debug |

### 5. Paste Telemetry Tableau Machine Count Data

Use Telemetry Tableau for the usage trend.

In **Pasted Tables -> Machine Count**:

1. In Tableau, select the machine count table.
2. Copy the table so it stays tab-separated.
3. Paste it into **Machine Count**.

Accepted shapes include:

```text
Year    Quarter    Month    Machine Type    Distinct count of machine_id
2025    Q1         Jan      Existing        848
```

or:

```text
Period    New    Existing
Q1 2025   12     836
```

The slide uses this table for:

1. Software usage trend chart.
2. Peak machines.
3. Min machines.
4. Average quarterly increase.

### 6. Paste Telemetry Tableau Location Data

Use Telemetry Tableau for top site locations.

In **Pasted Tables -> Locations**:

1. Copy the location/site table from Tableau.
2. Paste it into **Locations**.
3. Leave **Avoid product double-counting** checked unless you intentionally want to sum every product row.

Preferred Tableau geo export shape:

```text
ip_country    ip_region    ip_city    Measure Names    product_name    Measure Values
United States Texas        Austin     Distinct count of machine_id LabVIEW 50
```

Manual/simple shape also works:

```text
Country       State    City      Count
United States TX       Austin    50
Singapore             Singapore 12
```

The slide displays the top five sites as:

```text
COUNTRY | STATE | CITY | COUNT
```

> [!NOTE]
> If the location table is split by product, keeping **Avoid product
> double-counting** checked prevents the same machines from being counted
> repeatedly across product rows.

### 7. Paste Telemetry Tableau Version Data

Use Telemetry Tableau for top software and version usage.

In **Pasted Tables -> Usage Versions**:

1. Copy the Tableau version table.
2. Paste it into **Usage Versions**.

Expected shape:

```text
product_name    product_version    Distinct count of machine_id
LabVIEW         2020               767
MAX             20.0.0             479
```

The **Version Usage** section tells the story as:

1. Top software product by total usage.
2. Top version for that product.
3. Percent of that product's total usage on the top version.

### 8. Generate and Review the Preview

1. Click **Generate Preview**.
2. Review the slide preview on the page.
3. Review warnings above the preview.
4. Check that contract details, locations, version usage, license rows, support, and credits look right.
5. Adjust input fields and click **Generate Preview** again as needed.

Review checklist:

| Area | Check |
| --- | --- |
| Header | Service ID and customer name are correct |
| Contract Details | End date, term, scope, and phase are correct |
| Bundle Information | All contract bundles are included |
| NI SW Licenses | All finite contract software rows fit |
| Top Site Locations | Country, state, city, and count look correct |
| Version Usage | Product total, top version, and percent tell the right story |
| Training Credit Usage | Purchased, used, and utilized values are correct |
| Technical Support | Support tier, scope, and SNOW status are correct |

### 9. Download the PowerPoint

1. Leave **Include CSM Insights slide** checked if you want the insights slide.
2. Click **Download PPTX**.
3. Open the downloaded `.pptx` in PowerPoint.
4. Save the final version using your team's naming convention.

> [!CAUTION]
> Generated PPTX files may contain contract and telemetry-derived customer
> information. Share them only through approved internal channels.

### 10. Optional: Save a Profile for Next Time

Profiles are useful for quarterly refreshes.

1. Enter a **Profile name**.
2. Click **Export Profile JSON**.
3. Store the JSON file in an approved internal location.
4. Next quarter, use **Import Profile JSON**, refresh the Tableau tables, and regenerate the deck.

> [!IMPORTANT]
> Profile JSON files contain the values entered into the app. Treat them like
> customer data. Do not commit them to GitHub.

### 11. Optional: Build a Batch Deck

Use batch mode when you have multiple saved profile JSON files.

1. Export one profile JSON per account.
2. Under **Account Profiles & Batch Decks**, choose the profile JSON files.
3. Click **Download Batch PPTX**.
4. Review every slide before sharing.

## Security Precautions

Use this checklist every time.

| Precaution | Why it matters |
| --- | --- |
| Verify the URL is `https://ryleyp.github.io/CSM_OneSliders/` | Avoid lookalike or unapproved pages |
| Use approved company devices | Browser memory and downloads may contain customer data |
| Use approved networks | Reduce risk when accessing internal source data |
| Do not upload screenshots or source documents | The web version is designed for typed blanks and pasted tables |
| Do not commit profiles or PPTX files | They can contain contract and telemetry-derived customer data |
| Clear the page when finished | Refreshing or clicking **Clear Data** removes entered values from the browser session |
| Store outputs internally | Use approved customer-data handling channels |

## Troubleshooting

### PowerPoint says it cannot read the file

1. Refresh the web app.
2. Confirm you are using the live page, not an old downloaded HTML file.
3. Generate and download a new PPTX.
4. Delete the older failed download.

Older PPTX downloads cannot be repaired automatically after the fact; generate a fresh file from the current page.

### The preview is empty

1. Make sure **Machine Count** has data.
2. Click **Generate Preview**.
3. Review any warnings above the preview.

### Locations look wrong

1. Confirm the pasted table includes country, state/region, city, and count columns.
2. Keep **Avoid product double-counting** checked for product-split Tableau exports.
3. Regenerate the preview.

### Version usage looks wrong

1. Confirm the Tableau paste includes product name, product version, and distinct machine count.
2. Remove subtotal or grand total rows before pasting if Tableau includes them.
3. Regenerate the preview.

### Contract details are missing

1. Confirm the EPD fields were entered in **Contract Review Blanks**.
2. Click **Recompute End Date & Phase** if start date or term changed.
3. Regenerate the preview.
