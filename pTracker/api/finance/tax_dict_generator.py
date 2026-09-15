from django.conf import settings

from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler
from pTracker.common.logs import Logs
from pTracker.dataaccess.ptracker_access.tax_da import TaxDA


class TaxDictGenerator():
    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()
        self.__tax_da = TaxDA()


    def get_gross_salary_sec_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            total = amounts['gross_salary_sec_17_1'] + amounts['perquisites_value_sec_17_2'] + amounts['profits_lieu_sec_17_3']
            data = {
                'serial_number': '1.',
                'desc' : 'Gross Salary',
                'sub_items' : {
                            1 : {
                                'serial_number': '(a)',
                                'desc' : 'Salary as per provisions contained in section 17(1)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['gross_salary_sec_17_1']:.2f}",
                                'deductable_amount' : '',
                            },
                            2 : {
                                'serial_number': '(b)',
                                'desc' : 'Value of perquisites under section 17(2) (as per Form No.12BA, wherever applicable)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['perquisites_value_sec_17_2']:.2f}",
                                'deductable_amount' : '',
                            },
                            3 : {
                                'serial_number': '(c)',
                                'desc' : 'Profits in lieu of salary under section 17(3) (as per Form No.12BA, wherever applicable)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['profits_lieu_sec_17_3']:.2f}",
                                'deductable_amount' : '',
                            },
                            4 : {
                                'serial_number': '(d)',
                                'desc' : 'Total',
                                'gross_amount' : '',
                                'qualifying_amount' : '',
                                'deductable_amount' : f"{total:.2f}",
                            },
                            5 : {
                                'serial_number': '(e)',
                                'desc' : 'Reported total amount of salary received from other employer(s)',
                                'gross_amount' : '',
                                'qualifying_amount' : '',
                                'deductable_amount' : f"{amounts['reported_total_salary_from_other_employer']:.2f}",
                            }
                    }
                }
            response["data"] = data
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_allowances_extent_exempt_sec_10_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '2.',
                'desc' : 'Less : Allowances to the extent exempt under section 10',
                'sub_items' : {
                            1 : {
                                'serial_number': '(a)',
                                'desc' : 'Travel concession or assistance under section 10(5)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['travel_concession_sec_10_5']:.2f}",
                                'deductable_amount' : '',
                            },
                            2 : {
                                'serial_number': '(b)',
                                'desc' : 'Death-cum-retirement gratuity under section 10(10)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['gratuity_sec_10_10']:.2f}",
                                'deductable_amount' : '',
                            },
                            3 : {
                                'serial_number': '(c)',
                                'desc' : 'Commuted value of pension under section 10(10A)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['pension_sec_10_10_a']:.2f}",
                                'deductable_amount' : '',
                            },
                            4 : {
                                'serial_number': '(d)',
                                'desc' : 'Cash equivalent of leave salary encashment under section 10(10AA)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['leave_salary_encashment_sec_10_10_aa']:.2f}",
                                'deductable_amount' : '',
                            },
                            5 : {
                                'serial_number': '(e)',
                                'desc' : 'House rent allowance under section 10(13A)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['hra_exemption_sec_10_13_a']:.2f}",
                                'deductable_amount' : '',
                            },
                            6 : {
                                'serial_number': '(f)',
                                'desc' : 'Amount of any other exemption under section 10',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['other_exemption_sec_10']:.2f}",
                                'deductable_amount' : '',
                            },
                            # 7 : {
                            #     'serial_number': '(g)',
                            #     'desc' : 'Total amount of any other exemption under section 10',
                            #     'gross_amount' : '',
                            #     'qualifying_amount' : '',
                            #     'deductable_amount' : f"{float(amounts['total_other_exemption_sec_10']):.2f}",
                            # },
                            8 : {
                                'serial_number': '(h)',
                                'desc' : 'Total amount of exemption claimed under section 10 [2(a)+2(b)+2(c)+2(d)+2(e)+2(f)]',
                                'gross_amount' : '',
                                'qualifying_amount' : '',
                                'deductable_amount' : f"{float(sum(list(amounts.values()))):.2f}",
                            }
                    }
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response



    def get_total_salary_amount_from_current_employer_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '3.',
                'desc' : 'Total amount of salary received from current employer [1(d)-2(h)]',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(amounts['gross_total'] - amounts['allowances_sec_10_total']):.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_deductions_sec_16_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '4.',
                'desc' : 'Less: Deductions under section 16',
                'sub_items' : {
                            1 : {
                                'serial_number': '(a)',
                                'desc' : 'Standard deduction under section 16(ia)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['standard_deduction_sec_16_ia']:.2f}",
                                'deductable_amount' : '',
                            },
                            2 : {
                                'serial_number': '(b)',
                                'desc' : 'Entertainment allowance under section 16(ii)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['entertainment_allowance_sec_16_ii']:.2f}",
                                'deductable_amount' : '',
                            },
                            3 : {
                                'serial_number': '(c)',
                                'desc' : 'Tax on employment under section 16(iii)',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['employment_tax_sec_16_iii']:.2f}",
                                'deductable_amount' : '',
                            },
                        },
                    }
            response["data"] = data
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_total_deductions_sec_16_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '5.',
                'desc' : 'Total amount of deductions under section 16 [4(a)+4(b)+4(c)]',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(sum(list(amounts.values()))):.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_income_interchangeable_under_head_salaries_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            deductable_amount = amounts['salary_from_current_employer'] + amounts['gross_salary'] - amounts['total_deductions_sec_16']
            data = {
                'serial_number': '6.',
                'desc' : 'Income chargeable under the head "Salaries" [(3+1(e)-5]',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{deductable_amount:.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_other_income_reported_by_employee_under_sec_192_2B_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '7.',
                'desc' : 'Add: Any other income reported by the employee under as per section 192 (2B)',
                'sub_items' : {
                            1 : {
                                'serial_number': '(a)',
                                'desc' : 'Income (or admissible loss) from house property reported by employee offered for TDS',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['house_property_income']:.2f}",
                                'deductable_amount' : '',
                            },
                            2 : {
                                'serial_number': '(b)',
                                'desc' : 'Income under the head Other Sources offered for TDS',
                                'gross_amount' : '',
                                'qualifying_amount' : f"{amounts['head_other_sources_income']:.2f}",
                                'deductable_amount' : '',
                            },
                        },
                    }
            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_total_other_income_reported_by_employee_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '8.',
                'desc' : 'Total amount of other income reported by the employee [7(a)+7(b)]',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(sum(list(amounts.values()))):.2f}",
                'sub_items' : None
                }
            response["data"] = data
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_gross_total_income_details_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '9.',
                'desc' : 'Gross total income (6+8)',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(sum(list(amounts.values()))):.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_deductions_under_chapter_vi_a_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '10.',
                'desc' : 'Deductions under Chapter VI-A',
                'column_1': 'Gross',
                'column_2': 'Qualifying',
                'column_3': '',
                'not_amount_bold': True,
                'sub_items' : {
                            1 : {
                                'serial_number': '(a)',
                                'desc' : 'Deduction in respect of life insurance premia, contributions to provident fund etc. under section 80C',
                                'gross_amount' : f"{amounts['deduction_sec_80_c']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_c']:.2f}",
                                'deductable_amount' : "",
                            },
                            2 : {
                                'serial_number': '(b)',
                                'desc' : 'Deduction in respect of contribution to certain pension funds under section 80CCC',
                                'gross_amount' : f"{amounts['deduction_sec_80_ccc']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_ccc']:.2f}",
                                'deductable_amount' : "",
                            },
                            3 : {
                                'serial_number': '(c)',
                                'desc' : 'Deduction in respect of contribution by taxpayer to pension scheme under section 80CCD (1)',
                                'gross_amount' : f"{amounts['deduction_sec_80_ccd_1']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_ccd_1']:.2f}",
                                'deductable_amount' : "",
                            },
                            4 : {
                                'serial_number': '(d)',
                                'desc' : 'Total deduction under section 80C, 80CCC and 80CCD (1)',
                                'gross_amount' : '',
                                'qualifying_amount' : '',
                                'deductable_amount' : f"{float(amounts['deduction_sec_80_c'] + amounts['deduction_sec_80_ccc'] + amounts['deduction_sec_80_ccd_1']):.2f}",
                            },
                            5 : {
                                'serial_number': '(e)',
                                'desc' : 'Deductions in respect of amount paid/deposited to notified pension scheme under section 80CCD (1B)',
                                'gross_amount' : f"{amounts['deduction_sec_80_ccd_1b']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_ccd_1b']:.2f}",
                                'deductable_amount' : "",
                            },
                            6 : {
                                'serial_number': '(f)',
                                'desc' : 'Deduction in respect of contribution by Employer to pension scheme under section 80CCD (2)',
                                'gross_amount' : f"{amounts['deduction_sec_80_ccd_2']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_ccd_2']:.2f}",
                                'deductable_amount' : "",
                            },
                            7 : {
                                'serial_number': '(g)',
                                'desc' : 'Deduction in respect of health insurance premia under section 80D',
                                'gross_amount' : f"{amounts['deduction_sec_80_d']}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_d']}",
                                'deductable_amount' : "",
                            },
                            8 : {
                                'serial_number': '(h)',
                                'desc' : 'Deduction in respect of interest on loan taken for higher education under section 80E',
                                'gross_amount' : f"{amounts['deduction_sec_80_e']}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_e']}",
                                'deductable_amount' : "",
                            },
                            9 : {
                                'serial_number': '(i)',
                                'desc' : 'Total Deduction in respect of donations to certain funds, charitable institutions, etc. under section 80G',
                                'gross_amount' : f"{amounts['deduction_sec_80_g']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_g']:.2f}",
                                'deductable_amount' : "",
                            },
                            10 : {
                                'serial_number': '(j)',
                                'desc' : 'Deduction in respect of interest on deposits in savings account under section 80TTA',
                                'gross_amount' : f"{amounts['deduction_sec_80_tta']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_tta']:.2f}",
                                'deductable_amount' : "",
                            },
                            11 : {
                                'serial_number': '(k)',
                                'desc' : 'Amount deductible under any other provision(s) of Chapter VI-A',
                                'sub_items' : '',
                            },
                            12 : {
                                'serial_number': '(l)',
                                'desc' : 'Total of amount deductible under any other provision(s) of Chapter VI-A',
                                'gross_amount' : f"{amounts['other_provisions_chapter_vi_a']:.2f}",
                                'qualifying_amount' : f"{amounts['other_provisions_chapter_vi_a']:.2f}",
                                'deductable_amount' : "",
                            },
                            13 : {
                                'serial_number': '(m)',
                                'desc' : 'Interest on Home Loan for Affordable Home, Auto Loan for Electronic Vehicle',
                                'gross_amount' : f"{amounts['deduction_sec_80_eea']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_eea']:.2f}",
                                'deductable_amount' : "",
                            },
                            14 : {
                                'serial_number': '(n)',
                                'desc' : 'Interest on Auto Loan for Electronic Vehicle',
                                'gross_amount' : f"{amounts['deduction_sec_80_eeb']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_eeb']:.2f}",
                                'deductable_amount' : "",
                            },
                            15 : {
                                'serial_number': '(o)',
                                'desc' : 'Medical treatment for handicapped dependent or payment to specified scheme for \nmaintenance of handicapped dependent  ',
                                'gross_amount' : f"{amounts['deduction_sec_80_dd']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_dd']:.2f}",
                                'deductable_amount' : "",
                                'two_line' : True,
                            },
                            16 : {
                                'serial_number': '(p)',
                                'desc' : 'Medical Expenditure on Self or Dependent Relative for diseases specified in Rule 11DD  ',
                                'gross_amount' : f"{amounts['deduction_sec_80_ddb']:.2f}",
                                'qualifying_amount' : f"{amounts['deduction_sec_80_ddb']:.2f}",
                                'deductable_amount' : "",
                            },
                        },
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_aggregate_deductable_income_chapter_vi_a_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '11.',
                'desc' : 'Aggregate of deductible amount under Chapter VI-A [10(a)+10(b)+10(c)+10(e)+10(f)+10(g) \n+10(h)+10(i)+10(j)+10(l)+10(m)+10(n)+10(o)+10(p)]',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(sum(list(amounts.values()))):.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    # def get_total_taxable_income_dict(self, **amounts):
    #     response = {"error": None, "data":{}}
    #     try:
    #         data = {
    #             'serial_number': '13.',
    #             'desc' : 'Tax on total income',
    #             'gross_amount' : '',
    #             'qualifying_amount' : '',
    #             'deductable_amount' : amounts['gross_total_income'] - amounts['aggregate_deductable_amount'],
    #             'sub_items' : None
    #             }

    #         response["data"] = data

    #     except Exception as err:
    #         response["error"] = settings.ERROR_MSG["application_error"].format(
    #             str(err), self.__log.error(self.__exception.get_exception())
    #         )
    #     return response


    def get_tax_total_income_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: self.__get_custom_round(value) for key, value in amounts.items()}
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '13.',
                'desc' : 'Tax on total income',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amounts['tax_total_income']:.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_rebate_sec_87_a_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '14.',
                'desc' : 'Rebate under section 87A, if applicable',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amounts['rebate_sec_87_a']:.2f}",
                'sub_items' : None
                }
            response["data"] = data
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_surcharge_dict(self, surcharge):
        response = {"error": None, "data":{}}
        try:
            surcharge = self.__get_custom_round(surcharge)
            data = {
                'serial_number': '15.',
                'desc' : 'Surcharge, wherever applicable',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(surcharge):.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_health_education_cess_dict(self, health_education_cess):
        response = {"error": None, "data":{}}
        try:
            health_education_cess = self.__get_custom_round(health_education_cess)
            data = {
                'serial_number': '16.',
                'desc' : 'Health and education cess',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(health_education_cess):.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_tax_payable_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            amt = amounts['tax_total_income'] + amounts['surcharge'] + amounts['health_education_cess'] - amounts['rebate_sec_87_a']
            amt = self.__get_custom_round(amt)
            if amt <= 0:
                amt = 0
            data = {
                'serial_number': '17.',
                'desc' : 'Tax payable (13+15+16-14)',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amt:.2f}",
                #'deductable_amount' : 0,
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_relief_sec_89_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '18.',
                'desc' : 'Less: Relief under section 89 (attach details)',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amounts['relief_sec_89']:.2f}",
                'sub_items' : None
                }
            response["data"] = data
        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_net_tax_payable_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            amt = amounts['tax_payable'] - amounts['relief_sec_89']
            amt = self.__get_custom_round(amt)
            data = {
                'serial_number': '19.',
                'desc' : 'Net tax payable (17-18)',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{float(amt):.2f}",
                'sub_items' : None,
                'amount_bold': True,
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_tax_paid_till_now_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '20.',
                'desc' : 'Tax paid till now',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amounts['tds_sum']:.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_remaining_tax_to_be_paid_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            amt = amounts['net_tax_payable'] - amounts['tax_paid_till_now']
            amt = self.__get_custom_round(amt)
            data = {
                'serial_number': '21.',
                'desc' : 'Remaining tax to be paid',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amt:.2f}",
                'sub_items' : None,
                'amount_bold': True,
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_estimated_tds_to_be_deducted_in_future_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            amt = amounts['remaining_tax_to_be_paid']/amounts['remaining_month_count']
            amt = self.__get_custom_round(amt)
            data = {
                'serial_number': '22.',
                'desc' : 'Projected TDS deductions for upcoming months',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amt:.2f}",
                'sub_items' : None,
                'amount_bold': True,
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def get_total_taxable_income_dict(self, **amounts):
        response = {"error": None, "data":{}}
        try:
            amounts = {key: float(value) for key, value in amounts.items()}
            data = {
                'serial_number': '12.',
                'desc' : 'Total taxable income (9-11)',
                'gross_amount' : '',
                'qualifying_amount' : '',
                'deductable_amount' : f"{amounts['gross_total_income'] - amounts['aggregate_deductable_amount']:.2f}",
                'sub_items' : None
                }

            response["data"] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG["application_error"].format(
                str(err), self.__log.error(self.__exception.get_exception())
            )
        return response


    def __get_custom_round(self, num):
        num = float(num)
        integer_part = int(num)
        decimal_part = num - integer_part

        if decimal_part < 0.5:
            return integer_part
        else:
            return integer_part + 1