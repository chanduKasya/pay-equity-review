# Reproducibility check (starter, seed 20261022)

Two runs with the same seed: 34 of 34 files identical.

34 of 34 files also match the checksums saved in data/starter/manifest.json.

A third run with seed 20261023 changed 23 files, which shows the seed controls the data. Files that do not change are the fixed master tables.

Checksums are SHA-256, shortened to 16 characters here.

| File | Rows | Run 1 checksum | Run 2 checksum | Same? |
|---|---|---|---|---|
| csv/adjustment_proposal.csv | 40 | c0c88eeb2840cd8e | c0c88eeb2840cd8e | YES |
| csv/comparable_group.csv | 65 | 2e2d0ea7fd45100a | 2e2d0ea7fd45100a | YES |
| csv/comparable_group_member.csv | 615 | 6b02f2053585d29d | 6b02f2053585d29d | YES |
| csv/compensation_band.csv | 4800 | c9af9c638bed2227 | c9af9c638bed2227 | YES |
| csv/demographics.csv | 500 | 1c9412cf6e6f9649 | 1c9412cf6e6f9649 | YES |
| csv/employee.csv | 500 | 09ca203b7add9ebf | 09ca203b7add9ebf | YES |
| csv/fx_rate.csv | 15 | 9b4bb7b870c5360d | 9b4bb7b870c5360d | YES |
| csv/level.csv | 5 | 178f31e56479b515 | 178f31e56479b515 | YES |
| csv/location.csv | 8 | 6344d11dbecca128 | 6344d11dbecca128 | YES |
| csv/performance_evidence.csv | 1160 | d9a5bf71412c73fc | d9a5bf71412c73fc | YES |
| csv/promotion.csv | 97 | d01d302ba03f284c | d01d302ba03f284c | YES |
| csv/proposal_event.csv | 155 | 125c2c3b7bf08fcc | 125c2c3b7bf08fcc | YES |
| csv/role.csv | 40 | c2bd3d86c7f11750 | c2bd3d86c7f11750 | YES |
| csv/salary_record.csv | 1823 | 74f8edcb81c977a3 | 74f8edcb81c977a3 | YES |
| csv/tenure.csv | 500 | 40fce231bdd509a8 | 40fce231bdd509a8 | YES |
| ground_truth/ground_truth.csv | 29 | 51cd1a14c2c26a8a | 51cd1a14c2c26a8a | YES |
| ground_truth/ground_truth.json |  | a3259fa803900efe | a3259fa803900efe | YES |
| json/adjustment_proposal.json |  | 0689b347678fae0d | 0689b347678fae0d | YES |
| json/comparable_group.json |  | c88a2405ea5a5de7 | c88a2405ea5a5de7 | YES |
| json/comparable_group_member.json |  | f99aa88c84083cfc | f99aa88c84083cfc | YES |
| json/compensation_band.json |  | 4069924e3b3441e1 | 4069924e3b3441e1 | YES |
| json/demographics.json |  | 26617f91854dcdcf | 26617f91854dcdcf | YES |
| json/employee.json |  | 0938ec4b8c66922e | 0938ec4b8c66922e | YES |
| json/fx_rate.json |  | f736021a4e79b6a1 | f736021a4e79b6a1 | YES |
| json/level.json |  | 55437796b2a26f87 | 55437796b2a26f87 | YES |
| json/location.json |  | 687cf7315285c2fc | 687cf7315285c2fc | YES |
| json/performance_evidence.json |  | f3c755c84b66fada | f3c755c84b66fada | YES |
| json/promotion.json |  | f9c3025905031e15 | f9c3025905031e15 | YES |
| json/proposal_event.json |  | 52dd2e787ee3722b | 52dd2e787ee3722b | YES |
| json/role.json |  | 63aecee2b79aaa1e | 63aecee2b79aaa1e | YES |
| json/salary_record.json |  | 0b0f6b868fba6eeb | 0b0f6b868fba6eeb | YES |
| json/tenure.json |  | 7824e923f1dc4901 | 7824e923f1dc4901 | YES |
| sql/schema.sql |  | 97870a86f46879a1 | 97870a86f46879a1 | YES |
| sql/seed.sql |  | 167b03cc54908233 | 167b03cc54908233 | YES |
