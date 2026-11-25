content = open(r'E:\Gauri\projects\OfflineNoteAI\processing.py').read()
old = '''    # Second pass: merge topics that share multiple meaningful content words.
    # A single shared word (even a strong one like "faculty") is not enough to
    # merge unrelated topics; require at least 2 shared content words.
    _WEAK_MERGE_WORDS = {
        "faculty", "meeting", "meetings", "team", "committee", "project",
        "projects", "report", "reports", "review", "reviews", "discussion",
        "discussions", "update", "updates", "status", "plan", "plans",
    }

    merged_topics: list[list[SourceStatement]] = []
    for topic in topics:
        topic_words = _content_words(" ".join(s.text for s in topic))
        placed = False
        for mt in merged_topics:
            mt_words = _content_words(" ".join(s.text for s in mt))
            shared = topic_words & mt_words
            if len(shared) < 2:
                continue
            strong_shared = shared - _WEAK_MERGE_WORDS
            if len(strong_shared) >= 1:
                mt.extend(topic)
                placed = True
                break
        if not placed:
            merged_topics.append(topic)

    return merged_topics'''
new = '''    # Second pass: merge topics that share multiple meaningful content words.
    _WEAK_MERGE_WORDS = {
        "faculty", "meeting", "meetings", "team", "committee", "project",
        "projects", "report", "reports", "review", "reviews", "discussion",
        "discussions", "update", "updates", "status", "plan", "plans",
        "next", "week", "internal", "demo", "client", "date", "time",
    }

    merged_topics: list[list[SourceStatement]] = []
    for topic in topics:
        topic_words = _content_words(" ".join(s.text for s in topic))
        placed = False
        for mt in merged_topics:
            mt_words = _content_words(" ".join(s.text for s in mt))
            shared = topic_words & mt_words
            if not shared:
                continue
            strong_shared = shared - _WEAK_MERGE_WORDS
            if len(strong_shared) >= 1 or len(shared) >= 2:
                mt.extend(topic)
                placed = True
                break
        if not placed:
            merged_topics.append(topic)

    return merged_topics'''
if old not in content:
    print('not found')
else:
    content2 = content.replace(old, new)
    open(r'E:\Gauri\projects\OfflineNoteAI\processing.py','w').write(content2)
    print('ok')
