# Data Cleaning Report — Support Tickets (synthetic data)

## 1. Raw data inspection
- Rows: **114**, columns: **10**
- Exact duplicate rows: **3**
- Repeated `ticket_id` values (including exact duplicates): **4**

Empty values per column (raw):

| Column | Empty values |
|---|---:|
| created_at | 1 |
| country | 1 |
| category | 1 |
| resolution_hours | 1 |
| satisfaction_score | 2 |

## 2. Cleaning result
- Input rows: **114**
- Exact duplicates removed: **3**
- Rejected rows (sent to `rejected_rows.csv` for review): **12**
- Clean rows: **99**

Rejection reasons (a row can have more than one):

| Reason | Rows |
|---|---:|
| conflicting_ticket_id | 2 |
| invalid_category | 1 |
| invalid_created_at | 2 |
| invalid_language | 1 |
| missing_category | 1 |
| missing_created_at | 1 |
| negative_resolution_hours | 1 |
| non_numeric_resolution_hours | 1 |
| non_numeric_satisfaction_score | 1 |
| satisfaction_score_out_of_range | 1 |

## 3. Clean data overview

| Language | Tickets |
|---|---:|
| en | 36 |
| es | 33 |
| fr | 30 |

| Category | Tickets |
|---|---:|
| account | 28 |
| billing | 26 |
| delivery | 24 |
| technical | 21 |

Missing optional values kept as empty:

| Column | Empty values |
|---|---:|
| country | 1 |
| resolution_hours | 1 |
| satisfaction_score | 2 |

| Category | Mean resolution hours |
|---|---:|
| account | 33.8 |
| billing | 36.3 |
| delivery | 35.6 |
| technical | 43.6 |

| Channel | Mean satisfaction (1–5) |
|---|---:|
| chat | 2.53 |
| email | 3.25 |
| phone | 3.24 |

_The data is synthetic. These figures describe the sample, not any real business._
