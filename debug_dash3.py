from processing import (
    _split_sentences, organize_notes, SourceStatement,
    _INLINE_MEETING_METADATA, _EXPLANATORY_TEXT, _SECTION_HEADING,
    _METADATA_LINE, _ATTENDEE_LIST, _DECISION, _TENTATIVE, _PENDING_CUES,
    _TOPIC_HEADING, _cluster_similar_statements, _topic_similarity,
    _semantic_similarity, _is_action_sentence, _SUGGESTION, _ACTION,
    _IMPERATIVE_ACTION, _ASSIGNED_TO_ACTION, _NEGATION, _RESPONSIBLE,
    _RESPONSIBLE_MIXED, _RESPONSIBLE_ASKED, _RESPONSIBLE_WAS_ASKED,
    _RESPONSIBLE_TENTATIVE, _DEADLINE
)

notes = (
    'need to finish the dashboard before the next review. '
    'Rahul verma will update the charts by 2 nov. '
    "Priya said the dashboard is not approved yet, don't tell the client it is final."
)

sentences = _split_sentences(notes)
print('Sentences:')
for i, s in enumerate(sentences):
    print(f'  {i}: {s}')
    print(f'     is_action: {_is_action_sentence(s)}')
    print(f'     _ACTION: {bool(_ACTION.search(s))}')
    print(f'     _IMPERATIVE_ACTION: {bool(_IMPERATIVE_ACTION.search(s))}')
    print(f'     _ASSIGNED_TO_ACTION: {bool(_ASSIGNED_TO_ACTION.search(s))}')
    print()

result = organize_notes(notes)
print('Agenda items:')
for item in result.agenda_items:
    print(f'  {item.agenda_item}')
    print(f'    action_plan: {item.action_plan[:60]}')
    print(f'    action_items: {item.action_items}')
print()
print('All action_items:', result.action_items)
