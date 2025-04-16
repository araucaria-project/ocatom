from django.db.models import Count
from django.contrib.auth.models import Group

import csv
from .models import Target, TargetExtra, TargetName
from io import StringIO
from django.db.models import ExpressionWrapper, FloatField
from django.db.models.functions.math import ACos, Cos, Radians, Pi, Sin
from math import radians


# NOTE: This saves locally. To avoid this, create file buffer.
# referenced https://www.codingforentrepreneurs.com/blog/django-queryset-to-csv-files-datasets/
def export_targets(qs):
    """
    Exports all the specified targets into a csv file in folder csvTargetFiles
    NOTE: This saves locally. To avoid this, create file buffer.

    :param qs: List of targets to export
    :type qs: QuerySet

    :returns: String buffer of exported targets
    :rtype: StringIO
    """
    qs_pk = [data['id'] for data in qs]
    data_list = list(qs)
    target_fields = [field.name for field in Target._meta.get_fields()]
    target_extra_fields = list({field.key for field in TargetExtra.objects.filter(target__in=qs_pk)})
    # Gets the count of the target names for the target with the most aliases in the database
    # This is to construct enough row headers of format "name2, name3, name4, etc" for exporting aliases
    # The alias headers are then added to the set of fields for export
    aliases = TargetName.objects.filter(target__in=qs_pk).values('target_id').annotate(count=Count('target_id'))
    max_alias_count = 0
    if aliases:
        max_alias_count = max([alias['count'] for alias in aliases])
    all_fields = target_fields + target_extra_fields + [f'name{index+1}' for index in range(1, max_alias_count+1)]
    for key in ['id', 'targetlist', 'dataproduct', 'observationrecord', 'reduceddatum', 'aliases', 'targetextra']:
        all_fields.remove(key)

    file_buffer = StringIO()
    writer = csv.DictWriter(file_buffer, fieldnames=all_fields)
    writer.writeheader()
    for target_data in data_list:
        extras = list(TargetExtra.objects.filter(target_id=target_data['id']))
        names = list(TargetName.objects.filter(target_id=target_data['id']))
        for e in extras:
            target_data[e.key] = e.value
        name_index = 2
        for name in names:
            target_data[f'name{str(name_index)}'] = name.name
            name_index += 1
        # do not export 'pk's
        for pointer_key in [pk for pk in target_data.keys() if pk.endswith('_ptr_id')]:
            del target_data[pointer_key]
        del target_data['id']
        writer.writerow(target_data)
    return file_buffer


def convert_ra(value):
    """
    Konwertuje RA w formacie hh:mm:ss na float (stopnie).
    """
    if ':' in value:
        try:
            hours_str, minutes_str, seconds_str = value.split(':')
            hours = float(hours_str)
            minutes = float(minutes_str)
            seconds = float(seconds_str)
            return hours * 15 + minutes * 15/60 + seconds * 15/3600
        except Exception as e:
            raise ValueError(f"Błąd konwersji RA '{value}': {e}")
    else:
        # zakładamy, że to już jest liczba w stringu
        return float(value)


def convert_dec(value):
    """
    Konwertuje deklinację z formatu ±dd:mm:ss na liczbę w stopniach (float).
    Obsługuje np. '+15:36:12.75', '-11:11:52.75', itp.
    Jeśli nie ma dwukropków, traktuje to jako float w stopniach.
    """
    value = value.strip()
    if ':' in value:
        sign = 1
        if value.startswith('-'):
            sign = -1
            value = value[1:]
        elif value.startswith('+'):
            value = value[1:]

        # Teraz value powinno wyglądać np. '15:36:12.75'
        parts = value.split(':')
        if len(parts) != 3:
            raise ValueError("Niepoprawny format DEC, oczekiwano ±dd:mm:ss")

        degrees = float(parts[0])
        minutes = float(parts[1])
        seconds = float(parts[2])

        # Deklinację w formacie dd:mm:ss przeliczamy na °:
        #  dec(°) = ±( dd + mm/60 + ss/3600 )
        dec_degrees = sign * (degrees + minutes/60 + seconds/3600)
        return dec_degrees

    else:
        # zakładamy, że to już jest liczba, np. '36.459'
        return float(value)


