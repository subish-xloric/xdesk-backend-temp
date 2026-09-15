from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.asset_da import AssetDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA

from pTracker.common.logs import Logs
from pTracker.common.utility import Utility
from pTracker.common.exception_handler import ExceptionHandler

from django.conf import Settings, settings

from datetime import datetime

class AssetCategoryBL():

    def __init__(self):
        self.__log = Logs()
        self.__exception = ExceptionHandler()
        self.__utility = Utility()



    def create_or_update_asset_category(self, user, data):
        objAsset = AssetDA()
        objUser = UserDA()
        response = {'error' : '', 'success' : ''}
        temp_data = {}
        try:

            #TODO permissions to be set user based
            userID = user.id
            roleID, roleName = objUser.get_user_role_by_id(userID)

            if roleID not in (1, "1", 2, "2"):
                response['error'] = "You have no permission to create or update asset category details"
                return response

            categoryID = data.get('categoryID',0)
            temp_data['name'] = data.get('category_name','')
            temp_data['description'] = data.get('description','')
            # temp_data['create_date_time'] = data.get('create_data_time',None)
            temp_data['created_by'] = userID
            temp_data['parent_categoryID'] = data.get('parent_category',0)

            if categoryID:
                is_categoryID = objAsset.get_asset_category(categoryID)

                if not is_categoryID:
                    response['error'] = "No category found in this ID"
                    return response
                result = objAsset.update_asset_category(categoryID, temp_data)
                response['action'] = 'update'
            else:
                temp_data['create_date_time'] = datetime.now()
                result = objAsset.create_asset_category(temp_data)
                response['action'] = 'create'

            if result:
                if response['action'] == 'create':
                    response['success'] = True
                    response['message'] = "Asset category created successfully"
                else:
                    response['success'] = True
                    response['message'] = "Asset category updated successfully"
            else:
                if response['action'] == 'create':
                    response['error'] = "Asset category creation failed"
                else:
                    response['error'] = "Asset category updation failed"

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response



    def delete_asset_category(self, user, categoryID):
        objAsset = AssetDA()
        objUser = UserDA()
        response = {'error' : '', 'success' : ''}

        try:
            #TODO permissions to be set user based
            userID = user.id
            roleID, roleName = objUser.get_user_role_by_id(userID)

            if roleID not in (1, "1", 2, "2"):
                response['error'] = "You have no permission to delete asset category"
                return response

            is_categoryID = objAsset.get_asset_category(categoryID)

            if not is_categoryID:
                response['error'] = "No category found"
                return response

            sub_categories = objAsset.get_sub_asset_category_by_parentID(categoryID)

            if sub_categories:
                response['error'] = "You cannot delete this category as it is parent to other categorie(s)"
                return response

            #TODO need to check  item

            result = objAsset.delete_asset_category(categoryID)

            if result:
                response['success'] = True
                response['message'] = "Asset category deleted successfully"
            else:
                response['error'] = "Asset category deletion failed"

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response



    def get_asset_category_all(self,user):
        objAsset = AssetDA()
        objUser = UserDA()
        temp_result = {}
        data = []
        response = {'error' : '', 'success' : ''}
        try:
            #TODO permissions to be set user based
            userID = user.id
            roleID, roleName = objUser.get_user_role_by_id(userID)

            if roleID not in (1, "1", 2, "2"):
                response['error'] = "You have no permission to view the asset category list"
                return response
            asset_category = objAsset.get_asset_category()

            asset_cat_dict = { category.categoryID : {'name': category.name } for category in asset_category }

            if not asset_category:
                response['error'] = "No asset categories found"
                return response

            for eachItem in asset_category:
                temp_result = {}
                temp_result['asset_categoryID'] = eachItem.categoryID
                temp_result['name'] = eachItem.name
                temp_result['description'] = eachItem.description
                temp_result['create_date_time'] = eachItem.create_date_time.strftime('%Y-%m-%d') if eachItem.create_date_time else None
                temp_result['parent_categoryID'] = eachItem.parent_categoryID
                if not eachItem.parent_categoryID == 0:
                    temp_result['parent_category_name'] = asset_cat_dict[eachItem.parent_categoryID]['name']
                else:
                    temp_result['parent_category_name'] = 'N/A'

                data.append(temp_result)
            response['data'] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response



    def get_parent_asset_category(self,user):
        objAsset = AssetDA()
        objUser = UserDA()
        temp_result = {}
        data = []
        response = {'error' : '', 'success' : ''}

        try:
            #TODO permissions to be set user based
            userID = user.id
            roleID, roleName = objUser.get_user_role_by_id(userID)

            if roleID not in (1, "1", 2, "2"):
                response['error'] = "You have no permission to view the asset category list"
                return response
            asset_category = objAsset.get_asset_category()

            if not asset_category:
                response['error'] = "No asset categories Found"
                return response

            for eachRow in asset_category:
                temp_result = {}
                temp_result['asset_categoryID'] = eachRow.categoryID
                temp_result['name'] = eachRow.name
                temp_result['description'] = eachRow.description
                temp_result['create_date_time'] = eachRow.create_date_time if eachRow.create_date_time else None
                temp_result['parent_categoryID'] = eachRow.parent_categoryID
                data.append(temp_result)

            data = list(sorted(data, key=lambda x: x['create_date_time'], reverse=True))

            response['data'] = data

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response



    def get_sub_asset_category_by_parentID(self, user, data):
        objAsset = AssetDA()
        objUser = UserDA()
        response = {'error' : '', 'success' : ''}
        sub_data = []
        try:
            #TODO permissions to be set user based
            userID = user.id
            parentID = data.get('parent_categoryID', 0)
            roleID, roleName = objUser.get_user_role_by_id(userID)

            if roleID not in (1, "1", 2 ,"2"):
                response['error'] = "You have no permission to view sub asset category list"
                return response

            is_parentID = objAsset.get_asset_category(parentID)
            if not is_parentID:
                response['error'] = "No parent asset category found in this ID"
                return response

            sub_category = objAsset.get_sub_asset_category_by_parentID(parentID)
            if not sub_category:
                response['error'] = "No sub asset category found in the ID"
                return response

            for eachAsset in sub_category:
                temp_result = {}
                temp_result['categoryID'] = eachAsset.categoryID
                temp_result['name'] = eachAsset.name
                temp_result['description'] = eachAsset.description
                temp_result['create_date_time'] = eachAsset.create_date_time.strftime('%Y-%m-%d') if eachAsset.create_date_time else None
                temp_result['parent_categoryID'] = eachAsset.parent_categoryID
                sub_data.append(temp_result)
            response['data'] = sub_data

        except Exception as err:
            response["error"] = settings.ERROR_MSG['application_error']\
                .format(str(err), self.__log.error(self.__exception.get_exception()))
        return response













