from pTracker.common.utility import Utility
from pTracker.dataaccess.ptracker_access.asset_models import Asset, AssetCategory
from pTracker.dataaccess.ptracker_access.asset_models import Vendor, PurchaseOrder
from pTracker.dataaccess.ptracker_access.asset_models import PurchaseOrderDetails
from pTracker.dataaccess.ptracker_access.asset_models import Invoice, AssetEmployeeMapping

class AssetDA() :

    def __init__(self):
        pass

    """  methods for PurchaseOrder """
    
    def create_purchase_order(self , purchase_data) :
        return PurchaseOrder.objects.create(**purchase_data)

    def get_purchase_order_all(self):
        return PurchaseOrder.objects.filter(deleted = 0)

    def update_purchase_order(self , purchase_orderID , purchase_data) :
        return PurchaseOrder.objects.filter(poID = purchase_orderID).update(**purchase_data)
        
    def delete_purchase_order(self , purchase_orderID) :
        return PurchaseOrder.objects.filter(poID = purchase_orderID).update(deleted = 1)
       
    def purchase_order_status(self , purchase_orderID , status=1):
        try:
            if status == 1 :
                order_status = PurchaseOrder.objects.filter(poID = purchase_orderID).update(
                                status = status,
                                deleted = 1
                                )
            else:
                order_status = PurchaseOrder.objects.filter(poID = purchase_orderID).update(status = status)
        except Exception as err:
            Utility().log(err)
            order_status = None
        finally:
            return order_status

    def purchase_order_approval(self , purchase_orderID , userID):
        try:
            update_approval = PurchaseOrder.objects.filter(poId = purchase_orderID).update(approvedBy = userID)
        except Exception as err:
            Utility().log(err)
            update_approval = None
        finally:
            return update_approval

    """  methods for Vendor """

    def create_vendor(self , vendor_data) :
        return Vendor.objects.create(**vendor_data)

    def get_vendor_details(self,vendorID=0):
        if vendorID:
            return Vendor.objects.filter(vendorID = vendorID,is_deleted = 0)
        else:
            return Vendor.objects.filter(is_deleted = 0)
    
    def update_vendor(self , vendorID , vendor_data):
        return Vendor.objects.filter(vendorID = vendorID).update(**vendor_data)
        
    def delete_vendor(self , vendorID):
        return Vendor.objects.filter(vendorID = vendorID).update(is_deleted = 1)

    """ methods for PurchaseOrderDetails """

    def create_purchase_order_details(self , purchaseDetails_data):
        return PurchaseOrderDetails.objects.create(**purchaseDetails_data)

    def get_purchase_order_details_all(self):
        return PurchaseOrderDetails.objects.all()
    
    def update_purchase_order_details(self,podID,details_data):
        return PurchaseOrderDetails.objects.filter(podID = podID).update(**details_data)
       
    def delete_purchase_order_details(self,podID):
        return PurchaseOrderDetails.objects.filter(podID = podID).delete()

    """ methods for Invoice """

    def create_invoice(sef , invoice_data):
        return Invoice.objects.create(**invoice_data)

    def get_invoice_all(self):
        return Invoice.objects.all()

    def update_invoice(self , invoiceID , invoice_data):
        return Invoice.objects.filter(invoiceID = invoiceID).update(**invoice_data)
        
    def delete_invoice(self , invoiceID):
        return Invoice.objects.filter(invoiceID=invoiceID).delete()

    """ methods for AssetCategory """

    def create_asset_category(self , category_data):
        return AssetCategory.objects.create(**category_data)

    def get_asset_category(self, categoryID=0):
        if categoryID:
            return AssetCategory.objects.filter(categoryID=categoryID,is_deleted=0)
        else:
            return AssetCategory.objects.filter(is_deleted=0)
    
    def get_sub_asset_category_by_parentID(self, parent_categoryID):
        return AssetCategory.objects.filter(parent_categoryID=parent_categoryID, is_deleted=0)

    def get_parent_asset_category(self):
        return AssetCategory.objects.filter(parent_categoryID=0, is_deleted=0)
    
    def update_asset_category(self, categoryID, asset_data):
            return AssetCategory.objects.filter(categoryID=categoryID).update(**asset_data)
        
    def delete_asset_category(self, categoryID):
        return AssetCategory.objects.filter(categoryID=categoryID).update(is_deleted=1)
        
    """ methods for AssetSubCategory """

    # def create_asset_sub_category(self , asset_sub_category_data):
    #     return AssetSubCategory.objects.create(**asset_sub_category_data)

    # def get_asset_sub_category_all(self):
    #     return AssetSubCategory.objects.all()

    # def update_asset_sub_category(self , asset_sub_categoryID , asset_sub_category_data):
    #     return AssetSubCategory.objects.filter(assetSubCategoryID = asset_sub_categoryID).update(
    #                             **asset_sub_category_data)
        
    # def delete_asset_sub_category(self , asset_sub_categoryID):
    #     return AssetSubCategory.objects.filter(assetSubCategoryID = asset_sub_categoryID).delete()

    """ methods for Asset """

    def create_asset(self , asset_data):
        return Asset.objects.create(**asset_data)

    def get_asset_all(self):
        return Asset.objects.all()

    def update_asset(self , assetID , asset_data):
        return Asset.objects.filter(assetID = assetID , **asset_data)
        
    def delete_asset(self , assetID):
        return Asset.objects.filter(assetID = assetID).delete()

    """ methods for AssetEmployeeMapping """

    def create_asset_employee_mapping(self , mapping_data):
        return AssetEmployeeMapping.objects.create(**mapping_data)

    def get_asset_emp_mapping_all(self):
        return AssetEmployeeMapping.objects.all()

    def update_asset_emp_mapping(self , mappingID , mapping_data):
        return AssetEmployeeMapping.objects.filter(assetEmployeeMappingID = mappingID).update(**mapping_data)
        
    def delete_asset_emp_mapping(self , mappingID):
        return AssetEmployeeMapping.objects.filter(assetEmployeeMappingID = mappingID).delete()







    


    