
from  datetime import datetime, date, timedelta
from types import SimpleNamespace

from django.conf import settings
from django.db.models import query
from django.db.models import Q
from django.db.models import F

from django.contrib.auth.models import User
from django.contrib.auth.models import Group
from django.contrib.auth.models import Permission

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs

from pTracker.dataaccess.ptracker_access.tax_models import TaxPeriod
from pTracker.dataaccess.ptracker_access.tax_models import ClaimCategory
from pTracker.dataaccess.ptracker_access.tax_models import ClaimDeclaration
from pTracker.dataaccess.ptracker_access.tax_models import TaxPeriodExclude
from pTracker.dataaccess.ptracker_access.tax_models import TaxBatch
from pTracker.dataaccess.ptracker_access.tax_models import Claim
from pTracker.dataaccess.ptracker_access.tax_models import Parties
from pTracker.dataaccess.ptracker_access.tax_models import ClaimsActivity
from pTracker.dataaccess.ptracker_access.tax_models import ClaimAttachments
from pTracker.dataaccess.ptracker_access.tax_models import HraDetails
from pTracker.dataaccess.ptracker_access.tax_models import Chat
from pTracker.dataaccess.ptracker_access.tax_models import Message
from pTracker.dataaccess.ptracker_access.tax_models import EmployeeTDS
from pTracker.dataaccess.ptracker_access.tax_models import CtcMaster
from pTracker.dataaccess.ptracker_access.tax_models import CtcEmployee
from pTracker.dataaccess.ptracker_access.tax_models import EmployeeTaxDeduction

from django.db.models import Q

from pTracker.dataaccess.db import Connection

from io import BytesIO
import os

from PIL import Image


def new_dto():
    dto = SimpleNamespace()
    return dto


