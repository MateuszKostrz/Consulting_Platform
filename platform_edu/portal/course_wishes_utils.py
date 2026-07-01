MAX_ORDERED_COUNTRY_SCAN = 50


def ordered_countries_for_form(academic):
    countries = [
        country.strip()
        for country in academic.country_preferences.split(',')
        if country.strip()
    ]
    if not countries:
        countries = ['']
    return countries


def save_course_wishes(academic, request):
    countries = [
        country.strip()
        for country in request.POST.getlist('country_preferences')
        if country.strip()
    ]
    academic.country_preferences = ', '.join(countries)
    academic.primary_course_preference = request.POST.get(
        'primary_course_preference', ''
    ).strip()
    academic.secondary_course_preference = request.POST.get(
        'secondary_course_preference', ''
    ).strip()
    academic.excluded_countries_cities = request.POST.get(
        'excluded_countries_cities', ''
    ).strip()
