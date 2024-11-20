def calculate_device_score(device_score) -> float:
    """Calculate device component from e, p, f variables"""
    # return 0.75 * e + 0.5 * p + 0.3 * f
    if device_score == "VERY_HIGH":
        return 1000
    elif device_score == "HIGH":
        return 750
    elif device_score == "MEDIUM":
        return 500
    elif device_score == "LOW":
        return 300


def calculate_input_validation_score(
    identity1,
    identity2,
) -> float:
    if isinstance(identity1, list):
        identity1 = identity1[0]
    if isinstance(identity2, list):
        identity2 = identity2[0]
    score = 0
    if identity1.lower() not in identity2.lower():
        score += 100
    return score


def calculate_network_validation_score(
    network_from_device, network_from_alt_data
) -> float:
    score = 0
    vi_names_list = ["vi", "vodafone", "idea"]
    lower_case_network = network_from_alt_data.lower()
    if lower_case_network in vi_names_list:
        for network in vi_names_list:
            if find_needle_in_haystack_contains(network, network_from_device):
                score += 100
    else:
        if find_needle_in_haystack_contains(lower_case_network, network_from_device):
            score += 100
    return score


def calculate_app_profile_score(downloaded_apps, account_apps) -> float:
    """Calculate app presence score with penalties"""
    score = 0
    downloaded_set = set(downloaded_apps)
    account_set = set(account_apps)

    for app in account_set:
        if not find_needle_in_haystack_contains(app, downloaded_apps):
            score += 1000 / len(account_set)

    return score


def find_needle_in_haystack_contains(needle, haystack) -> bool:
    for val in haystack:
        if needle.lower() in val.lower():
            return True
    return False


def calculate_final_score(
    alternate_risk_score: float,
    device_risk_level: str,
    name_from_input,
    name_from_alt_data,
    network_from_device,
    network_from_alt_data,
    downloaded_apps,
    account_apps,
):
    # Calculate component scores
    device_score = calculate_device_score(device_risk_level)
    input_validation = calculate_input_validation_score(
        name_from_input, name_from_alt_data
    )
    network_validation = calculate_network_validation_score(
        network_from_device, network_from_alt_data
    )
    app_profile_score = calculate_app_profile_score(downloaded_apps, account_apps)

    # Calculate final score
    final_score = (
        0.5 * alternate_risk_score
        + 0.2 * device_score
        + 0.05 * input_validation
        + 0.10 * network_validation
        + 0.15 * app_profile_score
    )

    # Ensure final score is between 0 and 1
    # final_score = max(0, min(1, final_score))

    # Return detailed scoring breakdown
    return {
        "final_score": final_score,
        "component_scores": {
            "risk_score": alternate_risk_score,
            "device_risk_score": device_score,
            "input_validation_score": input_validation,
            "network_validation_score": network_validation,
            "app_score": app_profile_score,
        },
    }


def example_usage():
    # Sample data with mismatches
    x = 700
    e = "VERY_HIGH"

    identity1 = {
        "phone": "1234567890",
        "email": "user1@example.com",
        "name": "John Doe",
    }
    identity2 = {
        "phone": ["1234567890"],
        "email": ["user2@example.com"],
        "name": ["John Doe"],
    }

    # profile1 = {'currentNetwork': 'Airtel', 's': 'val2', 'd': 'val3', 'f': 'val4', 'g': 'val5', 'h': 'val6'}
    profile1 = {
        "currentNetwork": "Airtel",
    }
    profile2 = {
        "currentNetwork": "Airtel1",
    }
    # profile2 = {'currentNetwork': 'val1', 's': 'different', 'd': 'val3', 'f': 'different', 'g': 'val5', 'h': 'val6'}

    downloaded_apps = ["amazon", "netflix"]
    account_apps = ["amazon", "facebook", "netflix", "spotify"]

    # Get scores with default weights
    result = calculate_final_score(
        x, e, identity1, identity2, profile1, profile2, downloaded_apps, account_apps
    )

    return result
