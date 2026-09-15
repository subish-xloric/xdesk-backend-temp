from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.asset_da import AssetDA
from pTracker.dataaccess.ptracker_access.user_da import UserDA
from django.conf import settings

class AssetBL():

    def __init__(self):
        pass

    def create_or_update_purchase_order(self,data,user):
        objAsset = AssetDA()
        objUtility = Utility()
        objUser = UserDA()
        response = {}
        purchase_data = {}
        try:
            userID = user.id
            roleID , roleName = objUser.get_user_role_by_id(userID)
            if roleID in (2 , '2'):
                purchaseID = data.get('poID',0)
                purchase_data['companyID'] = data.get('companyID',0)
                purchase_data['vendorID'] = data.get('vendorID',0)
                purchase_data['purchaseNo'] = data.get('purchaseNo',0)
                purchase_data['poDate'] = data.get('poDate',"")
                purchase_data['shippingAddress'] = data.get('shippingAddress',"")
                purchase_data['shippingMethod'] = data.get('shippingMethod',"")
                purchase_data['shippingTerms'] = data.get('shippingTerms',"")
                purchase_data['expectedDeliveryDate'] = data.get('expectedDeliveryDate',"")
                purchase_data['comments'] = data.get('comments',"")
                purchase_data['createdBy'] = data.get('createdBy',"")
                purchase_data['createdDate'] = data.get('createdDate',"")
                purchase_data['approvedBy'] = data.get('approvedBy',"")
                purchase_data['approvalDate'] = data.get('approvalDate',"")
           
                if purchaseID:
                    result = objAsset.update_purchase_order(purchaseID,purchase_data)
                    response['action'] = 'update'
                else:
                    result = objAsset.create_purchase_order(purchase_data)
                    response['action'] = 'create'
                if result:
                    response['status'] = 'success'
            else:
                response['status'] = 'error'
                response['error'] = settings.ERROR_MSG.get('no_permission')
                
        except Exception as error:
            objUtility.log("Error in the method create_or_update_purchase_order in the class AssetBL, \
                                Error is : {0} ".format(str(error)))
        finally:
            return response


    def get_all_purchase_order(self):
        objAsset = AssetDA()
        objUtility = Utility()
        response = {}
        data = []
        try:
            result = objAsset.get_purchase_order_all()
            if result:
                for eachItem in result:
                    temp_result = {}
                    temp_result['poID'] = eachItem.poID
                    temp_result['companyID'] = eachItem.companyID
                    temp_result['vendorID'] = eachItem.vendorID
                    temp_result['purchaseNo'] = eachItem.purchaseNo
                    temp_result['poDate'] = eachItem.poDate
                    temp_result['shippingAddress'] = eachItem.shippingAddress
                    temp_result['shippingMethod'] = eachItem.shippingMethod
                    temp_result['shippingTerms'] = eachItem.shippingTerms
                    temp_result['expectedDeliveryDate'] = eachItem.expectedDeliveryDate
                    temp_result['comments'] = eachItem.comments
                    temp_result['createdBy'] = eachItem.createdBy
                    temp_result['createdDate'] = eachItem.createdDate
                    temp_result['approvedBy'] = eachItem.approvedBy
                    temp_result['approvedDate'] = eachItem.approvedDate
                    data.append(temp_result)
                response['data'] = data
        except Exception as error:
            objUtility.log("Error in the method get_all_purchase_order in the class AssetBL, \
                                Error is : {0} ".format(str(error)))
        finally:
            return response

    
    def purchase_order_approval(self,user,data):
        objAsset = AssetDA()
        objUtility = Utility()
        objUser = UserDA()
        response = {}
        try:
            userID = user.id
            action = data.get("action","")
            purchase_orderID = data.get('poID',0)
            roleID , roleName = objUser.get_user_role_by_id(userID)
            if roleID in (1 , 2 , "1" , "2") :
                if action == 'APPROVED':
                    status = 2
                elif action == 'REJECTED':
                    status = 3
                elif action == 'DELETE' :
                    status = 1
                order_status = objAsset.purchase_order_status(purchase_orderID,status)
                if order_status:
                    result_approval =  objAsset.purchase_order_approval(purchase_orderID,userID)
                if result_approval:
                    response['status'] = action
            else:
                response['status'] = 'error'
                response['error'] = settings.ERROR_MSG.get('no_permission')
        except Exception as error:
            objUtility.log("Error in the method purchase_order_approval in the class AssetBL, \
                                Error is : {0} ".format(str(error)))
        finally:
            return response

    # def delete_purchase_order(self , purchaseID):
    #     objAsset = AssetDA()
    #     objUtility = Utility()
    #     response = {}
    #     try:
    #         result = objAsset.delete_purchase_order(purchaseID)
    #         if result:
    #             response['status'] = 'success'
    #     except Exception as error:
    #         objUtility.log("Error in the method delete_purchase_order in the class AssetBL, \
    #                             Error is : {0} ".format(str(error)))
    #     finally:
    #         return response










            







      
        


        
