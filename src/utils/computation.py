
def calculate_device_score(device_score) -> float:
    """Calculate device component from e, p, f variables"""
    # return 0.75 * e + 0.5 * p + 0.3 * f
    if device_score=="VERY_HIGH":
        return 1000
    elif device_score=="HIGH":
        return 750
    elif device_score=="MEDIUM":
        return 500
    elif device_score=="LOW":
        return 300

def calculate_input_validation_score(
    identity1,
    identity2,
) -> float:
    """Calculate identity matching score with penalties"""
    score = 0
    
    for field in identity1.keys():
        if not identity1[field] in identity2[field]:
            score += 1000/len(identity2.keys())
    
    return score

def calculate_network_validation_score(
    profile1,
    profile2,
) -> float:
    score = 0
    
    for field in profile1.keys():
        if profile1[field] != profile2[field]:
            score += 1000/len(profile2.keys())
    
    return score

def calculate_app_profile_score(
    downloaded_apps,
    account_apps) -> float:
    """Calculate app presence score with penalties"""
    score = 0
    downloaded_set = set(downloaded_apps)
    account_set = set(account_apps)
    
    for app in account_set:
        if app in account_set and app not in downloaded_set:
            score += 1000/len(account_set)
    
    return score


def calculate_final_score(
    x: float,
    e: float,
    identity1,
    identity2,
    profile1,
    profile2,
    downloaded_apps,
    account_apps,
):

    
    # Calculate component scores
    y = calculate_device_score(e)
    a = calculate_input_validation_score(identity1, identity2)
    b = calculate_network_validation_score(profile1, profile2)
    c = calculate_app_profile_score(downloaded_apps, account_apps)
    
    # Calculate final score
    final_score = 0.5 * x + 0.2 * y + 0.05 * a + 0.10 * b + 0.15 * c
    
    # Ensure final score is between 0 and 1
    # final_score = max(0, min(1, final_score))
    
    # Return detailed scoring breakdown
    return {
        'final_score': final_score,
        'component_scores': {
            'risk_score': x,
            'device_risk_score': y,
            'input_validation_score': a,
            'network_validaiton_score': b,
            'app_score': c
        }
    }

def example_usage():
    # Sample data with mismatches
    x = 700
    e="VERY_HIGH"
    
    identity1 = {'phone': '1234567890', 'email': 'user1@example.com', 'name': 'John Doe'}
    identity2 = {'phone': ['1234567890'], 'email': ['user2@example.com'], 'name': ['John Doe']}
    
    # profile1 = {'currentNetwork': 'Airtel', 's': 'val2', 'd': 'val3', 'f': 'val4', 'g': 'val5', 'h': 'val6'}
    profile1 = {'currentNetwork': 'Airtel',}
    profile2 = {'currentNetwork': 'Airtel1', }
    # profile2 = {'currentNetwork': 'val1', 's': 'different', 'd': 'val3', 'f': 'different', 'g': 'val5', 'h': 'val6'}
    
    downloaded_apps = ['amazon', 'netflix']
    account_apps = ['amazon', 'facebook', 'netflix', 'spotify']
    
    # Get scores with default weights
    result = calculate_final_score(
        x, e,
        identity1, identity2,
        profile1, profile2,
        downloaded_apps, account_apps
    )
    
    return result