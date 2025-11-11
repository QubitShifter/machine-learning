from dataclasses import dataclass
from typing import List

# thresholds (toy, for learning)
small_suspicious_amount = 3.0        # very small -> suspicious
late_hour_start = 21                 # 21:00 and later
early_hour_end = 6                   # before 06:00

# categories treated as "personal-like" if done late
personal_night_cats = {
    "shopping",
    "entertainment",
    "hotel",
    "grocery",
    "electronics",
}

@dataclass(frozen=True)
class merchant_def:
    name: str        # lowercase
    category: str    # lowercase
    whitelisted: bool


# allowed merchants (policy ok)
whitelist_merchants: List[merchant_def] = [
    merchant_def("lufthansa",        "flight",     True),
    merchant_def("ryanair",          "flight",     True),
    merchant_def("emirates",         "flight",     True),
    merchant_def("hilton",           "hotel",      True),
    merchant_def("marriott",         "hotel",      True),
    merchant_def("ibis",             "hotel",      True),
    merchant_def("businesstaxi",     "taxi",       True),
    merchant_def("workcanteen",      "restaurant", True),
    merchant_def("officesuppliesco", "supplies",   True),
    merchant_def("trainexpress",     "train",      True),
]

# suspicious/personal merchants
non_whitelist_merchants: List[merchant_def] = [
    merchant_def("luxurymall",   "shopping",      False),
    merchant_def("toystore",     "shopping",      False),
    merchant_def("electrofun",   "electronics",   False),
    merchant_def("beachresort",  "hotel",         False),
    merchant_def("nightclubx",   "entertainment", False),
    merchant_def("groceryplus",  "grocery",       False),
    merchant_def("cinemaworld",  "entertainment", False),
    merchant_def("gamingworld",  "electronics",   False),
]

whitelist_names = {m.name for m in whitelist_merchants}
non_whitelist_names = {m.name for m in non_whitelist_merchants}


def is_whitelisted_merchant(merchant_name: str) -> int:
    """
    1 if known whitelisted, 0 if known bad or unknown.
    strict on unknowns to make it interesting.
    """
    name = str(merchant_name).lower()
    if name in whitelist_names:
        return 1
    if name in non_whitelist_names:
        return 0
    return 0


def is_late_hour(hour: int) -> int:
    """
    late evening / night flag:
    from 21:00 until 05:59 considered suspicious window.
    """
    return int(hour >= late_hour_start or hour < early_hour_end)


def label_misuse(
    *,
    merchant_name: str,
    mcc_category: str,
    is_whitelisted_merchant: int,
    has_business_trip: int,
    hour: int,
    amount: float,
) -> int:
    """
    synthetic misuse rules:

      1) very small amount          -> misuse
      2) non-whitelisted merchant   -> misuse
      3) flight/hotel w/o trip      -> misuse
      4) late-hour + personal cat   -> misuse

    gender is NOT used in the rule (we keep it fair),
    but the model will see gender as a feature so you can
    inspect if it correlates with patterns.
    """

    cat = str(mcc_category).lower()
    late = is_late_hour(hour)

    # 1) tiny amount
    if amount < small_suspicious_amount:
        return 1

    # 2) merchant outside whitelist
    if is_whitelisted_merchant == 0:
        return 1

    # 3) travel-like but no approved trip
    if cat in {"flight", "hotel"} and has_business_trip == 0:
        return 1

    # 4) late evening / night personal-style spending
    if late == 1 and cat in personal_night_cats:
        return 1

    return 0
