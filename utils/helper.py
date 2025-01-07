from services.embedding import _construct_vector_text

def document_to_promptable(documents):
    if not documents:
        return ""
    document_str = ""
    try:
        for idx, doc in enumerate(documents):
            doc_text = _construct_vector_text(doc)
            if doc_text:
                document_str += f"{idx+1}.\n" + doc_text + "\n\n"
        return document_str.strip()
    except Exception as e:
        print(f"Error in document_to_promptable: {e}")
        return ""