class TaxDA():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()


    def bulk_create_finance_data(self, data, financial_year_id):
        data_dict = []

        for each_item, value in data.items():
            data_dict.append(TaxBatch(fin_year_id = value['fin_year_id'],
            user_id = value['user_id'],
            last_date = value['last_date'],
            created_by = value['created_by']
            ))

        return TaxBatch.objects.bulk_create(data_dict)


    def bulk_create_tds_data(self, tds_data):
        data = []
        for each in tds_data:
            data.append(EmployeeTDS(fin_year_id=each['fin_year_id'],
                                    month_id=each['month_id'],
                                    year=each['year'],
                                    user_id=each['user_id'],
                                    last_updated_by=each['last_updated_by']))
        return EmployeeTDS.objects.bulk_create(data)
    
    def bulk_create_tds_data_v1(self, tds_data):
        data = []
        for each in tds_data:
            data.append(EmployeeTDS(fin_year_id=each['fin_year_id'],
                                    month_id=each['month_id'],
                                    year=each['year'],
                                    user_id=each['user_id'],
                                    amount= each['amount'],
                                    last_updated_by=each['last_updated_by']))
        return EmployeeTDS.objects.bulk_create(data)


    def get_declaration_by_period_and_user(self, tax_period_id, user_id):
        declarations = []
        try:
            declarations = ClaimDeclaration.objects.filter(tax_period_id=tax_period_id, user_id=user_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declarations


    def get_all_declarations_from_period_id(self, tax_period_id):
        declarations = []
        try:
            declarations = ClaimDeclaration.objects.filter(tax_period_id=tax_period_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declarations


    def bulk_update_tax_batch_data(self, tax_batch_data):
        is_updated = False
        for tax_batch in tax_batch_data:
            TaxBatch.objects.filter(id=tax_batch['id']).update(**tax_batch)
        is_updated = True
        return is_updated


    def get_all_tax_batches_from_period_id(self, period_id):
        tax_batch_data = []
        try:
            tax_batch_data = TaxBatch.objects.filter(tax_period_id=period_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch_data


    def get_parties_from_claim_ids(self, party_ids):
        parties = []
        try:
            parties = Parties.objects.filter(id__in=party_ids, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return parties


    def get_claims_by_declaration_ids(self, current_period_declarations):
        claims = []
        try:
            claims = Claim.objects.filter(claim_declaration_id__in=current_period_declarations, is_deleted=0).values_list('party_id', flat=True)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claims


    def get_users_current_period_declarations(self, user_id, tax_period_id, cat_id):
        current_declarations = []
        try:
            current_declarations = ClaimDeclaration.objects.filter(user_id=user_id, tax_period_id=tax_period_id,cat_id=cat_id,is_deleted=0).values_list('id')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return current_declarations


    def get_all_tax_batch_data_for_regime_type(self, tax_period_id, org_id):
        tax_batch_data = []
        try:
            tax_batch_data = TaxBatch.objects.filter(tax_period_id=tax_period_id, org_id=org_id, is_deleted=0).values_list('user_id', 'regime_type', 'org_id')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch_data


    def get_all_category_maximum_allowed_amount(self):
        maximum_allowed_list = []
        try:
            maximum_allowed_list = ClaimCategory.objects.all().values_list('id', 'maximum_allowed')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return maximum_allowed_list


    def get_maximum_declaration_amount(self, cat_id):
        maximum_allowed_amount = 0
        try:
            maximum_allowed_amount = ClaimCategory.objects.filter(id=cat_id).first().maximum_allowed
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return maximum_allowed_amount


    def get_approved_claims_amount_by_declaration_id(self, claim_declaration_id):
        approved_amount = 0
        try:
            approved_amount = Claim.objects.filter(claim_declaration_id=claim_declaration_id, status='Approved', is_deleted=0).values_list('amount', flat=True)
            approved_amount = list(map(lambda x: float(x), approved_amount))
            approved_amount = sum(approved_amount)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return approved_amount


    def get_in_progress_claim_amount_from_declaration_id(self, claim_declaration_id):
        in_progress_amount = 0
        try:
            in_progress_amount = Claim.objects.filter(claim_declaration_id=claim_declaration_id, status='Under Review', is_deleted=0).values_list('amount', flat=True)
            in_progress_amount = list(map(lambda x: float(x), in_progress_amount))
            in_progress_amount = sum(in_progress_amount)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return in_progress_amount


    def get_all_chat_ids_of_user(self, user_id):
        chat_ids = []
        try:
            chat_ids = Chat.objects.filter((Q(user_1=user_id) | Q(user_2=user_id))).values_list('chat_id')
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return chat_ids



    def get_unseen_message_count(self, user_id, chat_id):
        unseen_message_count = None
        try:
            unseen_message_count = Message.objects.filter(~Q(created_by=user_id), chat_id=chat_id, unseen=1).count()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return unseen_message_count


    def create_chat_data(self, user_id, emp_id):
        return Chat.objects.create(user_1=user_id, user_2=emp_id)


    def get_chat_from_users_id(self, user_id, emp_id):
        chat = None
        try:
            chat = Chat.objects.filter((Q(user_1=user_id) | Q(user_2=user_id)), (Q(user_1=emp_id) | Q(user_2=emp_id))).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return chat


    def create_message_data(self, user_id, chat_id, tax_period_id, content):
        return Message.objects.create(chat_id=chat_id, content=content, tax_period_id=tax_period_id, created_by=user_id)


    def get_chat_from_chat_id(self, chat_id):
        chat = None
        try:
            chat = Chat.objects.filter(chat_id=chat_id).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return chat


    def is_permitted_to_view_chat(self, chat_id, user_id):
        is_permitted = False
        try:
            is_permitted = Chat.objects.filter((Q(user_1=user_id) | Q(user_2=user_id)), chat_id = chat_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_permitted


    def get_chats_from_chat_id_and_tax_period_id(self, chat_id, tax_period_id):
        chats = []
        try:
            chats = Message.objects.filter(chat_id=chat_id, tax_period_id=tax_period_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return chats


    def get_tax_period_from_declaration_id(self, declaration_id):
        tax_period_id = None
        try:
            tax_period_id = ClaimDeclaration.objects.filter(id=declaration_id, is_deleted=0).first().tax_period_id
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period_id


    def get_section_and_category_from_cat_id(self, cat_id):
        section = category = None
        try:
            section = ClaimCategory.objects.filter(id=cat_id).first()
            if not section.parent_id == 0:
                category = section.name
                section = ClaimCategory.objects.filter(id=section.parent_id).first()
            section = section.name
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return section, category


    def delete_hra_details_by_claim_id(self, claim_id):
        is_deleted = False
        try:
            hra_details = HraDetails.objects.filter(claim_id=claim_id).first().delete()
            is_deleted = True
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_deleted

    def delete_hra_details_by_declaration_id(self, declaration_id):
        is_deleted = False
        try:
            hra_details = HraDetails.objects.filter(claim_declaration_id=declaration_id)
            deleted_count, _ = hra_details.delete()
            is_deleted=True
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_deleted


    def get_section_name_from_cat_id(self, cat_id):
        section_name = None
        try:
            category = ClaimCategory.objects.filter(id=cat_id).first()
            section_name = category.name if not category.parent_id else ClaimCategory.objects.filter(id=category.parent_id).first().name
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return section_name


    def get_hra_details_from_claim_id(self, claim_id):
        hra_details = None
        try:
            hra_details = HraDetails.objects.filter(claim_id=claim_id).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return hra_details


    def get_claimed_amount_by_declaration(self, declaration_id):
        total_claim_amount = 0
        try:
            claim_amount = Claim.objects.filter(claim_declaration_id=declaration_id, status__in=['Approved', 'Under Review'], is_deleted=0).values_list('amount', flat=True)
            total_claim_amount = sum(claim_amount)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return total_claim_amount


    def get_claim_declarations_under_tax_period_id(self, period_id):
        declarations = None
        try:
            declarations = ClaimDeclaration.objects.filter(tax_period_id=period_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declarations

    def get_claim_declaration_from_claim_id(self, claim_id):
        declaration_id = None
        try:
            declaration_id = Claim.objects.filter(id=claim_id, is_deleted=0).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declaration_id


    def get_claim_declaration_user_id(self, declaration_id):
        user_id = None
        try:
            claim_declaration = ClaimDeclaration.objects.filter(id=declaration_id, is_deleted=0).first()
            user_id = claim_declaration.user_id
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return user_id


    def get_claim_category_by_id(self, cat_id):
        claim_category = None
        try:
            claim_category = ClaimCategory.objects.filter(id=cat_id).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claim_category


    def delete_claims_by_declaration(self, declaration_id):
        claims = Claim.objects.filter(claim_declaration_id=declaration_id)
        claims.delete()
        claim_attachments = ClaimAttachments.objects.filter(claim_declaration_id=declaration_id)
        claim_attachments.delete()

    def get_declaration_amount_from_declaration_id(self, declaration_id):
        declaration_amount = None
        try:
            declaration_amount = ClaimDeclaration.objects.filter(id=declaration_id, is_deleted=0).first().amount
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declaration_amount

    def is_last_date_of_declaration_valid(self, tax_period_id, user_id):
        is_last_date_of_declaration_valid = None
        try:
            is_last_date_of_declaration_valid = TaxBatch.objects.filter(tax_period_id=tax_period_id, user_id=user_id, last_date_of_declaration__gte=datetime.now(), is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_last_date_of_declaration_valid


    def is_last_date_of_claim_entry_valid(self, tax_period_id, user_id):
        is_last_date_of_claim_entry_valid = None
        try:
            is_last_date_of_claim_entry_valid = TaxBatch.objects.filter(tax_period_id=tax_period_id, user_id=user_id, last_date_of_claim_entry__gte=datetime.now(), is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_last_date_of_claim_entry_valid


    def get_claim_from_claim_id(self, claim_id):
        claim = None
        try:
            claim = Claim.objects.filter(id=claim_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claim


    def delete_tax_batches_from_tax_period_id(self, tax_period_id):
        tax_batches = None
        try:
            tax_batches = TaxBatch.objects.filter(tax_period_id=tax_period_id).delete()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batches

    def get_tax_period_from_tax_period_id(self, tax_period_id):
        tax_period = None
        try:
            tax_period = TaxPeriod.objects.filter(id=tax_period_id, is_deleted=0).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period

    def get_tax_batch_by_period(self, tax_period_id, user_id=0):
        tax_batch = None
        try:
            tax_batch = TaxBatch.objects.filter(tax_period_id=tax_period_id, is_deleted=0)
            if user_id:
                tax_batch = tax_batch.filter(user_id=user_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch


    def get_tax_period_from_financial_year_id(self, financial_year_id):
        tax_period = None
        try:
            tax_period = TaxPeriod.objects.filter(fin_year_id=financial_year_id, is_deleted=0).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period


    def edit_tax_period_data(self, tax_period_id, data):
        return TaxPeriod.objects.filter(id=tax_period_id).update(**data)


    def get_all_tax_periods(self):
        return TaxPeriod.objects.filter(is_deleted=0)


    def get_claim_detail_with_parties(self, tax_period_id, cat_id,user_id):
        amount = name = address = pan_number = None
        try:
            claim = Claim.objects.filter(cat_id=cat_id, tax_period_id=tax_period_id, user_id=user_id, status='Approved', is_deleted=0).first()
            if claim:
                party = Parties.objects.filter(id=claim.party_id, is_deleted=0).first()
                amount = claim.amount if claim else 0
                if party:
                    name = party.name
                    address = party.address_line1
                    pan_number = party.pan_number

        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return amount, name, address, pan_number


    def get_claim_detail_without_parties(self, tax_period_id, cat_id, user_id):
        amount = None
        try:
            claim = Claim.objects.filter(cat_id=cat_id, tax_period_id=tax_period_id, user_id=user_id, status='Approved', is_deleted=0).first()
            amount = claim.amount if claim else 0
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return amount


    def get_claim_declaration_estimate_amount(self, user_id, tax_period_id, cat_id):
        estimate_amount = 0
        try:
            claim_declaration = ClaimDeclaration.objects.filter(user_id=user_id, tax_period_id=tax_period_id, cat_id=cat_id, is_deleted=0).first()
            estimate_amount = claim_declaration.amount if claim_declaration else 0
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return estimate_amount


    # def get_claim_declaration_estimate_amount_with_parties(self, user_id, tax_period_id, cat_id):
    #     estimate_amount = name = address = pan_number = None
    #     try:
    #         claim_declaration = ClaimDeclaration.objects.filter(user_id=user_id, tax_period_id=tax_period_id, cat_id=cat_id, is_deleted=0).first()
    #         estimate_amount = claim_declaration.amount if claim_declaration else 0
    #         claim = Claim.objects.filter(cat_id=cat_id, claim_declaration_id=claim_declaration.id, is_deleted=0).first()
    #         if claim:
    #             # amount = claim.amount
    #             party = Parties.objects.filter(claim_id=claim.id, is_deleted=0).first()
    #             name = party.name
    #             address = party.address_line1
    #             pan_number = party.pan_number
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return estimate_amount, name, address, pan_number


    def delete_tax_period(self, tax_period_id):
        tax_period = None
        try:
            tax_period = TaxPeriod.objects.filter(id=tax_period_id).update(is_deleted=1)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period


    def get_user_id_from_claim_declaration_id(self, claim_declaration_id):
        user_id = None
        try:
            user_id = ClaimDeclaration.objects.filter(id=claim_declaration_id, is_deleted=0).first().user_id
            return user_id
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
            return user_id

    # def get_parties_from_claim_id(self, claim_id):
    #     try:
    #         return Parties.objects.filter(id=claim_id, is_deleted=0).first()
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #         return None


    def get_claim_by_id(self, claim_id):
        try:
            return Claim.objects.filter(id=claim_id, is_deleted=0).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
            return None

    def get_fin_year_id_from_tax_period_id(self, tax_period_id):
        try:
            tax_period = TaxPeriod.objects.filter(id=tax_period_id, is_deleted=0).first()
            return tax_period.fin_year_id
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
            return None


    # def delete_party_using_claim_id(self, data, claim_id):
    #     try:
    #         party = Parties.objects.filter(claim_id=claim_id)
    #         party.delete()
            # if party.last().parent_id == 0:
            #     party.update(**data)
            #     return True
            # else:
            #     party.delete()
        #     return True
        # except Exception as err:
        #     self.__log.error(self.__exception.get_exception())
        #     return False

    def delete_party_using_list_claim_id(self, data, party_ids):
        try:
            for party_id in party_ids:
                party = Parties.objects.filter(id=party_id)
                if party.last().parent_id == 0:
                    party.update(**data)
                else:
                    party.delete()
            return True
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
            return False


    def delete_claim_attachments_by_claim_id(self, claim_id):
        files = ClaimAttachments.objects.filter(claim_id=claim_id)
        #delete_file_list = list(files.values_list('file_name', flat=True))
        files.delete()
        #return delete_file_list



    def get_claim_id_from_tax_period_id(self, tax_period_id):
        claim_id = None
        try:
            claim = Claim.objects.filter(tax_period_id=tax_period_id, is_deleted=0)
            claim_id = claim.id
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claim_id

    def get_all_claims_by_period_id(self, tax_period_id, status):
        claims = Claim.objects.filter(tax_period_id=tax_period_id, is_deleted=0)
        if status:
            claims = claims.filter(status=status)
        return claims


    def get_all_user_claims_by_period_id(self, user_id, tax_period_id, status=None):
        claims = Claim.objects.filter(user_id=user_id, tax_period_id=tax_period_id, is_deleted=0)
        if status:
            claims = claims.filter(status=status)
        return claims


    def create_claim(self, claim_data):
        claim = Claim.objects.create(**claim_data)
        return claim


    def update_claim(self, claim_data, claim_id):
        return Claim.objects.filter(id=claim_id).update(**claim_data)



    def update_party(self, party_data, party_id):
        return Parties.objects.filter(id=party_id).update(**party_data)


    # def delete_claim_data(self, claim_data, claim_id):
    #     claim = None
    #     try:
    #         claim = Claim.objects.filter(id=claim_id).update(**claim_data)
    #     except Exception as err:
    #         self.__log.error(self.__exception.get_exception())
    #     return claim


    def get_all_claim_declarations(self):
        claim_declarations = None
        try:
            claim_declarations = ClaimDeclaration.objects.all()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claim_declarations


    def create_tax_period_data(self, data):
        tax_period = None
        try:
            tax_period = TaxPeriod(fin_year_id=data['fin_year_id'], claim_declaration_last_date=data['claim_declaration_last_date'], \
                                   claim_entry_last_date=data['claim_entry_last_date'], created_by=data['created_by'])
            tax_period.save()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period


    def update_tax_period_data(self, data, tax_period_id):
        tax_period = None
        try:
            tax_period = TaxPeriod.objects.filter(id=tax_period_id).update(**data)
        except Exception as err:
            print(err)
            self.__log.error(self.__exception.get_exception())
        return tax_period


    def update_finance_data(self, user_id, data_dict):
        tax_batch = None
        try:
            tax_batch = TaxBatch.objects.filter(user_id=user_id).update(**data_dict)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch


    def check_tax_period(self, financial_year_id):
        tax_period = None
        try:
            tax_period = TaxPeriod.objects.filter(fin_year_id=financial_year_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period

    def check_claim_id(self, claim_id):
        claim_data = None
        try:
            claim_data = Claim.objects.filter(id=claim_id, is_deleted=0)
            if claim_data.status != 'Under review':
                return None, 'Claim not under review'
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claim_data, 'Claim data'


    def bulk_create_finance_data(self, data, financial_year_id):
        data_dict = []

        for each_item, value in data.items():
            data_dict.append(TaxBatch(fin_year_id = value['fin_year_id'],
            user_id = value['user_id'],
            last_date = value['last_date'],
            created_by = value['created_by']
            ))

        return TaxBatch.objects.bulk_create(data_dict)


    def get_all_categories(self):
        categories = None
        try:
            categories = ClaimCategory.objects.all()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return categories


    def get_claim_declarations_by_emp_id(self, emp_id=0, tax_period_id=0):
        claims = None
        try:
            claims = ClaimDeclaration.objects.filter(is_deleted=0)
            if emp_id:
                claims = claims.filter(user_id=emp_id)
            if tax_period_id:
                claims = claims.filter(tax_period_id=tax_period_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claims


    def delete_claim_attachments_using_file_ids(self, file_ids):
        claim_attachments = ClaimAttachments.objects.filter(id__in=file_ids)
        delete_list = list(claim_attachments.values_list('file_name', flat=True))
        claim_attachments.delete()
        return delete_list


    def get_claim_declaration_by_id(self, id=0):
        declaration = ClaimDeclaration.objects.filter(id=id,is_deleted=0)
        if declaration:
            return declaration[0]
        else:
            return None

    def get_claim_declarations_status(self, id=0):
        claims = Claim.objects.all()
        if id:
            claims = claims.filter(claim_declaration_id=id,status = "Approved", is_deleted=0).exists()
        return claims



    def get_tax_batches_by_tax_period_id(self, tax_period_id):
        tax_batches = None
        try:
            tax_batches = TaxBatch.objects.filter(tax_period_id=tax_period_id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batches


    def create_claims_activity_log(self, data):
        claims_activity = None
        try:
            claims_activity = ClaimsActivity.objects.create(**data)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claims_activity



    def get_claim_declarations(self, id):
        declarations = None
        try:
            declarations = ClaimDeclaration.objects.filter(fin_year_id=id, is_deleted=0)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declarations



    def get_claim_declarations_from_declarations_id(self, declarations_id):
        claim_declarations = None
        try:
            declarations = ClaimDeclaration.objects.filter(id=declarations_id,is_deleted=0).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return declarations


    def get_claim_declarations_by_id(self, declarations_id):
        declarations = None
        declarations = ClaimDeclaration.objects.filter(id=declarations_id,is_deleted=0)
        if declarations:
            declaration = declarations[0]
        return declaration


    def create_claim_declaration(self, data):
        claim_declarations, created = ClaimDeclaration.objects.get_or_create(
            tax_period_id=data['tax_period_id'],
            user_id=data['user_id'],
            cat_id=data['cat_id'],
            is_deleted = 0,
            defaults={'created_by': data['created_by'], 'amount': data['amount']}
        )
        if not created:
            ClaimDeclaration.objects.filter(
                tax_period_id=data['tax_period_id'],
                user_id=data['user_id'],
                cat_id=data['cat_id']
            ).update(amount=F('amount') + data['amount'],created_by = data['created_by'])
        return claim_declarations

    # def edit_claim_declaration_data(self, data):
    #     ClaimDeclaration.objects.filter(
    #         tax_period_id=data['tax_period_id'],
    #         user_id=data['user_id'],
    #         cat_id=data['cat_id']
    #     ).update(amount= data['amount'])



    def update_claim_declaration(self, data, declaration_id):
        claim_declarations = ClaimDeclaration.objects.filter(id=declaration_id).update(**data)
        # claim_declarations = ClaimDeclaration.objects.filter(id=id).first()
        # if claim_declarations.is_deleted == 1:
        #     return claim_declarations
        # else:
        #     return None


    def claim_declarations_log_data(self, data):
        claims_activity = None
        try:
            claims_activity = ClaimsActivity.objects.create(**data)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claims_activity



    def get_assessment_period_by_fin_year_id(self, fin_year_id):
        tax_period = None
        try:
            tax_period = TaxPeriod.objects.filter(fin_year_id=fin_year_id, is_deleted=0)
            if tax_period:
                tax_period = tax_period.last()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period



    def get_time_period_exclude_data_by_emp_id(self, emp_id, tax_period_id):
        tax_period_exclude = None
        try:
            tax_period_exclude = TaxPeriodExclude.objects.filter()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period_exclude



    def get_logs_by_claim_id(self, claim_id):
        claims_activity = None
        try:
            claims_activity = ClaimsActivity.objects.filter(claim_id=claim_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claims_activity



    def create_tax_parties(self, data_dict):
        valid = False
        try:
            valid = Parties.objects.create(**data_dict)
        except Exception as err:
            valid = False
        return valid

    def get_parties(self, emp_id):
        return Parties.objects.filter(user_id=emp_id, is_deleted=0)

    def get_sub_categories(self, parent_id):
        claim_category = None
        try:
            claim_category = ClaimCategory.objects.filter(parent_id=parent_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return claim_category

    def get_tax_period_excludes(self, tax_period_id, user_id):
        tax_period_exclude = None
        try:
            tax_period_exclude = TaxPeriodExclude.objects.filter(tax_period_id=tax_period_id, user_id=user_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_period_exclude

    def get_id_by_fin_year_id(self, fin_year_id):
        return TaxPeriod.objects.filter(fin_year_id=fin_year_id, is_deleted=0).last()

    def get_partie_by_id(self, pk):
        return Parties.objects.filter(pk=pk, is_deleted=0).last()

    def get_claims_by_declaration_id(self, declaration_id):
        return Claim.objects.filter(claim_declaration_id=declaration_id, is_deleted=0)

    def add_claim_files(self, data):
        return ClaimAttachments.objects.create(**data)

    def get_claim_files(self, declaration_id=0, claim_id=0):
        files = ClaimAttachments.objects.all()
        if declaration_id:
            files = files.filter(claim_declaration_id=declaration_id)
        if claim_id:
            files = files.filter(claim_id=claim_id)
        return files

    # def get_claim_by_id(self, claim_id):
    #     return Claim.objects.filter(id=claim_id, is_deleted=0)


    def check_tax_batch(self, tax_batch_id):
        tax_batch = None
        try:
            tax_batch = TaxBatch.objects.filter(id=tax_batch_id, is_deleted=0).first()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch


    def bulk_create_tax_batch(self, data):
        data_dict = []
        for each_item, value in data.items():
            data_dict.append(TaxBatch(tax_period_id = value['tax_period_id'],
            user_id = value['user_id'],
            last_date_of_declaration = value['last_date_of_declaration'],
            last_date_of_claim_entry = value['last_date_of_claim_entry'],
            regime_type = value['regime_type'],
            created_by = value['created_by'],
            org_id = value['org_id'],
            ))
        return TaxBatch.objects.bulk_create(data_dict)


    def create_tax_batch(self, data):
        tax_batch = None
        try:
            tax_batch = TaxBatch.objects.create(**data)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch

    def create_or_update_tax_bacth(seld, data):
        # Check if the TaxBatch already exists based on tax_period_id and user_id
        tax_batch, created = TaxBatch.objects.get_or_create(
            tax_period_id=data['tax_period_id'],
            user_id=data['user_id'],
            org_id=data['org_id'],
            defaults=data  # Update with new data if the object is created
        )

        # If the TaxBatch already exists, update its fields with new data
        if not created:
            tax_batch.regime_type = data['regime_type']
            tax_batch.last_date_of_declaration = data['last_date_of_declaration']
            tax_batch.last_date_of_claim_entry = data['last_date_of_claim_entry']
            tax_batch.created_by = data['created_by']
            tax_batch.save()

        return tax_batch

    def delete_tax_batch_data(self, tax_batch_id):
        is_deleted = None
        try:
            is_deleted = TaxBatch.objects.filter(id=tax_batch_id).delete()
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return is_deleted


    def add_tax_batch(self, request, user_id, last_date_of_declaration, last_date_of_claim_entry, is_created):
        return TaxBatch.objects.create(
            tax_period_id=is_created,
            last_date_of_declaration=last_date_of_declaration,
            last_date_of_claim_entry=last_date_of_claim_entry,
            user_id=user_id,
            regime_type=0,
            created_by=request.user.id
        )

    def update_tax_batch(self, batch_id, data):
        tax_batch = None
        try:
            tax_batch = TaxBatch.objects.filter(id=batch_id).update(**data)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tax_batch

    def get_is_taxable_from_user_id(self, user_id, tax_period_id):
        return TaxBatch.objects.filter(user_id= user_id,tax_period_id=tax_period_id, is_deleted=0).last()

    def create_hra_details(self, _data_dict):
        return HraDetails.objects.create(**_data_dict)

    ##############################################
    # report page

    def get_all_emplyee_declarations(self, tax_period_id, emp_id):
        return ClaimDeclaration.objects.filter(tax_period_id=tax_period_id, user_id=emp_id, is_deleted=0)

    def get_claim_parties_by_party_id(self, party_ids):
        claim_parties = None
        try:
            claim_parties = Parties.objects.filter(id=party_ids, is_deleted=0).first()
        except Exception as err:
            claim_parties = None
            self.__log.error(self.__exception.get_exception())
        return claim_parties

    def get_hra_details_claim_id(self, claim_id):
        hra_details = None
        try:
            hra_details = HraDetails.objects.filter(claim_id=claim_id, proof_type = 'Receipt').first()
        except Exception as err:
            hra_details = None
            self.__log.error(self.__exception.get_exception())
        return hra_details

    def get_regime_type_by_tax_period_user_id(self,tax_period_id, user_id):
        regime_type = None
        try:
            regime_type = TaxBatch.objects.filter(tax_period_id=tax_period_id,user_id=user_id, is_deleted=0).first()
        except Exception as err:
            regime_type = None
            self.__log.error(self.__exception.get_exception())
        return regime_type


    #TDS
    def get_tds_data_from_fin_year_id(self, fin_year_id):
        tds_data = None
        try:
            tds_data = EmployeeTDS.objects.filter(fin_year_id=fin_year_id)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tds_data


    def get_employee_tds_by_fin_year_id(self, user_id, fin_year_id):
        tds_data = None
        try:
            current_month = datetime.now().month
            fin_year_months = settings.FIN_YEAR_MONTH_ORDER_LIST
            current_month_index = fin_year_months.index(current_month)
            previous_months = fin_year_months[:current_month_index]
            tds_data = EmployeeTDS.objects.filter(user_id=user_id, fin_year_id=fin_year_id, month_id__in=previous_months)
        except Exception as err:
            self.__log.error(self.__exception.get_exception())
        return tds_data


    def get_tax_batch_by_period_and_user(self, tax_period_id, user_id):
        tax_batch = TaxBatch.objects.filter(tax_period_id=tax_period_id, user_id=user_id, is_deleted=0).first()
        return tax_batch


    #TODO remove this method
    def get_all_details_from_ctc(self):
        ctc_details = CtcMaster.objects.filter(is_deleted=0).all()
        return ctc_details

    def get_ctc_master(self):
        ctc_details = CtcMaster.objects.filter(is_deleted=0).all()
        return ctc_details


    def get_all_details_from_ctc_emp(self):
        ctc_emp_details = CtcEmployee.objects.filter(is_deleted=0)
        return ctc_emp_details

    def get_all_employees_ctc_by_fin_year(self, fin_yr_id):
        ctc_emp_details = CtcEmployee.objects.filter(is_deleted=0, fin_yr_id=fin_yr_id)
        return ctc_emp_details

    def get_emp_ctc_by_user_id_and_fin_yr(self, user_id, fin_yr_id):
        ctc_emp_details = CtcEmployee.objects.filter(is_deleted=0, emp_id=user_id, fin_yr_id=fin_yr_id)
        return ctc_emp_details


    def bulk_create_ctc_employee(self,ctc_emp_data):
        bulk_data = []
        try:
            for each in ctc_emp_data:
                bulk_data.append(
                    CtcEmployee(
                        fin_yr_id = each['fin_yr_id'],
                        emp_id = each['emp_id'],
                        ctc_id = each['ctc_id'],
                        amount = each['amount'],
                        created_by = each['created_by']
                    )
                )
            ctc_employee = CtcEmployee.objects.bulk_create(bulk_data)
        except :
            ctc_employee = False

        return ctc_employee


    def update_employee_ctc(self, ctc_amounts):
        for each_ctc in ctc_amounts:
            try:
                CtcEmployee.objects.filter(emp_ctc_id=each_ctc['emp_ctc_id']).update(amount=each_ctc['amount'])
            except:
                continue



    def get_tds_by_id(self, tds_id):
        try:
            tds_data = EmployeeTDS.objects.filter(id=tds_id).first()
        except Exception as err:
            tds_data = None
        return tds_data


    def bulk_update_tds_data(self, update_list):
        is_updated = False
        for each in update_list:
            EmployeeTDS.objects.filter(month_id=each['month_id'], fin_year_id=each['fin_year_id'], user_id=each['user_id']).update(amount=each['amount'])
        is_updated = True
        return is_updated


    def update_tds_data(self, data_dict):
        return EmployeeTDS.objects.filter(id=data_dict['id']).update(amount=data_dict['amount'])


    def delete_tds_by_fin_year_id(self, fin_year_id):
        return EmployeeTDS.objects.filter(fin_year_id=fin_year_id).delete()


    def delete_individual_tds_by_fin_year_id(self, user_id, fin_year_id):
        return EmployeeTDS.objects.filter(user_id=user_id, fin_year_id=fin_year_id).delete()


    def get_employee_ctc(self, emp_id, fin_yr_id):
        emp_ctc = CtcEmployee.objects.filter(emp_id=emp_id, fin_yr_id=fin_yr_id, is_deleted=0)
        return emp_ctc

    def get_ctc_employee_data_by_emp_id_fin_year_id(self, fin_year_id, emp_id):
        return CtcEmployee.objects.filter(fin_yr_id=fin_year_id, emp_id=emp_id)


    def get_employee_actual_hra_by_fin_year_id(self, emp_id, fin_year_id):
        return CtcEmployee.objects.filter(fin_yr_id=fin_year_id, emp_id=emp_id, ctc_id=2)

    def get_all_subcategories_by_cat_id(self, cat_id):
        return ClaimCategory.objects.filter(parent_id=cat_id)

    def get_employee_tax_deduction_by_emp_id_fin_year_id(self, fin_year_id, emp_id):
        return EmployeeTaxDeduction.objects.filter(fin_year_id=fin_year_id, emp_id=emp_id)

    def get_other_income_and_deduction(self, fin_year_id, emp_id, section):
        return EmployeeTaxDeduction.objects.filter(fin_year_id=fin_year_id, emp_id=emp_id, section=section)


    def get_employee_tax_deduction_by_fin_year_id(self, fin_year_id, user_id=0):
        if user_id:
            return EmployeeTaxDeduction.objects.filter(fin_year_id=fin_year_id, emp_id=user_id)
        return EmployeeTaxDeduction.objects.filter(fin_year_id=fin_year_id)


    def create_other_income_deduction(self, tax_deduct_data):
        is_created = EmployeeTaxDeduction.objects.create(**tax_deduct_data)
        return is_created

    def update_other_income_deduction(self,tax_deduct_data):
        is_updated = False
        is_updated = EmployeeTaxDeduction.objects.filter(
            emp_id=tax_deduct_data['emp_id'], fin_year_id=tax_deduct_data['fin_year_id'],
            codename=tax_deduct_data['codename']).update(amount=tax_deduct_data['amount'])
        return is_updated


    def delete_tax_deduction_data(self,tax_deduct_data):
        is_deleted = False
        tax_deduction = EmployeeTaxDeduction.objects.filter(
            emp_id=tax_deduct_data['emp_id'], fin_year_id=tax_deduct_data['fin_year_id'],
            codename=tax_deduct_data['codename'])
        tax_deduction.delete()
        is_deleted = True
        return is_deleted