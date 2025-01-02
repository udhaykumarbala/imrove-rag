def _json_to_promptable_test(data):
    if data is None:
        return "No relevant lender information found."
    
    try:
        # Handle dictionary-like objects
        if isinstance(data, dict):
            result = []
            for key, value in data.items():
                if value is None:
                    value = "N/A"
                elif isinstance(value, (dict, list)):
                    value = str(value)
                result.append(f"{key}: {value}")
            return "\n".join(result)
        
        # Handle list-like objects
        elif isinstance(data, list):
            return "\n".join(str(item) if item is not None else "N/A" for item in data)
        
        # Handle everything else
        return str(data)
    except Exception as e:
        print(f"Error converting to promptable text: {e}")
        return ""

def document_to_promptable(documents):
    if not documents:
        return ""
        
    document_str = ""
    try:
        for i in documents:
            doc_text = _json_to_promptable_test(i)
            if doc_text:  # Only concatenate if we have actual text
                document_str += doc_text + "\n"
        return document_str.strip()
    except Exception as e:
        print(f"Error in document_to_promptable: {e}")
        return ""