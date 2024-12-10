# Define role mappings
role_mapping = {
    "top": "top",
    "jungle": "jungle", "jg": "jungle", "jgl": "jungle", "jung": "jungle",
    "mid": "mid", "middle": "mid",
    "adc": "adc",
    "support": "support", "supp": "support",
    "fill": "fill"
}

# Function to map role variations to standardized roles
def get_standard_role(role: str) -> str:
    if not role:
        return None
    return role_mapping.get(role.lower())