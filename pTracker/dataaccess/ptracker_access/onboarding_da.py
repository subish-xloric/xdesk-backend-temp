from django.db.models import Q
from pTracker.dataaccess.ptracker_access.onboarding_models import KYCDocumentTypes, KYCDocuments, TechnicalAndNonTechnicalSkills, UserAcademicDetails, WorkExperience, onBoardingCandidate


class OnboardingDA():
    def __init__(self):
        pass

    def get_onboarding_candidate_by_email_or_phone(self, phone, email):
        return onBoardingCandidate.objects.filter(Q(email=email)| Q(phone=phone),is_deleted=0)

    def create_new_candidate(self, candidate_data_dict):
        return onBoardingCandidate.objects.create(**candidate_data_dict)

    def get_all_onboarding_candidates(self):
        return onBoardingCandidate.objects.filter(is_deleted=0).order_by('-candidate_id')

    def get_onboarding_candidate_by_candidate_id(self, candidate_id):
        candidates =onBoardingCandidate.objects.filter(is_deleted=0, candidate_id = candidate_id)
        if candidates:
            return candidates[0]
        return None

    def update_onboarding_candidate(self, update_data, candidate_id):
        return onBoardingCandidate.objects.filter(candidate_id = candidate_id).update(**update_data)

    def get_onboarding_candidate_by_onboarding_code(self, onboarding_code):
        return onBoardingCandidate.objects.filter(is_deleted=0, onboarding_code = onboarding_code)

    def get_all_kyc_doc_types(self):
        return KYCDocumentTypes.objects.all()

    def deltete_onboarding_candidate(self, candidate_id):
        return onBoardingCandidate.objects.filter(candidate_id = candidate_id).delete()


    def create_employee_work_experience(self, create_data):
        return WorkExperience.objects.create(**create_data)

    def create_employee_academic_details(self, create_data):
        return UserAcademicDetails.objects.create(**create_data)

    def create_employee_kyc_documents(self, create_data):
        return KYCDocuments.objects.create(**create_data)

    def create_employee_skills(self, create_data):
        return TechnicalAndNonTechnicalSkills.objects.create(**create_data)

    def get_kyc_details_by_emp_id(self, emp_id):
        return KYCDocuments.objects.filter(emp_id = emp_id)

    def get_work_experiences_by_emp_id(self, emp_id):
        return WorkExperience.objects.filter(emp_id = emp_id)

    def get_educational_details_by_emp_id(self,emp_id):
        return UserAcademicDetails.objects.filter(emp_id = emp_id)

    def get_skills_by_emp_id(self, emp_id):
        return TechnicalAndNonTechnicalSkills.objects.filter(emp_id = emp_id)

    def delete_kyc_document(self, kyc_id):
        file_name =''
        kyc_list = KYCDocuments.objects.filter(id = kyc_id)
        if kyc_list:
            file_name = kyc_list[0].kyc_document
            kyc_list.delete()
        return file_name


    def get_wrk_experience_by_id(self, wrk_exp_id):
        wrk_exp_list = WorkExperience.objects.filter(id = wrk_exp_id)
        if wrk_exp_list:
            return wrk_exp_list[0]
        else:
            return None


    def delete_wrk_experience(self, wrk_exp_id):
       return WorkExperience.objects.filter(id = wrk_exp_id).delete()

    def get_edu_details_by_list_of_id(self, deleted_educational_details):
        return UserAcademicDetails.objects.filter(id__in = deleted_educational_details)

    def delete_edu_details_by_list_of_id(self, deleted_educational_details):
        return UserAcademicDetails.objects.filter(id__in = deleted_educational_details).delete()

    def delete_skill_by_list_of_id(self, skill_id_list):
        return TechnicalAndNonTechnicalSkills.objects.filter(id__in = skill_id_list).delete()
