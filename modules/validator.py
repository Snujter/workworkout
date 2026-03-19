def is_positive_int(val: str):
    if str(val).isdigit() and int(val) > 0:
        return True, int(val), ""
    return False, None, "Must be a positive integer."
