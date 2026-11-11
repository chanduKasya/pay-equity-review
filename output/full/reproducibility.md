# Reproducibility check (full, seed 20261022)

Two runs with the same seed: 34 of 34 files identical.

34 of 34 files also match the checksums saved in data/full/manifest.json.

A third run with seed 20261023 changed 23 files, which shows the seed controls the data. Files that do not change are the fixed master tables.

Checksums are SHA-256, shortened to 16 characters here.

| File | Rows | Run 1 checksum | Run 2 checksum | Same? |
|---|---|---|---|---|
| csv/adjustment_proposal.csv | 577 | f0b158138c80da0b | f0b158138c80da0b | YES |
| csv/comparable_group.csv | 523 | d465329f51e8233e | d465329f51e8233e | YES |
| csv/comparable_group_member.csv | 6651 | ae34a653df265d01 | ae34a653df265d01 | YES |
| csv/compensation_band.csv | 4800 | c9af9c638bed2227 | c9af9c638bed2227 | YES |
| csv/demographics.csv | 5000 | af0486d6c6962985 | af0486d6c6962985 | YES |
| csv/employee.csv | 5000 | f1876609fd2b7863 | f1876609fd2b7863 | YES |
| csv/fx_rate.csv | 15 | 9b4bb7b870c5360d | 9b4bb7b870c5360d | YES |
| csv/level.csv | 5 | 178f31e56479b515 | 178f31e56479b515 | YES |
| csv/location.csv | 8 | 6344d11dbecca128 | 6344d11dbecca128 | YES |
| csv/performance_evidence.csv | 11791 | e1f68ee95f824ead | e1f68ee95f824ead | YES |
| csv/promotion.csv | 1225 | 1bae0a2bea300bca | 1bae0a2bea300bca | YES |
| csv/proposal_event.csv | 2236 | 4c44f426c36a059d | 4c44f426c36a059d | YES |
| csv/role.csv | 40 | c2bd3d86c7f11750 | c2bd3d86c7f11750 | YES |
| csv/salary_record.csv | 18690 | a0717e6e921486c6 | a0717e6e921486c6 | YES |
| csv/tenure.csv | 5000 | 6777c24175683b4c | 6777c24175683b4c | YES |
| ground_truth/ground_truth.csv | 258 | b7c1c608d565b2ca | b7c1c608d565b2ca | YES |
| ground_truth/ground_truth.json |  | 5f63fafbcc1c7799 | 5f63fafbcc1c7799 | YES |
| json/adjustment_proposal.json |  | 699d65a8138c5a7d | 699d65a8138c5a7d | YES |
| json/comparable_group.json |  | 92f8d3a0e732ac0e | 92f8d3a0e732ac0e | YES |
| json/comparable_group_member.json |  | e2ac28c61585b59b | e2ac28c61585b59b | YES |
| json/compensation_band.json |  | 4069924e3b3441e1 | 4069924e3b3441e1 | YES |
| json/demographics.json |  | 5377c9f6a9ce05e5 | 5377c9f6a9ce05e5 | YES |
| json/employee.json |  | 5f175f619363dafa | 5f175f619363dafa | YES |
| json/fx_rate.json |  | f736021a4e79b6a1 | f736021a4e79b6a1 | YES |
| json/level.json |  | 55437796b2a26f87 | 55437796b2a26f87 | YES |
| json/location.json |  | 687cf7315285c2fc | 687cf7315285c2fc | YES |
| json/performance_evidence.json |  | 5fa83f3e53d9675c | 5fa83f3e53d9675c | YES |
| json/promotion.json |  | cec982d2d1e2df98 | cec982d2d1e2df98 | YES |
| json/proposal_event.json |  | 8e502d40af373c90 | 8e502d40af373c90 | YES |
| json/role.json |  | 63aecee2b79aaa1e | 63aecee2b79aaa1e | YES |
| json/salary_record.json |  | 8da12b8cad9561f9 | 8da12b8cad9561f9 | YES |
| json/tenure.json |  | 75f5b903390d84b6 | 75f5b903390d84b6 | YES |
| sql/schema.sql |  | 97870a86f46879a1 | 97870a86f46879a1 | YES |
| sql/seed.sql |  | 44084afac1b3341a | 44084afac1b3341a | YES |
