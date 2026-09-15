from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.asset_da import AssetDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA

class VendorBL():

    def __init__(self):
        pass

    def create_or_update_vendor(self,userID,data):
        objUtility = Utility()
        objAsset =AssetDA()
        objUser = UserDA()
        vendor_data = {}
        response = {"error" : "" , "success" : ""}
        try:
            roleID , roleName = objUser.get_user_role_by_id(userID)
            if roleID not in(1 ,"1" , 2 , "2"):
                response['error'] = "You have no permission to create or update the Vendor Details"
                return response

            vendorID = data.get('vendorID' , 0)
            vendor_data['name'] = data.get('name','')
            vendor_data['addressLine1'] = data.get('addressLine1','')
            vendor_data['addressLine2'] = data.get('addressLine2' , '')
            vendor_data['addressLine3'] = data.get('addressLine3','')
            vendor_data['contactPersonName'] = data.get('contactPersonName' ,'')
            vendor_data['email'] = data.get('email' , '')
            vendor_data['phone'] = data.get('phone' , '')
            vendor_data['mobile'] = data.get('mobile' , '')
            vendor_data['website'] = data.get('website','')
            
            if vendorID:
                is_vendor = objAsset.get_vendor_details(vendorID)
                if not is_vendor:
                    response['error'] = "No vendor found in this ID"
                    return response
                result = objAsset.update_vendor(vendorID,vendor_data)
                response['action'] = 'update'
            else:
                result = objAsset.create_vendor(vendor_data)
                response['action'] = 'create'

            if result:
                if response['action'] == 'create':
                    response['success'] = "Vendor created successfully"
                else:
                    response['success'] = "Vendor updated successfully"
            return response
        except Exception as error:
            objUtility.log("Error in the method create_or_update_vendor in the class VendorBL,\
                                Error is : {0} ".format(str(error)))
            msg = str(error)
            response['error'] = msg
            return response
        
    def get_all_vendor(self,user):
        objUtility = Utility()
        objAsset =AssetDA()
        objUser = UserDA()
        response = {"error" : "", "success" : "" , "data" : ""}
        data = []
        try:
            userID = user.id
            roleID , roleName = objUser.get_user_role_by_id(userID)
            if roleID not in (1,"1",2,"2"):
                response['error'] = "You have no permission to view Vendor details"
                return response
            result = objAsset.get_vendor_details()
            if result:
                for eachVendor in result:
                    temp_result = {}
                    temp_result['vendorID'] = eachVendor.vendorID
                    temp_result['name'] = eachVendor.name
                    temp_result['addressLine1'] = eachVendor.addressLine1
                    temp_result['addressLine2'] = eachVendor.addressLine2
                    temp_result['addressLine3'] = eachVendor.addressLine3
                    temp_result['contactPersonName'] = eachVendor.contactPersonName
                    temp_result['email'] = eachVendor.email
                    temp_result['phone'] = eachVendor.phone
                    temp_result['mobile'] = eachVendor.mobile
                    temp_result['website'] = eachVendor.website
                    data.append(temp_result)
                response['data'] = data
            return response
        except Exception as error:
            objUtility.log("Error in the method get_all_vendor in the class VendorBL, \
                                Error is : {0} ".format(str(error)))
            msg = str(error)
            response['error'] = msg
            return response


    def delete_vendor(self,user,vendorID):
        objUtility = Utility()
        objAsset =AssetDA()
        objUser = UserDA()
        response={"error" : "", "success" : ""}
        try:
            userID = user.id
            roleID , roleName = objUser.get_user_role_by_id(userID)
            vendorID = vendorID
            is_vendor = objAsset.get_vendor_details(vendorID)
            if roleID not in (1,"1",2,"2"):
                response['error'] =  "You have no permission to delete Vendor details"
                return response
            if not is_vendor:
                response['error'] = "No vendor found in this ID"
                return response
            result = objAsset.delete_vendor(vendorID)
            if result:
                response['success'] = "Vendor deleted successfully"
            return response
        except Exception as error:
            objUtility.log("Error in the method delete_vendor in the class VendorBL, \
                                Error is : {0} ".format(str(error)))
            msg = str(error)
            response['error'] = msg
            return response
        





    



                        





