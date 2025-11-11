import random
from datetime import timedelta
from typing import Dict, Tuple, List

import numpy as np
import pandas as pd

from .config import (
    n_employees,
    start_date,
    end_date,
    random_seed,
    synth_transactions_csv,
)
from .rules import (
    whitelist_merchants,
    non_whitelist_merchants,
    is_whitelisted_merchant,
    label_misuse,
)

rng = np.random.default_rng(random_seed)
random.seed(random_seed)

countries = ["de", "fr", "nl", "es", "it", "uk"]
city_by_country: Dict[str, Tuple[str, ...]] = {
    "de": ("berlin", "munich", "frankfurt"),
    "fr": ("paris", "lyon"),
    "nl": ("amsterdam", "rotterdam"),
    "es": ("madrid", "barcelona"),
    "it": ("milan", "rome"),
    "uk": ("london", "manchester"),
}

# desired total rows
target_rows = 2_000_000


def random_day():
    days = int((end_date - start_date).days)
    return start_date + timedelta(days=int(rng.integers(0, days + 1)))


def generate_base_transactions() -> pd.DataFrame:
    employees = [f"e{idx:03d}" for idx in range(1, n_employees + 1)]

    # assign home base + gender
    emp_home: Dict[str, Tuple[str, str]] = {}
    emp_gender: Dict[str, str] = {}

    for emp in employees:
        c = random.choice(countries)
        city = random.choice(city_by_country[c])
        gender = "m" if random.random() < 0.5 else "f"
        emp_home[emp] = (c, city)
        emp_gender[emp] = gender

    rows: List[dict] = []
    tx_id = 1

    for emp in employees:
        home_country, home_city = emp_home[emp]
        gender = emp_gender[emp]

        # approved business trips
        for month in (1, 2, 3):
            n_trips = int(rng.integers(0, 3))  # 0-2 trips per month
            for _ in range(n_trips):
                start_day = int(rng.integers(3, 25))
                trip_len = int(rng.integers(2, 6))
                trip_start = start_date.replace(
                    month=month,
                    day=start_day,
                    hour=9, minute=0, second=0, microsecond=0,
                )

                # flight
                flight_candidates = [m for m in whitelist_merchants if m.category == "flight"]
                if not flight_candidates:
                    raise ValueError("no whitelisted flight merchants configured")
                flight_merch = random.choice(flight_candidates)
                amount = float(abs(rng.normal(250, 80)))
                rows.append({
                    "transaction_id": tx_id,
                    "employee_id": emp,
                    "gender": gender,
                    "tx_datetime": trip_start - timedelta(hours=2),
                    "amount": amount,
                    "merchant_name": flight_merch.name,
                    "mcc_category": flight_merch.category,
                    "has_business_trip": 1,
                    "country": home_country,
                    "city": home_city,
                })
                tx_id += 1

                # hotel
                hotel_candidates = [m for m in whitelist_merchants if m.category == "hotel"]
                if not hotel_candidates:
                    raise ValueError("no whitelisted hotel merchants configured")
                hotel_merch = random.choice(hotel_candidates)

                for night in range(trip_len):
                    dt = trip_start + timedelta(days=night, hours=20)
                    c = random.choice(countries)
                    city = random.choice(city_by_country[c])
                    amount = float(abs(rng.normal(120, 30)))
                    rows.append({
                        "transaction_id": tx_id,
                        "employee_id": emp,
                        "gender": gender,
                        "tx_datetime": dt,
                        "amount": amount,
                        "merchant_name": hotel_merch.name,
                        "mcc_category": hotel_merch.category,
                        "has_business_trip": 1,
                        "country": c,
                        "city": city,
                    })
                    tx_id += 1

                # meals during trip
                for _ in range(int(rng.integers(2, 6))):
                    dt = trip_start + timedelta(
                        days=int(rng.integers(0, trip_len)),
                        hours=int(rng.integers(11, 21)),
                        minutes=int(rng.integers(0, 60)),
                    )
                    amount = float(abs(rng.normal(25, 10)))
                    rows.append({
                        "transaction_id": tx_id,
                        "employee_id": emp,
                        "gender": gender,
                        "tx_datetime": dt,
                        "amount": amount,
                        "merchant_name": "workcanteen",
                        "mcc_category": "restaurant",
                        "has_business_trip": 1,
                        "country": home_country,
                        "city": home_city,
                    })
                    tx_id += 1

        # legit local expenses
        n_local = int(rng.integers(20, 60))
        for _ in range(n_local):
            d = random_day()
            dt = d.replace(
                hour=int(rng.integers(8, 20)),
                minute=int(rng.integers(0, 60)),
                second=0,
                microsecond=0,
            )
            legit_merchants = [
                m for m in whitelist_merchants
                if m.name in ("workcanteen", "officesuppliesco", "businesstaxi")
            ]
            if not legit_merchants:
                raise ValueError("expected basic legit merchants in whitelist")
            merch = random.choice(legit_merchants)
            amount = float(abs(rng.normal(30, 15)))
            rows.append({
                "transaction_id": tx_id,
                "employee_id": emp,
                "gender": gender,
                "tx_datetime": dt,
                "amount": amount,
                "merchant_name": merch.name,
                "mcc_category": merch.category,
                "has_business_trip": 0,
                "country": home_country,
                "city": home_city,
            })
            tx_id += 1

        # suspicious / misuse-like
        n_misuse = int(rng.integers(10, 30))
        for _ in range(n_misuse):
            d = random_day()

            # late or night more likely
            if rng.random() < 0.7:
                hour = random.choice([21, 22, 23, 0, 1, 2, 3, 4, 5])
            else:
                hour = int(rng.integers(10, 22))

            dt = d.replace(
                hour=hour,
                minute=int(rng.integers(0, 60)),
                second=0,
                microsecond=0,
            )

            if not non_whitelist_merchants:
                raise ValueError("no non-whitelist merchants configured")
            merch = random.choice(non_whitelist_merchants)
            c = random.choice(countries)
            city = random.choice(city_by_country[c])

            # mix: very small amounts sometimes, otherwise normal suspicious
            if rng.random() < 0.15:
                amount = round(float(abs(rng.normal(1.5, 0.7))), 2)
                if amount <= 0:
                    amount = 1.0
            else:
                amount = float(abs(rng.normal(80, 40)))

            rows.append({
                "transaction_id": tx_id,
                "employee_id": emp,
                "gender": gender,
                "tx_datetime": dt,
                "amount": amount,
                "merchant_name": merch.name,
                "mcc_category": merch.category,
                "has_business_trip": 0,
                "country": c,
                "city": city,
            })
            tx_id += 1

    df = pd.DataFrame(rows)

    # clean basics
    df["tx_datetime"] = pd.to_datetime(df["tx_datetime"])
    df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)
    df = df[df["amount"] > 0].reset_index(drop=True)

    # time features (hour/weekday/is_weekend)
    df["hour"] = df["tx_datetime"].dt.hour
    df["weekday"] = df["tx_datetime"].dt.weekday
    df["is_weekend"] = (df["weekday"] >= 5).astype(int)

    # normalize text
    for col in ("merchant_name", "mcc_category", "country", "city", "gender"):
        df[col] = df[col].astype(str).str.lower()

    # whitelist flag
    df["is_whitelisted_merchant"] = df["merchant_name"].apply(is_whitelisted_merchant)

    # label misuse using rules (includes small amount, late hours, non-whitelist, travel)
    df["is_misuse"] = df.apply(
        lambda r: label_misuse(
            merchant_name=r["merchant_name"],
            mcc_category=r["mcc_category"],
            is_whitelisted_merchant=int(r["is_whitelisted_merchant"]),
            has_business_trip=int(r["has_business_trip"]),
            hour=int(r["hour"]),
            amount=float(r["amount"]),
        ),
        axis=1,
    )

    return df


def inflate_to_target(df: pd.DataFrame, target: int) -> pd.DataFrame:
    """repeat and shuffle base df to reach target rows."""
    n = len(df)
    if n >= target:
        df = df.sample(target, random_state=random_seed).reset_index(drop=True)
        df["transaction_id"] = np.arange(1, target + 1)
        return df

    reps = int(np.ceil(target / n))
    df_big = pd.concat([df] * reps, ignore_index=True)
    df_big = df_big.sample(target, random_state=random_seed).reset_index(drop=True)
    df_big["transaction_id"] = np.arange(1, target + 1)
    return df_big


def main():
    base_df = generate_base_transactions()
    big_df = inflate_to_target(base_df, target_rows)

    synth_transactions_csv.parent.mkdir(parents=True, exist_ok=True)
    big_df.to_csv(synth_transactions_csv, index=False)

    misuse_rate = big_df["is_misuse"].mean()
    print(
        f"saved synthetic data to {synth_transactions_csv} "
        f"shape={big_df.shape}, misuse_rate={misuse_rate:.3f}"
    )


if __name__ == "__main__":
    main()
