from services.xai import XAIEmbedding
from services.pinecone import PineconeService
import uuid
from datetime import datetime

embed = XAIEmbedding()
pinecone_handler = PineconeService()

def _format_range(min_val, max_val, prefix="", suffix=""):
    """Helper function to format range values"""
    if min_val == max_val == 0:
        return "Not specified"
    if max_val == 0:
        return f"{prefix}{min_val}{suffix} minimum"
    return f"{prefix}{min_val}{suffix} to {prefix}{max_val}{suffix}"

def _format_list(items):
    """Helper function to format lists"""
    if not items:
        return "Not specified"
    if len(items) == 1:
        return items[0]
    return ", ".join(items[:-1]) + " and " + items[-1]

def _statecode_to_state(statecode):
    """Helper function to convert state code to state name"""
    state_codes = {
        "AL": "Alabama",
        "AK": "Alaska",
        "AZ": "Arizona",
        "AR": "Arkansas",
        "CA": "California",
        "CO": "Colorado",
        "CT": "Connecticut",
        "DE": "Delaware",
        "FL": "Florida",
        "GA": "Georgia",
        "HI": "Hawaii",
        "ID": "Idaho",
        "IL": "Illinois",
        "IN": "Indiana",
        "IA": "Iowa",
        "KS": "Kansas",
        "KY": "Kentucky",
        "LA": "Louisiana",
        "ME": "Maine",
        "MD": "Maryland",
        "MA": "Massachusetts",
        "MI": "Michigan",
        "MN": "Minnesota",
        "MS": "Mississippi",
        "MO": "Missouri",
        "MT": "Montana",
        "NE": "Nebraska",
        "NV": "Nevada",
        "NH": "New Hampshire",
        "NJ": "New Jersey",
        "NM": "New Mexico",
        "NY": "New York",
        "NC": "North Carolina",
        "ND": "North Dakota",
        "OH": "Ohio",
        "OK": "Oklahoma",
        "OR": "Oregon",
        "PA": "Pennsylvania",
        "RI": "Rhode Island",
        "SC": "South Carolina",
        "SD": "South Dakota",
        "TN": "Tennessee",
        "TX": "Texas",
        "UT": "Utah",
        "VT": "Vermont",
        "VA": "Virginia",
        "WA": "Washington",
        "WV": "West Virginia",
        "WI": "Wisconsin",
        "WY": "Wyoming"
    }
    return state_codes.get(statecode, statecode)

def _safe_get(d, *keys, default=None):
    """Safely get nested dictionary values"""
    try:
        value = d
        for key in keys:
            value = value[key]
        return value if value not in ("", None) else default
    except (KeyError, TypeError):
        return default

