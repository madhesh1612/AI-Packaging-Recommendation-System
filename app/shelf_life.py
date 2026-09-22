"""
Shelf-life prediction using a simplified Q10 temperature-dependence model,
adjusted by how well the chosen packaging's WVTR meets the product's needs.

shelf_life = ref_shelf_life * Q10 ^ ((ref_temp - storage_temp) / 10) * wvtr_adjustment
"""

Q10 = 2.5  # typical Q10 for food spoilage reactions (2-3 range is standard)


def predict_shelf_life(ref_shelf_life_days: float, ref_temp_c: float,
                        storage_temp_c: float, material_wvtr_avg: float,
                        required_wvtr_max: float) -> float:
    temp_factor = Q10 ** ((ref_temp_c - storage_temp_c) / 10)

    # if material WVTR is well within the required max, moisture protection
    # is good -> small bonus; if it's close to/over the limit, small penalty
    if required_wvtr_max <= 0:
        wvtr_factor = 1.0
    else:
        ratio = material_wvtr_avg / required_wvtr_max
        wvtr_factor = max(0.6, min(1.3, 1.3 - 0.3 * ratio))

    predicted = ref_shelf_life_days * temp_factor * wvtr_factor
    return round(predicted, 1)
