def ellipsis(text, max_length=40):
    if len(text) > max_length:
        return text[:max_length] + '...'
    return text