# Reproducibility check (full, seed 20261022)

Two runs with the same seed: 32 of 32 files identical.

32 of 32 files also match the checksums saved in data/full/manifest.json.

A third run with seed 20261023 changed 21 files, which shows the seed controls the data. Files that do not change are the fixed master tables.

Checksums are SHA-256, shortened to 16 characters here.

| File | Rows | Run 1 checksum | Run 2 checksum | Same? |
|---|---|---|---|---|
| csv/adjustment_proposal.csv | 435 | d44691d8c37afdb3 | d44691d8c37afdb3 | YES |
| csv/comparable_group.csv | 523 | 8902d50385533f54 | 8902d50385533f54 | YES |
| csv/comparable_group_member.csv | 6657 | e2a6758e928734be | e2a6758e928734be | YES |
| csv/compensation_band.csv | 4800 | c9af9c638bed2227 | c9af9c638bed2227 | YES |
| csv/employee.csv | 5000 | f1876609fd2b7863 | f1876609fd2b7863 | YES |
| csv/fx_rate.csv | 15 | 9b4bb7b870c5360d | 9b4bb7b870c5360d | YES |
| csv/level.csv | 5 | 178f31e56479b515 | 178f31e56479b515 | YES |
| csv/location.csv | 8 | 6344d11dbecca128 | 6344d11dbecca128 | YES |
| csv/performance_evidence.csv | 11791 | e1f68ee95f824ead | e1f68ee95f824ead | YES |
| csv/promotion.csv | 1225 | 1bae0a2bea300bca | 1bae0a2bea300bca | YES |
| csv/proposal_event.csv | 1704 | 1616000830ea34d5 | 1616000830ea34d5 | YES |
| csv/role.csv | 40 | c2bd3d86c7f11750 | c2bd3d86c7f11750 | YES |
| csv/salary_record.csv | 18617 | 44a232c138b91509 | 44a232c138b91509 | YES |
| csv/tenure.csv | 5000 | 6777c24175683b4c | 6777c24175683b4c | YES |
| ground_truth/ground_truth.csv | 259 | 4d7ddcf5d0342350 | 4d7ddcf5d0342350 | YES |
| ground_truth/ground_truth.json |  | b81a81eeaf713ff1 | b81a81eeaf713ff1 | YES |
| json/adjustment_proposal.json |  | 98af996819a049e4 | 98af996819a049e4 | YES |
| json/comparable_group.json |  | d879bb8e78d7b2fc | d879bb8e78d7b2fc | YES |
| json/comparable_group_member.json |  | 2b4e78318710673b | 2b4e78318710673b | YES |
| json/compensation_band.json |  | 4069924e3b3441e1 | 4069924e3b3441e1 | YES |
| json/employee.json |  | 5f175f619363dafa | 5f175f619363dafa | YES |
| json/fx_rate.json |  | f736021a4e79b6a1 | f736021a4e79b6a1 | YES |
| json/level.json |  | 55437796b2a26f87 | 55437796b2a26f87 | YES |
| json/location.json |  | 687cf7315285c2fc | 687cf7315285c2fc | YES |
| json/performance_evidence.json |  | 5fa83f3e53d9675c | 5fa83f3e53d9675c | YES |
| json/promotion.json |  | cec982d2d1e2df98 | cec982d2d1e2df98 | YES |
| json/proposal_event.json |  | c0a8b1ddbc89b0e9 | c0a8b1ddbc89b0e9 | YES |
| json/role.json |  | 63aecee2b79aaa1e | 63aecee2b79aaa1e | YES |
| json/salary_record.json |  | 928695f473134f3e | 928695f473134f3e | YES |
| json/tenure.json |  | 75f5b903390d84b6 | 75f5b903390d84b6 | YES |
| sql/schema.sql |  | ad5ace1d2f27bf52 | ad5ace1d2f27bf52 | YES |
| sql/seed.sql |  | 18232dd4ff9a2ed2 | 18232dd4ff9a2ed2 | YES |