def _construct_vector_text(extract_document_info) -> str:
    """
    Construct a text string from document information for vectorization.
    Args:
        extract_document_info: Dictionary containing document information
    Returns:
        str: Constructed text string
    """
    info = extract_document_info
    parts = []
    
    parts.append(f"{_safe_get(info, 'company_name', default='Company')} offers {_safe_get(info, 'loan_plans', default='loan program')} loan program.")
    
    service_area = _safe_get(info, 'service_area', default=[])
    if service_area:
        service_area = [_statecode_to_state(statecode) for statecode in service_area]
        parts.append(f"They service the following states: {_format_list(service_area)}.")

    loan_amount_max = _safe_get(info, 'loan_amount', 'max', default=0)
    loan_amount_min = _safe_get(info, 'loan_amount', 'min', default=0)
    if loan_amount_min or loan_amount_max:
        parts.append(f"Loan amounts range from ${loan_amount_min} to ${loan_amount_max}.")

    ltv_ratio_max = _safe_get(info, 'ltv_ratio', 'max', default=0)
    ltv_ratio_min = _safe_get(info, 'ltv_ratio', 'min', default=0)
    if ltv_ratio_max or ltv_ratio_min:
        parts.append(f"Loan to value ratio range from {ltv_ratio_min} to {ltv_ratio_max}%.")
    
    interest_rate_min = _safe_get(info, 'interest_rate', 'min', default=0)
    interest_rate_max = _safe_get(info, 'interest_rate', 'max', default=0)
    if interest_rate_min or interest_rate_max:
        parts.append(f"Interest rates range from {interest_rate_min}% to {interest_rate_max}%.")
    
    loan_term_min = _safe_get(info, 'loan_term', 'min', default=0)
    loan_term_max = _safe_get(info, 'loan_term', 'max', default=0)
    if loan_term_min or loan_term_max:
        parts.append(f"Loan terms available from {loan_term_min} to {loan_term_max} years.")
    
    amortization = _safe_get(info, 'amortization', default="Not specified")
    if amortization:
        parts.append(f"Amortization: {amortization}.")

    credit_score_requirements = _safe_get(info, 'credit_score_requirements', default="Not specified")
    if credit_score_requirements:
        parts.append(f"Credit Score Requirements: {credit_score_requirements}.")

    points_charged = _safe_get(info, 'points_charged', default="Not specified")
    if points_charged:
        parts.append(f"Points charged: {points_charged}.")
    
    ltc_ratio_min = _safe_get(info, 'ltc_ratio', 'min', default=0)
    ltc_ratio_max = _safe_get(info, 'ltc_ratio', 'max', default=0)
    if ltc_ratio_min or ltc_ratio_max:
        parts.append(f"Loan terms available from {ltc_ratio_min} to {ltc_ratio_max} years.")

    dscr_min = _safe_get(info, 'dscr', 'min', default=0)
    dscr_max = _safe_get(info, 'dscr', 'max', default=0)
    if dscr_min or dscr_max:
        parts.append(f"Debt service coverage ratio range from {dscr_min} to {dscr_max}.")

    guidelines = _safe_get(info, 'guidelines', default="Not specified")
    if guidelines:
        parts.append(f"Guidelines: {guidelines}.")
    
    property_types = _safe_get(info, 'property_types', default="Not specified")
    if property_types:
        parts.append(f"Eligible property types: {_format_list(property_types)}.")
    
    application_requirements = _safe_get(info, 'application_requirements', default="Not specified")
    if application_requirements:
        parts.append(f"Application requirements: {application_requirements}.")
    
    liquidity_requirements = _safe_get(info, 'liquidity_requirements', default="Not specified")
    if liquidity_requirements:
        parts.append(f"Liquidity requirements: {liquidity_requirements}.")
    
    construction = _safe_get(info, 'construction', default="Not specified")
    if construction:
        parts.append(f"Construction loans: {construction}.")
    
    value_add = _safe_get(info, 'value_add', default="Not specified")
    if value_add:
        parts.append(f"Value add loans: {value_add}.")

    personal_guarantee = _safe_get(info, 'personal_guarantee', default="Not specified")
    if personal_guarantee:
        parts.append(f"Personal guarantee required: {personal_guarantee}.")

    contact_information = _safe_get(info, 'contact_information', default={})
    contact_parts = []
    contact_person = _safe_get(contact_information, 'person', default="")
    contact_phone_number = _safe_get(contact_information, 'phone_number', default="")
    contact_email = _safe_get(contact_information, 'email', default="")
    if contact_person:
        contact_parts.append(f"Contact {contact_person}")
    if contact_phone_number:
        contact_parts.append(f"at {contact_phone_number}")
    if contact_email:
        contact_parts.append(f"or email {contact_email}")
    if contact_parts:
        parts.append(" ".join(contact_parts) + ".")
    
    return " ".join(parts)

def _construct_vector_metadata(text, user_id, document_id) -> dict:
    """
    Construct metadata dictionary from document information for vectorization.
    Args:
        extract_document_info: Dictionary containing document information
    Returns:
        dict: Constructed metadata dictionary
    """
    metadata = {
        "document_id": document_id,
        "created_by": user_id,
        "created_at": datetime.utcnow(),
        "document_text": text
    }
    return metadata

def _construct_vector(extract_document_info, user_id, document_id) -> dict:
    """
    Construct a vector dictionary from document information for vectorization.
    Args:
        extract_document_info: Dictionary containing document information
    Returns:
        dict: Constructed vector dictionary
    """
    text = _construct_vector_text(extract_document_info)
    metadata = _construct_vector_metadata(text, user_id, document_id)
    vector = embed.create_embedding(text)

    return [
        {
            "id": str(uuid.uuid4()),
            "values": vector,
            "metadata": metadata
        }
    ]


def upsert_embedding(document_id, user_id, extract_document_info):
    """
    Store document embedding in Pinecone index.
    Args:
        extract_document_info: Dictionary containing document information
    Returns:
        bool: Success status
    """
    try:
        vectors = _construct_vector(extract_document_info, user_id, document_id)
        return pinecone_handler.upsert_vectors(vectors)
    except Exception as e:
        print(f"Error storing document embedding: {e}")
        return False


    
