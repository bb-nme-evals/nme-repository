"""
Configuration and mappings for NME extraction.
"""

# Known isotopes in NME literature
KNOWN_ISOTOPES = {
    "76Ge", "96Zr", "100Mo", "116Cd", "128Te", "130Te", "136Xe",
    "76Ge", "82Se", "130Te", "150Nd",  # Common beta-decay candidates
}

# Model classes (theoretical approaches)
MODEL_CLASSES = {
    "QRPA",  # Quasiparticle Random Phase Approximation
    "Shell Model",
    "EDF",   # Energy Density Functional
    "IBM",   # Interacting Boson Model
}

# Standard model variants
MODEL_VARIANTS = {
    "WS",      # Woods-Saxon
    "sp",      # Single-particle
    "large",   # Large model space
    "small",   # Small model space
}

# Matrix element field mappings
# Maps various PDF notations to canonical field names
MATRIX_ELEMENT_ALIASES = {
    # Total matrix element
    "M_{total}": ["M_total", "M_{total}", "M_0νββ", "M"],
    
    # Long/short range
    r"M_{long\,range}": ["M_LR", "M_{LR}", "M_long", "M_{long}", "M_long_range"],
    r"M_{short\,range}": ["M_SR", "M_{SR}", "M_short", "M_{short}", "M_short_range"],
    
    # Summed channels
    "M_{GT}": ["M_GT", "M_{GT}", "M_Gamow-Teller", "M_Gamow Teller"],
    "M_F": ["M_F", "M_{F}", "M_Fermi"],
    "M_T": ["M_T", "M_{T}", "M_Tensor"],
    
    # Subcomponents - Fermi
    "M_{Fsd}": ["M_Fsd", "M_{Fsd}", "M_F^{sd}"],
    
    # Subcomponents - Gamow-Teller
    "M_{GT}^{AA}": ["M_GT^{AA}", "M_{GT}^{AA}", "M_GT(AA)"],
    "M_{GT}^{AP}": ["M_GT^{AP}", "M_{GT}^{AP}", "M_GT(AP)"],
    "M_{GT}^{PP}": ["M_GT^{PP}", "M_{GT}^{PP}", "M_GT(PP)"],
    "M_{GT}^{MM}": ["M_GT^{MM}", "M_{GT}^{MM}", "M_GT(MM)"],
    
    # Subcomponents - Tensor
    "M_{T}^{AA}": ["M_T^{AA}", "M_{T}^{AA}", "M_T(AA)"],
    "M_{T}^{AP}": ["M_T^{AP}", "M_{T}^{AP}", "M_T(AP)"],
    "M_{T}^{PP}": ["M_T^{PP}", "M_{T}^{PP}", "M_T(PP)"],
    "M_{T}^{MM}": ["M_T^{MM}", "M_{T}^{MM}", "M_T(MM)"],
    
    # Subcomponents - GT single-particle excitations
    "M_{GTsd}^{AA}": ["M_GTsd^{AA}", "M_{GTsd}^{AA}", "M_GT^{sd,AA}"],
    "M_{GTsd}^{AP}": ["M_GTsd^{AP}", "M_{GTsd}^{AP}", "M_GT^{sd,AP}"],
    "M_{GTsd}^{PP}": ["M_GTsd^{PP}", "M_{GTsd}^{PP}", "M_GT^{sd,PP}"],
    
    # Subcomponents - Tensor single-particle excitations
    "M_{Tsd}^{AP}": ["M_Tsd^{AP}", "M_{Tsd}^{AP}", "M_T^{sd,AP}"],
    "M_{Tsd}^{PP}": ["M_Tsd^{PP}", "M_{Tsd}^{PP}", "M_T^{sd,PP}"],
}

# Reverse mapping: alias -> canonical name
ALIAS_TO_CANONICAL = {}
for canonical, aliases in MATRIX_ELEMENT_ALIASES.items():
    for alias in aliases:
        ALIAS_TO_CANONICAL[alias.lower()] = canonical

# Canonical field order for entries
ENTRY_FIELD_ORDER = [
    "Model class",
    "Model",
    "Isotope",
    "g_A",
    "matrix_elements",
]

# Matrix element structure (hierarchical)
MATRIX_ELEMENT_STRUCTURE = {
    "M_{total}": None,             # Leaf: {value, error}
    r"M_{long\,range}": None,      # Leaf: {value, error}
    r"M_{short\,range}": None,     # Leaf: {value, error}
    "M_summed": {                  # Branch
        "M_{GT}": None,
        "M_F": None,
        "M_T": None,
    },
    "M_subcomponents": {           # Branch
        "M_F": None,
        "M_{GT}^{AA}": None,
        "M_{GT}^{AP}": None,
        "M_{GT}^{PP}": None,
        "M_{GT}^{MM}": None,
        "M_{T}^{AA}": None,
        "M_{T}^{AP}": None,
        "M_{T}^{PP}": None,
        "M_{T}^{MM}": None,
        "M_{Fsd}": None,
        "M_{GTsd}^{AA}": None,
        "M_{GTsd}^{AP}": None,
        "M_{GTsd}^{PP}": None,
        "M_{Tsd}^{AP}": None,
        "M_{Tsd}^{PP}": None,
    },
}

# Error notation patterns (regex patterns to detect uncertainty format)
ERROR_PATTERNS = [
    r"\(\d+\)",                    # (3) format: value(error)
    r"±",                          # ± format: value ± error
    r"\+/-",                       # +/- format: value +/- error
]

# Isotope name patterns (for parsing PDF text)
ISOTOPE_PATTERN = r"([0-9]{2,3})([A-Z][a-z]?)"  # e.g., 76Ge, 100Mo

# g_A values (standard axial coupling constants)
STANDARD_g_A = ["1.00", "1.27", "1.256", "1.25"]

# Configuration for table detection
TABLE_DETECTION = {
    "keywords": ["matrix element", "nuclear matrix", "M_", "NME", "β decay"],
    "min_rows": 2,
    "min_cols": 3,
}

# Fuzzy matching threshold for semantic parsing (0-100, higher = stricter)
FUZZY_MATCH_THRESHOLD = 75
