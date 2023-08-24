from math import sqrt


def ol_pp_score(pp_r_start: int, pp_n_p: int, leading_edge: int, cfg) -> int:
    """
    Higher score is better
    """
    dist_extend = pp_r_start - cfg["min_overlap"] - leading_edge
    prop_extended = dist_extend / cfg["amplicon_size_max"]

    return prop_extended**2 / sqrt(pp_n_p)


def walk_pp_score(pp_f_end: int, pp_n_p: int, leading_edge: int) -> int:
    return (pp_f_end - leading_edge) * sqrt(pp_n_p)
