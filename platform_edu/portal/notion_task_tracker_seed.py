"""One-time Notion Tasks Tracker statuses (Nov 2025 screenshot)."""

# Column order: Onboarding, Forms Sent, Diagnostic, Achievements, Research,
# Choices Made, PS, Email Created, CV, Docs, Application Portals

D = 'done'
P = 'in_progress'
N = 'not_started'
A = 'not_applicable'

# PlatformUser.id -> list of 11 statuses
NOTION_TASK_TRACKER_BY_USER_ID = {
    # Mateusz St. / Bronek W. — done through Email Created; CV not started; Docs & portals in progress
    12: [D, D, D, D, D, D, D, D, N, P, P],
    14: [D, D, D, D, D, D, D, D, N, P, P],
    # Helena N. / Ryszard Dąbroś — done through Research; then in progress except CV
    15: [D, D, D, D, D, P, P, P, N, P, P],
    17: [D, D, D, D, D, P, P, P, N, P, P],
    # Szymon Jasiołek — diagnostic N/A; CV in progress; otherwise done on early pipeline
    19: [D, D, A, D, D, D, D, D, P, D, D],
    # Konstancja Czyżewska (Czarnoleska) — docs done; CV in progress
    18: [D, D, D, D, D, D, D, P, P, D, P],
    # Antoni, Filip, Aleksander Osiadacz, Zuzanna — done through Choices; PS/Docs in progress
    20: [D, D, D, D, D, D, P, N, N, P, N],
    22: [D, D, D, D, D, D, P, N, N, P, N],
    23: [D, D, D, D, D, D, P, N, N, P, N],
    25: [D, D, D, D, D, D, P, N, N, P, N],
    # Wiktor Olejniczak — PS not started
    24: [D, D, D, D, D, D, N, N, N, P, N],
    # Not started across the board (Notion bottom rows)
    29: [N] * 11,
    28: [N] * 11,
    27: [N] * 11,
    26: [N] * 11,
}