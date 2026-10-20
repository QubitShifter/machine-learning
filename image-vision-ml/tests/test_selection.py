from ml.ingestion.selection import season_name, select_stratified_scenes


def _record(scene_id, date, cloud=1.0):
    return {
        "scene_id": scene_id,
        "acquisition_date": date,
        "acquisition_datetime": date + "T10:00:00Z",
        "cloud_cover": cloud,
    }


def test_stratified_selection_spans_years_and_seasons():
    records = [
        _record("y23_winter", "2023-01-10", 1.0),
        _record("y23_spring", "2023-04-10", 2.0),
        _record("y23_summer", "2023-07-10", 3.0),
        _record("y23_clearer_winter", "2023-02-01", 0.1),
        _record("y24_winter", "2024-01-12", 4.0),
        _record("y24_spring", "2024-05-01", 5.0),
        _record("y24_autumn", "2024-10-01", 1.5),
        _record("y25_winter", "2025-01-08", 2.0),
        _record("y25_spring", "2025-03-20", 1.0),
        _record("y25_summer", "2025-08-01", 6.0),
    ]
    selected = select_stratified_scenes(records, limit=9, scenes_per_year=3)
    assert len(selected) == 9
    years = {item["acquisition_date"][:4] for item in selected}
    assert years == {"2023", "2024", "2025"}
    seasons = {season_name(item["acquisition_date"]) for item in selected}
    assert len(seasons) >= 3
    selected_ids = {item["scene_id"] for item in selected}
    assert "y23_spring" in selected_ids
    assert "y25_summer" in selected_ids
    lowest_cloud_only = selected_ids == {"y23_clearer_winter"}
    assert not lowest_cloud_only


def test_selection_limit_zero():
    assert select_stratified_scenes([_record("a", "2023-01-01")], limit=0) == []