def import_targets(target_stream):
    """
    Imports a set of targets into the TOM and saves them to the database.

    :param target_stream: String buffer of targets
    :type target_stream: StringIO

    :returns: dictionary of successfully imported targets, as well errors
    :rtype: dict
    """
    # TODO: Replace this with an in memory iterator
    targetreader = csv.DictReader(target_stream, dialect=csv.excel)
    targets = []
    errors = []
    base_target_fields = [field.name for field in Target._meta.get_fields()]
    for index, row in enumerate(targetreader):
        # filter out empty values in base fields, otherwise converting empty string to float will throw error
        row = {k: v for (k, v) in row.items() if not (k in base_target_fields and not v)}
        target_extra_fields = []
        target_names = []
        group_names = []
        target_fields = {}
        for k in row:
            # All fields starting with 'name' (e.g. name2, name3) that aren't literally 'name' will be added as
            # TargetNames
            if k != 'name' and k.startswith('name'):
                target_names.append(row[k])
            elif k == 'groups':
                groups = row[k].split(',')
                for group in groups:
                    group_names.append(group.strip())
            elif k not in base_target_fields:
                target_extra_fields.append((k, row[k]))
            else:
                # standardowo bierzemy wartość z row
                value = row[k]

                # Jeśli klucz to 'ra', spróbuj konwertować
                if k == 'ra':
                    try:
                        value = convert_ra(value)
                    except ValueError as e:
                        error = f"Error on line {index + 2}: {e}"
                        errors.append(error)
                        continue  # pomijamy ten wiersz

                if k == 'dec':
                    try:
                        value = convert_dec(value)
                    except ValueError as e:
                        error = f"Error on line {index + 2}: {e}"
                        errors.append(error)
                        continue

                # przypisz przetworzoną wartość do target_fields
                target_fields[k] = value

        for extra in target_extra_fields:
            row.pop(extra[0])
        try:
            target = Target.objects.create(**target_fields)
            for extra in target_extra_fields:
                TargetExtra.objects.create(target=target, key=extra[0], value=extra[1])
            for name in target_names:
                if name:
                    TargetName.objects.create(target=target, name=name)
            targets.append(target)
            for group in group_names:
                try:
                    group_instance = Group.objects.get(name=group)
                    target.give_user_access(group_instance)
                except Group.DoesNotExist:
                    pass
        except Exception as e:
            error = 'Error on line {0}: {1}'.format(index + 2, str(e))
            errors.append(error)

    return {'targets': targets, 'errors': errors}


def cone_search_filter(queryset, ra, dec, radius):
    """
    Executes cone search by annotating each target with separation distance from the specified RA/Dec.
    Formula is from Wikipedia: https://en.wikipedia.org/wiki/Angular_distance
    The result is converted to radians.

    Cone search is preceded by a square search to reduce the search radius before annotating the queryset, in
    order to make the query faster.

    :param queryset: Queryset of Target objects
    :type queryset: Target

    :param ra: Right ascension of center of cone.
    :type ra: float

    :param dec: Declination of center of cone.
    :type dec: float

    :param radius: Radius of cone search in degrees.
    :type radius: float
    """
    ra = float(ra)
    dec = float(dec)
    radius = float(radius)

    double_radius = radius * 2
    queryset = queryset.filter(
        ra__gte=ra - double_radius, ra__lte=ra + double_radius,
        dec__gte=dec - double_radius, dec__lte=dec + double_radius
    )

    separation = ExpressionWrapper(
        180 * ACos(
            (Sin(radians(dec)) * Sin(Radians('dec'))) +
            (Cos(radians(dec)) * Cos(Radians('dec')) * Cos(radians(ra) - Radians('ra')))
        ) / Pi(), FloatField()
    )

    return queryset.annotate(separation=separation).filter(separation__lte=radius)
