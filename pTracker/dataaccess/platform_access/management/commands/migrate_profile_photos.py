import os
import stat

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.core.management.base import CommandError
from django.db import transaction

from pTracker.common.confidential_storage import StorageError
from pTracker.common.confidential_storage import StoredFileMissing
from pTracker.common.profile_photo import ALLOWED_TYPES
from pTracker.common.profile_photo import LEGACY_NAME_PATTERN
from pTracker.common.profile_photo import ProfilePhotoStore
from pTracker.common.upload_validation import UploadRejected
from pTracker.common.upload_validation import validate_content
from pTracker.dataaccess.platform_access.membership_da import MembershipDA
from pTracker.dataaccess.platform_access.tenancy_models import Company
from pTracker.dataaccess.ptracker_access.user_models import UserProfile


class Command(BaseCommand):
    help = ('Copy profile photos still stored under MEDIA_ROOT/employee_profile_photo/ into each '
            "employee's company confidential storage (<root>/<company uuid>/employee_profile_photo/) "
            'and point user_profile.profile_photo at the copy. Dry run unless --apply. The company '
            'is the single company the employee has an active membership in, else '
            'user_profile.company_id. Old files are kept unless --delete-old. Old files are read '
            'from MEDIA_ROOT/employee_profile_photo/ or --source-dir; with --match-username a '
            'missing stored name falls back to <username>.<ext>.')

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Copy files and update rows (default: report only)')
        parser.add_argument('--delete-old', action='store_true',
                            help='With --apply: remove an old file once no profile references it any more')
        parser.add_argument('--user', type=int, action='append', dest='users', help='Only this user id (repeatable)')
        parser.add_argument('--source-dir', help='Folder holding the old files (path inside the container)')
        parser.add_argument('--match-username', action='store_true',
                            help='If the stored file name has no file, use <username>.<ext> '
                                 '(stored extension first, then jpeg, jpg, png)')
        parser.add_argument('--max-mb', type=int, default=20,
                            help='Largest existing photo to migrate, in MB (default 20; new uploads stay at 2 MB)')

    def handle(self, *args, **options):
        apply, delete_old = options['apply'], options['delete_old']
        source_dir = options['source_dir']
        if source_dir:
            source_dir = os.path.realpath(source_dir)
            if not os.path.isdir(source_dir):
                raise CommandError(f'--source-dir is not a directory: {source_dir}')
        max_bytes = options['max_mb'] * 1024 * 1024
        usernames = dict(get_user_model().objects.values_list('id', 'username'))
        store = ProfilePhotoStore()
        profiles = UserProfile.objects.exclude(profile_photo__isnull=True).exclude(profile_photo='')
        if options['users']:
            profiles = profiles.filter(user_id__in=options['users'])
        companies = {c.id: c for c in Company.objects.all()}
        counts = {'moved': 0, 'already': 0, 'skipped': 0}
        moved_names = set()

        for profile in profiles.only('user_id', 'company_id', 'profile_photo').order_by('user_id'):
            user_id, value = profile.user_id, profile.profile_photo
            if store.is_company_stored(value):
                counts['already'] += 1
                continue

            company, reason = self.__company(user_id, profile.company_id, companies)
            if company is None:
                self.__skip(counts, user_id, value, reason)
                continue
            try:
                content, source_name = self.__read_old(store, source_dir, value, usernames.get(user_id),
                                                       options['match_username'])
                validate_content(content, ALLOWED_TYPES, max_bytes)
            except StoredFileMissing:
                self.__skip(counts, user_id, value, 'file missing or name not allowed')
                continue
            except (UploadRejected, StorageError) as error:
                self.__skip(counts, user_id, value, str(error))
                continue

            target = f'{company.uuid}/employee_profile_photo/'
            if not apply:
                self.stdout.write(f'user {user_id}: {source_name} -> {target} (company {company.id})')
                counts['moved'] += 1
                continue

            try:
                new_value = store.save_bytes(company, content, max_bytes)
            except (UploadRejected, StorageError) as error:
                self.__skip(counts, user_id, value, str(error))
                continue
            try:
                with transaction.atomic():
                    updated = UserProfile.objects.filter(user_id=user_id, profile_photo=value)\
                        .update(profile_photo=new_value)
                    if updated != 1:
                        raise RuntimeError('profile changed while migrating')
            except Exception as error:
                store.delete(new_value)
                self.__skip(counts, user_id, value, str(error))
                continue
            counts['moved'] += 1
            moved_names.add(source_name)
            self.stdout.write(f'user {user_id}: {source_name} -> {new_value}')

        if apply and delete_old:
            for name in sorted(moved_names):
                # The same legacy file can be shared by several profiles.
                if UserProfile.objects.filter(profile_photo=name).exists():
                    continue
                if source_dir:
                    os.unlink(os.path.join(source_dir, name))
                else:
                    store.delete(name)
                self.stdout.write(f'deleted old file {name}')

        verb = 'moved' if apply else 'to move'
        self.stdout.write(self.style.SUCCESS(
            f"{counts['moved']} {verb}, {counts['already']} already in company storage, "
            f"{counts['skipped']} skipped" + ('' if apply else ' (dry run - use --apply)')))

    def __company(self, user_id, profile_company_id, companies):
        member_of = {m.company_id: m.company for m in MembershipDA().get_active_memberships_for_user(user_id)}
        if len(member_of) == 1:
            return next(iter(member_of.values())), None
        if profile_company_id in member_of or (not member_of and profile_company_id in companies):
            return companies[profile_company_id], None
        if member_of:
            return None, f'active in several companies {sorted(member_of)}; user_profile.company_id does not decide'
        return None, f'no active membership and unknown company_id {profile_company_id}'

    def __read_old(self, store, source_dir, value, username, match_username):
        """ (bytes, file name) of an old photo; raises StoredFileMissing. Names
        must be plain file names, and nothing outside source_dir is read. """
        candidates = [value]
        if match_username and username:
            stored_ext = value.rsplit('.', 1)[-1].lower() if '.' in value else ''
            for ext in dict.fromkeys([stored_ext, 'jpeg', 'jpg', 'png']):
                if ext in ('jpeg', 'jpg', 'png'):
                    candidates.append(f'{username}.{ext}')
        for name in candidates:
            if not LEGACY_NAME_PATTERN.match(name or ''):
                continue
            if source_dir is None:
                content = store.read_or_none(name)
            else:
                content = self.__read_file(source_dir, name)
            if content:
                return content, name
        raise StoredFileMissing('No old file')

    @staticmethod
    def __read_file(source_dir, name):
        path = os.path.join(source_dir, name)
        try:
            fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
        except OSError:
            return None
        with os.fdopen(fd, 'rb') as handle:
            if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
                return None
            return handle.read()

    def __skip(self, counts, user_id, value, reason):
        counts['skipped'] += 1
        self.stdout.write(self.style.WARNING(f'user {user_id}: skipped {value}: {reason}'))
