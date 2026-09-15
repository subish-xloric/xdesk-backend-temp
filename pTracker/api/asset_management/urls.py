from django.urls import path
from pTracker.api.asset_management.views import CreatePurchaseOrderView, DeleteAssetCategoryView
from pTracker.api.asset_management.views import UpdatePurchaseOrderView, GetAssetCategoryView
from pTracker.api.asset_management.views import GetPurchaseOrderView, UpdateAssetCategoryView
# from pTracker.api.asset_management.views import DeletePurchaseOrderView
from pTracker.api.asset_management.views import PurchaseOrderApproval
from pTracker.api.asset_management.views import CreateVendorView
from pTracker.api.asset_management.views import UpdateVendorView
from pTracker.api.asset_management.views import GetAllVendorView
from pTracker.api.asset_management.views import DeleteVendorView
from pTracker.api.asset_management.views import CreateAssetCategoryView
from pTracker.api.asset_management.views import GetParentAssetCategory
from pTracker.api.asset_management.views import GetSubCategoryView



urlpatterns = [
    path('create_purchase_order/', CreatePurchaseOrderView.as_view(), name="create_purchase_order"),
    path('update_purchase_order/', UpdatePurchaseOrderView.as_view(), name='update_purchase_order'),
    path('get_all_purchase_order/', GetPurchaseOrderView.as_view(), name='get_all_purchase_order'),
    path('purchase_order_approval/', PurchaseOrderApproval.as_view(), name='purchase_order_approval'),
    # path('delete_purchase_order/',DeletePurchaseOrderView.as_view(),name='delete_purchase_order'),

    path('create_vendor/', CreateVendorView.as_view(), name="create_vendor"),
    path('update_vendor/', UpdateVendorView.as_view(), name='update_vendor'),
    path('get_all_vendors/', GetAllVendorView.as_view(), name='get_all_vendors'),
    path('delete_vendor/<int:vendorID>', DeleteVendorView.as_view(), name='delete_vendor'),

    path('create_asset_category/', CreateAssetCategoryView.as_view(), name='create_asset_category'),
    path('update_asset_category/', UpdateAssetCategoryView.as_view(), name='update_asset_category'),
    path('delete_asset_category/<int:categoryID>', DeleteAssetCategoryView.as_view(), name='delete_asset_category'),
    path('get_asset_category_all/', GetAssetCategoryView.as_view(), name='get_asset_category'),
    path('get_parent_asset/', GetParentAssetCategory.as_view(), name='get_parent_asset'),
    path('get_sub_asset_by_parentID/',GetSubCategoryView.as_view(), name="get_sub_asset_by_parentID"),
    
    
]


