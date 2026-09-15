# from time import time
from django.db import models
""" The following tables are defined here 
PurchaseOrder
PurchaseOrderDetails
Invoice 
Vendor
AssetCategory
AssetSubCategory
Asset
AssetEmployeeMapping
"""
# class PurchaseOrder(models.Model):
#     poID        = models.AutoField(primary_key=True)
#     poRefNo     = models.IntegerField(max_length=10)
#     description = models.CharField(max_length=30,blank=True,null=True)
#     filename    = models.CharField(max_length=20)

class PurchaseOrder(models.Model):
    poID = models.AutoField(primary_key=True)
    companyID = models.IntegerField(max_length=10)
    vendorID = models.IntegerField(max_length=11)
    purchaseNo = models.IntegerField(max_length=10)
    poDate = models.DateField()
    shippingAddress = models.CharField(max_length=40)
    shippingMethod = models.CharField(max_length=20)
    shippingTerms = models.CharField(max_length=20)
    expectedDeliveryDate = models.DateField()
    comments = models.TextField()
    createdBy = models.CharField(max_length=20)
    createdDate = models.DateField()
    approvedBy = models.CharField(max_length=20,default=0)
    approvalDate = models.DateField()
    deleted = models.SmallIntegerField(default=0)


class PurchaseOrderDetails(models.Model):
    podID = models.AutoField(primary_key=True)
    poID = models.IntegerField(max_length=11)
    quantity = models.IntegerField()
    itemCode = models.CharField(max_length=15)
    itemDescription = models.TextField()
    unitPrice = models.FloatField()
    tax = models.FloatField()

    
class Invoice(models.Model):
    invoiceID = models.AutoField(primary_key=True)
    invoiceNo = models.IntegerField(max_length=10)
    vendorID = models.IntegerField(max_length=11)
    poID = models.IntegerField(max_length=11)
    invoiceFile = models.CharField(max_length=20)
    
       
class Vendor(models.Model):
    vendorID = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)
    addressLine1 = models.CharField(max_length=500)
    addressLine2 = models.CharField(max_length=500)
    addressLine3 = models.CharField(max_length=500)
    contactPersonName = models.CharField(max_length=100)
    email = models.EmailField(max_length=1000)
    phone = models.CharField(max_length=20)
    mobile = models.CharField(max_length=20)
    website = models.CharField(max_length=200)
    is_deleted = models.SmallIntegerField(default=0)
    class Meta:
        db_table = u'vendor'
    
    
class AssetCategory(models.Model):
    categoryID = models.AutoField(primary_key=True)
    name = models.CharField(max_length=250)
    description = models.CharField(max_length=500)
    create_date_time = models.DateTimeField(blank=True, null=True,auto_now=True)
    created_by = models.IntegerField()
    parent_categoryID = models.IntegerField(default=0)
    is_deleted = models.SmallIntegerField(default=0)
    class Meta:
        db_table = u'asset_category'
    
    
# class AssetSubCategory(models.Model):
#     assetSubCategoryID = models.AutoField(primary_key=True)
#     assetCategoryID  = models.IntegerField(max_length=11)
#     name     = models.CharField(max_length=30)
    
    
class Asset(models.Model):
    assetID = models.AutoField(primary_key=True)
    name = models.CharField(max_length=30)
    modelNumber = models.IntegerField(max_length=10)
    categoryID = models.IntegerField(max_length=11)
    poID = models.IntegerField(max_length=11)
    invoiceID = models.IntegerField(max_length=11)
    VendorID = models.IntegerField(max_length=11)
    assetStatus = models.CharField(max_length=10)
    
   
class AssetEmployeeMapping(models.Model):
    assetEmployeeMappingID = models.AutoField(primary_key=True)
    assetID = models.IntegerField(max_length=11)
    employeeID = models.IntegerField(max_length=11)
    assignedDate = models.DateField()
    releasedDate = models.DateField() 
    status = models.CharField(max_length=10)
    
 
    
    
    
        



