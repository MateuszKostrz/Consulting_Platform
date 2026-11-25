"""One-time Notion Documents Tracker statuses (Nov 2025 screenshot)."""

# Column order: Passport, PS Form, Predicted Grades, Transcripts, Statement,
# Recommendation Letters, English Exam, Picture

D = 'done'
P = 'in_progress'
S = 'not_sent'
A = 'not_applicable'

# PlatformUser.id -> list of 8 statuses
NOTION_DOCUMENT_TRACKER_BY_USER_ID = {
    12: [D, D, S, D, S, D, D, D],  # Mateusz Stolarski
    14: [D, D, S, S, S, S, A, D],  # Bronisław Wypych (Bronek W.)
    15: [D, D, D, D, D, D, A, D],  # Helena Nielsen
    17: [D, D, S, P, S, S, D, S],  # Ryszard Dąbroś
    19: [D, D, S, D, D, S, A, D],  # Szymon Jasiołek
    18: [D, D, D, D, D, D, P, D],  # Konstancja Czarnoleska
    20: [D, D, S, D, D, S, A, S],  # Antoni Mączka - Magierowski
    22: [D, D, S, D, S, S, A, S],  # Filip Evangelou
    23: [D, D, S, D, S, S, A, S],  # Aleksander Osiadacz
    24: [S, D, S, S, S, S, S, S],  # Wiktor Olejniczak
    25: [S, D, S, S, S, S, A, S],  # Zuzanna Kacprzak
    29: [S, S, S, S, S, S, S, S],  # Michał Szczepanik
    28: [S, S, S, S, S, S, S, S],  # Sara Pilcek
    27: [S, S, S, S, S, S, S, S],  # Karol Kardaś
    26: [S, S, S, S, S, S, S, S],  # Aleksander Chimiak
}