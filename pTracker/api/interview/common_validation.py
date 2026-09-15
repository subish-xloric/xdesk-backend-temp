import re

class CommonValidation():
    def __init__(self):
        pass

    def is_empty(self, value):
        is_empty = False
        if value.isspace():
            is_empty = True
        return is_empty


    def clean_integer(self, value):
        try:
            return int(value)
        except ValueError:
            return 0

    def is_alpha(self, value):
        if value.isalpha():
            return True
        else:
            return False

    def is_mobile_number(self, value):
        if len(value) > 10 or len(value) < 10:
            return False
        else:
            return True

    def is_email(self, email):
        """Validate email address using regex"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_is_integer(self, value):

        # if  isinstance(value, int):
        #     return True
        # else:
        #     return False
        isInteger = True
        try:
            int(value)
        except ValueError:
            isInteger = False
        return isInteger

    def validate_string_length(self, stringValue, min, max):
        if len(stringValue) < min or len(stringValue) > max:
            return False
        else:
            return True

    def validate_is_alpha_numeric(self, value):
        if value.isalnum():
            return True
        else:
            return False

    def validate_is_alpha_numeric_with_special_characters(self, value, characters=[]):
        flag = True
        # pattern = '^[a-zA-Z0-9\s&,.(_)-]$'
        for each in value:
            if each.isalpha() or each.isdigit() or each.isspace():
                continue
            else:
                if each not in characters:
                    flag = False
                    break
        return flag










