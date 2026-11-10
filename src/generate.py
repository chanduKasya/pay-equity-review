"""
generate.py - the single command that builds the whole dataset.

Run from the project folder:
    python3 src/generate.py --scale starter
    python3 src/generate.py --scale full --seed 20261022
"""

import argparse
import os

import config
import io_utils
import master_data


def main():
    # Read the options typed on the command line.
    parser = argparse.ArgumentParser(description="Generate the synthetic pay-equity dataset.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    parser.add_argument("--out", default="data")
    args = parser.parse_args()

    out_folder = os.path.join(args.out, args.scale)
    print("Scale:", args.scale, "| Seed:", args.seed, "| Output folder:", out_folder)

    # ---- Stage 1: master tables (parents first) ----
    roles = master_data.build_roles()
    levels = master_data.build_levels()
    locations = master_data.build_locations()
    fx_rates = master_data.build_fx_rates()
    bands = master_data.build_bands(roles, levels, locations, fx_rates)

    io_utils.write_csv(roles, out_folder, "role.csv",
                       ["role_id", "role_name", "job_family", "base_mid_usd"])
    io_utils.write_csv(levels, out_folder, "level.csv",
                       ["level_id", "level_name", "level_rank", "mid_multiplier"])
    io_utils.write_csv(locations, out_folder, "location.csv",
                       ["location_id", "city", "country", "currency_code", "geo_factor"])
    io_utils.write_csv(fx_rates, out_folder, "fx_rate.csv",
                       ["currency_code", "rate_year", "units_per_usd"])
    io_utils.write_csv(bands, out_folder, "compensation_band.csv",
                       ["band_id", "role_id", "level_id", "location_id", "band_year",
                        "currency_code", "band_min", "band_mid", "band_max",
                        "effective_from", "effective_to"])

    print("role:", len(roles))
    print("level:", len(levels))
    print("location:", len(locations))
    print("fx_rate:", len(fx_rates))
    print("compensation_band:", len(bands))
    print("role/level combinations:", len(roles) * len(levels))


if __name__ == "__main__":
    main()
